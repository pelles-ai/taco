"""Lightweight A2A-compliant server base class.

Each TACO agent creates an A2AServer with an AgentCard and registers
async handlers for TACO task types. The server provides:

- GET  /.well-known/agent-card.json — A2A v0.3+ Agent Card discovery
- GET  /.well-known/agent.json      — Legacy Agent Card path (kept for back-compat)
- POST /                            — JSON-RPC 2.0 dispatch
- GET  /health                      — Health check endpoint

When ``enable_admin=True``:

- POST /admin/skills              — dynamic skill registration
- DELETE /admin/skills/{skill_id} — remove a skill
- GET  /admin/skills              — list current skills

Internally wires the A2A SDK v1 server primitives (``LegacyRequestHandler``
plus ``create_jsonrpc_routes``) and exposes the v0.3 wire format via the
``enable_v0_3_compat=True`` flag, so on-the-wire JSON is unchanged from
TACO 0.3.x.
"""

from __future__ import annotations

import asyncio
import hmac
import logging
import time
import uuid
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

from a2a.compat.v0_3 import conversions
from a2a.server.agent_execution import AgentExecutor
from a2a.server.events import EventQueue
from a2a.server.request_handlers import LegacyRequestHandler
from a2a.server.routes import create_jsonrpc_routes
from a2a.server.tasks import (
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
    PushNotificationConfigStore,
    TaskStore,
)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ._compat import (
    extract_structured_data,
    make_artifact,
    make_text_part,
)
from .agent_card import ConstructionAgentCard
from .auth import BearerAuthMiddleware, TokenVerifier, _set_current_auth, auth_from_call_context
from .errors import TacoTaskError
from .types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Artifact,
    Message,
    Part,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

logger = logging.getLogger("taco.server")

TaskHandler = Callable[[Task, dict], Coroutine[Any, Any, Artifact]]
StreamingTaskHandler = Callable[[Task, dict], AsyncIterator[Part]]

# JSON-RPC method names (v0.3 compat and v1) that open an SSE stream. The
# a2a-sdk dispatcher records the method on ``ServerCallContext.state``.
_STREAMING_METHODS = frozenset({"message/stream", "SendStreamingMessage"})


def _failure_text(task_type: str, exc: Exception) -> str:
    """The status message a caller sees when a handler raises ``exc``.

    Only :class:`TacoTaskError` messages are passed through. Anything else is
    logged with an error id and reported generically, so exception text
    (connection strings, paths, upstream API errors) never leaves the server.
    """
    if isinstance(exc, TacoTaskError):
        logger.info("Task handler for %s failed: %s", task_type, exc)
        return str(exc)
    error_id = uuid.uuid4().hex[:12]
    logger.error("Task handler for %s failed (error id %s)", task_type, error_id, exc_info=exc)
    return f"Task handler failed for type '{task_type}' (error id {error_id})"


def _is_streaming_request(context: Any) -> bool:
    """Return True when the request that started this execution is a stream."""
    call_context = getattr(context, "call_context", None)
    state = getattr(call_context, "state", None) or {}
    return state.get("method") in _STREAMING_METHODS


# ---------------------------------------------------------------------------
# Pydantic ↔ protobuf bridge for the executor
#
# v1 of the A2A SDK passes protobuf objects through the executor boundary
# (``RequestContext.message`` / ``.current_task``, ``EventQueue`` events).
# We keep the user-facing handler API on Pydantic v0_3 types so existing
# TACO handlers do not have to change. These helpers convert at the edges.
# ---------------------------------------------------------------------------


def _pb_message_to_compat(pb_msg) -> Message | None:
    return conversions.to_compat_message(pb_msg) if pb_msg is not None else None


def _pb_task_to_compat(pb_task) -> Task | None:
    return conversions.to_compat_task(pb_task) if pb_task is not None else None


async def _enqueue(event_queue: EventQueue, event: object) -> None:
    """Convert a Pydantic v0.3 event to protobuf and enqueue."""
    if isinstance(event, TaskStatusUpdateEvent):
        await event_queue.enqueue_event(conversions.to_core_task_status_update_event(event))
    elif isinstance(event, TaskArtifactUpdateEvent):
        await event_queue.enqueue_event(conversions.to_core_task_artifact_update_event(event))
    elif isinstance(event, Message):
        await event_queue.enqueue_event(conversions.to_core_message(event))
    elif isinstance(event, Task):
        await event_queue.enqueue_event(conversions.to_core_task(event))
    else:
        # Already a protobuf event; let the queue validate it.
        await event_queue.enqueue_event(event)  # type: ignore[arg-type]


class _TacoAgentExecutor(AgentExecutor):
    """Bridge between TACO task handlers and the A2A SDK AgentExecutor ABC."""

    def __init__(self) -> None:
        self._handlers: dict[str, TaskHandler] = {}
        self._streaming_handlers: dict[str, StreamingTaskHandler] = {}
        # Running handler jobs by task id, so cancel() can stop them.
        self._running: dict[str, asyncio.Future[None]] = {}
        self._canceled: set[str] = set()

    def _resolve_task_type(self, metadata: dict[str, Any] | None) -> str:
        """Determine task_type from request metadata, or auto-select sole handler."""
        task_type = (metadata or {}).get("taskType")
        if task_type:
            return task_type
        all_handlers = set(self._handlers) | set(self._streaming_handlers)
        if len(all_handlers) == 1:
            task_type = next(iter(all_handlers))
            logger.info(
                "No taskType specified; using sole registered handler: %s",
                task_type,
            )
            return task_type
        available = sorted(all_handlers)
        raise ValueError(f"Missing metadata.taskType. Available: {available}")

    def _extract_input(self, message: Message) -> dict[str, Any]:
        """Extract structured data from the first DataPart in a message."""
        for part in message.parts:
            data = extract_structured_data(part)
            if data is not None:
                return data
        logger.warning("Message has no DataPart; handler receives empty input")
        return {}

    # ------------------------------------------------------------------
    # Event-emission helpers (reduce duplication)
    # ------------------------------------------------------------------

    @staticmethod
    async def _emit_failure(
        eq: EventQueue,
        task_id: str,
        ctx_id: str,
        text: str,
    ) -> None:
        await _enqueue(
            eq,
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=ctx_id,
                status=TaskStatus(
                    state=TaskState.failed,
                    message=Message(
                        role=Role.agent,
                        parts=[make_text_part(text)],
                        message_id=str(uuid.uuid4()),
                    ),
                ),
                final=True,
            ),
        )

    @staticmethod
    async def _emit_completed(
        eq: EventQueue,
        task_id: str,
        ctx_id: str,
    ) -> None:
        await _enqueue(
            eq,
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=ctx_id,
                status=TaskStatus(state=TaskState.completed),
                final=True,
            ),
        )

    # ------------------------------------------------------------------

    async def execute(self, context, event_queue: EventQueue) -> None:
        """Run the handler for this task as a job :meth:`cancel` can stop."""
        task_id = context.task_id or str(uuid.uuid4())
        work = asyncio.ensure_future(self._run(context, event_queue, task_id))
        self._running[task_id] = work
        try:
            await work
        except asyncio.CancelledError:
            work.cancel()
            if task_id in self._canceled:
                return  # cancel() already reported the task as canceled
            raise
        finally:
            self._running.pop(task_id, None)
            self._canceled.discard(task_id)

    async def _run(self, context, event_queue: EventQueue, task_id: str) -> None:
        """Dispatch to the registered TACO handler for this task type."""
        # Make the caller's identity available to handlers via
        # taco.current_auth(). This runs in its own task, so it never leaks.
        _set_current_auth(auth_from_call_context(getattr(context, "call_context", None)))
        metadata = context.metadata
        message = _pb_message_to_compat(context.message)
        context_id = context.context_id or str(uuid.uuid4())

        try:
            task_type = self._resolve_task_type(metadata)
        except ValueError as exc:
            await self._emit_failure(event_queue, task_id, context_id, str(exc))
            return

        input_data = self._extract_input(message) if message else {}

        # Report the task as working before the handler runs. Without an
        # early event, return_immediately callers and streaming clients saw
        # nothing until the handler had finished.
        task = _pb_task_to_compat(context.current_task)
        if task is None:
            task = Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.working),
                history=[message] if message else None,
                metadata={"taskType": task_type},
            )
            await _enqueue(event_queue, task)
        else:
            await _enqueue(
                event_queue,
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    status=TaskStatus(state=TaskState.working),
                    final=False,
                ),
            )

        # A ``message/stream`` request uses the streaming handler when there is
        # one; ``message/send`` prefers the regular handler and falls back to
        # collecting a streaming handler's parts into one artifact.
        has_streaming = task_type in self._streaming_handlers
        has_regular = task_type in self._handlers
        use_streaming = has_streaming and (_is_streaming_request(context) or not has_regular)

        if has_regular and not use_streaming:
            try:
                artifact = await self._handlers[task_type](task, input_data)
                await _enqueue(
                    event_queue,
                    TaskArtifactUpdateEvent(
                        task_id=task_id,
                        context_id=context_id,
                        artifact=artifact,
                        append=False,
                    ),
                )
                await self._emit_completed(event_queue, task_id, context_id)
            except Exception as exc:
                await self._emit_failure(
                    event_queue, task_id, context_id, _failure_text(task_type, exc)
                )
        elif use_streaming:
            try:
                collected_parts: list[Part] = []
                handler = self._streaming_handlers[task_type]
                # All chunks share one artifact id. The A2A spec only allows
                # ``append=True`` for an artifact that already exists, so the
                # first chunk creates the artifact and later chunks append to
                # it. a2a-sdk >= 1.1 rejects an append to an unknown id.
                stream_artifact_id = str(uuid.uuid4())
                async for part in handler(task, input_data):
                    is_first_chunk = not collected_parts
                    collected_parts.append(part)
                    await _enqueue(
                        event_queue,
                        TaskArtifactUpdateEvent(
                            task_id=task_id,
                            context_id=context_id,
                            artifact=make_artifact(
                                parts=[part],
                                name=f"{task_type}-stream-chunk",
                                artifact_id=stream_artifact_id,
                            ),
                            append=not is_first_chunk,
                        ),
                    )

                if collected_parts:
                    await _enqueue(
                        event_queue,
                        TaskArtifactUpdateEvent(
                            task_id=task_id,
                            context_id=context_id,
                            artifact=make_artifact(
                                parts=collected_parts,
                                name=f"{task_type}-stream-result",
                            ),
                            append=False,
                        ),
                    )
                await self._emit_completed(event_queue, task_id, context_id)
            except Exception as exc:
                await self._emit_failure(
                    event_queue, task_id, context_id, _failure_text(task_type, exc)
                )
        else:
            await self._emit_failure(
                event_queue,
                task_id,
                context_id,
                f"No handler for task type: {task_type}",
            )

    async def cancel(self, context, event_queue: EventQueue) -> None:
        """Stop the task's handler, if it is still running, and report it canceled."""
        task_id = context.task_id or str(uuid.uuid4())
        context_id = context.context_id or str(uuid.uuid4())
        work = self._running.get(task_id)
        if work is not None and not work.done():
            self._canceled.add(task_id)
            work.cancel()
        await _enqueue(
            event_queue,
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.canceled),
                final=True,
            ),
        )


class A2AServer:
    """Reusable FastAPI application implementing the A2A protocol.

    Wraps the official A2A SDK v1 server primitives (``LegacyRequestHandler``
    plus ``create_jsonrpc_routes``) while exposing the v0.3 JSON-RPC wire
    format unchanged.
    """

    def __init__(
        self,
        agent_card: AgentCard | ConstructionAgentCard,
        *,
        task_store: TaskStore | None = None,
        push_config_store: PushNotificationConfigStore | None = None,
        cors_origins: list[str] | None = None,
        enable_admin: bool = False,
        admin_auth_token: str | None = None,
        enable_monitor: bool = False,
        monitor_auth_token: str | None = None,
        token_verifier: TokenVerifier | None = None,
        require_task_scope: bool = True,
    ) -> None:
        """Create the server.

        ``token_verifier`` turns on bearer-token auth for the JSON-RPC
        endpoint (see :mod:`taco.auth`): requests without a valid token get
        HTTP 401 and, with ``require_task_scope``, a token lacking
        ``taco:task:<taskType>`` gets HTTP 403. Declare the scheme in the
        card's ``security_schemes`` / ``security`` so callers know to send it.

        ``agent_card`` may be a :class:`ConstructionAgentCard`; it is
        converted with ``to_a2a()``.
        """
        if isinstance(agent_card, ConstructionAgentCard):
            agent_card = agent_card.to_a2a()
        self.agent_card = agent_card
        if not agent_card.url:
            logger.info(
                "Agent card %r has no url; the served card will use the address "
                "each request reached. Set url= to the agent's public address.",
                agent_card.name,
            )
        self._executor = _TacoAgentExecutor()
        self._start_time = time.monotonic()
        self._admin_auth_token = admin_auth_token

        # Build the protobuf AgentCard the v1 SDK requires, then construct
        # the request handler around our executor. When the card advertises
        # push_notifications, plug in an InMemoryPushNotificationConfigStore
        # by default so callers can register webhooks out of the box.
        self._a2a_card_pb = self._to_protobuf_card(agent_card)
        self._task_store = task_store or InMemoryTaskStore()
        if push_config_store is None and (
            agent_card.capabilities is not None and agent_card.capabilities.push_notifications
        ):
            push_config_store = InMemoryPushNotificationConfigStore()
        self._push_config_store = push_config_store
        self._request_handler = LegacyRequestHandler(
            agent_executor=self._executor,
            task_store=self._task_store,
            agent_card=self._a2a_card_pb,
            push_config_store=push_config_store,
        )

        # Build the FastAPI app and mount the v1 JSON-RPC routes (with v0.3
        # compat enabled so legacy method names like ``message/send`` still
        # dispatch on the same endpoint).
        self.app = FastAPI(title=agent_card.name)
        self.app.router.routes.extend(
            create_jsonrpc_routes(
                request_handler=self._request_handler,
                rpc_url="/",
                enable_v0_3_compat=True,
            )
        )

        # TACO serves its own card (with the x-construction extension) at
        # both the new v0.3+ path and the legacy path.
        self.app.get("/.well-known/agent-card.json")(self._serve_agent_card)
        self.app.get("/.well-known/agent.json")(self._serve_agent_card)
        self.app.get("/health")(self._health)

        if enable_admin:
            if not admin_auth_token:
                logger.warning(
                    "Admin endpoints enabled without admin_auth_token — endpoints are unprotected"
                )
            self.app.post("/admin/skills")(self._add_skill)
            self.app.delete("/admin/skills/{skill_id}")(self._remove_skill)
            self.app.get("/admin/skills")(self._list_skills)

        # Middleware added later wraps earlier middleware: CORS outermost (so
        # 401/403 responses still carry CORS headers), then auth, then the
        # monitor's tracer, so rejected requests never reach handlers.
        if enable_monitor:
            from .monitor import enable_monitor as _enable_monitor

            _enable_monitor(
                server=self,
                agent_name=agent_card.name,
                auth_token=monitor_auth_token,
            )

        if token_verifier is not None:
            self.app.add_middleware(
                BearerAuthMiddleware,
                server=self,
                verifier=token_verifier,
                require_task_scope=require_task_scope,
            )

        if cors_origins is not None:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_origins,
                allow_methods=["*"],
                allow_headers=["*"],
            )

    @staticmethod
    def _to_protobuf_card(card: AgentCard):
        """Convert TACO AgentCard to the v1 protobuf form via the v0_3 compat path."""
        from a2a.compat.v0_3.types import (
            AgentCapabilities as A2ACapabilities,
        )
        from a2a.compat.v0_3.types import (
            AgentCard as A2AAgentCard,
        )
        from a2a.compat.v0_3.types import (
            AgentSkill as A2AAgentSkill,
        )

        skills = []
        for s in card.skills:
            skills.append(
                A2AAgentSkill(
                    id=s.id,
                    name=s.name,
                    description=s.description,
                    tags=s.tags or [],
                    input_modes=s.input_modes,
                    output_modes=s.output_modes,
                )
            )

        compat_card = A2AAgentCard(
            name=card.name,
            description=card.description,
            url=card.url,
            version=card.version,
            default_input_modes=card.default_input_modes,
            default_output_modes=card.default_output_modes,
            capabilities=A2ACapabilities(
                streaming=card.capabilities.streaming if card.capabilities else False,
                push_notifications=(
                    card.capabilities.push_notifications
                    if card.capabilities and card.capabilities.push_notifications is not None
                    else False
                ),
            ),
            skills=skills,
        )
        return conversions.to_core_agent_card(compat_card)

    def register_handler(self, task_type: str, handler: TaskHandler) -> None:
        """Register an async handler for a TACO task type.

        Handler signature: async def handler(task: Task, input_data: dict) -> Artifact
        """
        self._executor._handlers[task_type] = handler

    def register_streaming_handler(
        self,
        task_type: str,
        handler: StreamingTaskHandler,
    ) -> None:
        """Register an async streaming handler for a TACO task type.

        Handler signature: async def handler(task: Task, input_data: dict) -> AsyncIterator[Part]

        Marks the agent card as streaming-capable. ``message/stream`` requests
        for ``task_type`` use this handler even when a regular handler is also
        registered; ``message/send`` requests prefer the regular handler.
        """
        self._executor._streaming_handlers[task_type] = handler
        if self.agent_card.capabilities is None:
            self.agent_card.capabilities = AgentCapabilities(streaming=True)
        else:
            self.agent_card.capabilities.streaming = True
        # The a2a-sdk request handler checks the protobuf card's capabilities
        # before accepting ``message/stream``, so it must be rebuilt too.
        self._sync_a2a_card()

    # ------------------------------------------------------------------
    # Health endpoint
    # ------------------------------------------------------------------

    async def _health(self) -> JSONResponse:
        from . import __version__

        handlers = sorted(set(self._executor._handlers) | set(self._executor._streaming_handlers))
        return JSONResponse(
            {
                "status": "ok",
                "agent": self.agent_card.name,
                "version": __version__,
                "uptime_seconds": round(time.monotonic() - self._start_time, 2),
                "handlers": handlers,
            }
        )

    # ------------------------------------------------------------------
    # Agent card endpoint (serves TACO card with x-construction)
    # ------------------------------------------------------------------

    async def _serve_agent_card(self, request: Request) -> JSONResponse:
        card = self.agent_card.model_dump(mode="json", by_alias=True, exclude_none=True)
        if not card.get("url"):
            # A2A clients connect to the card's url; an empty one makes the
            # agent unreachable through standard clients. Fall back to the
            # address this request reached.
            card["url"] = str(request.base_url).rstrip("/")
        return JSONResponse(card)

    # ------------------------------------------------------------------
    # A2A SDK card sync
    # ------------------------------------------------------------------

    def _sync_a2a_card(self) -> None:
        """Re-sync the protobuf AgentCard after TACO agent_card mutations."""
        self._a2a_card_pb = self._to_protobuf_card(self.agent_card)
        # LegacyRequestHandler keeps the card on a private attribute; refresh
        # it so dynamic skill registration shows up in subsequent dispatches.
        self._request_handler._agent_card = self._a2a_card_pb  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Admin auth helper
    # ------------------------------------------------------------------

    def _check_admin_auth(self, request: Request) -> JSONResponse | None:
        """Return a 401 JSONResponse if admin auth is required and fails, else None."""
        if not self._admin_auth_token:
            return None
        auth_header = request.headers.get("authorization", "")
        expected = f"Bearer {self._admin_auth_token}"
        if hmac.compare_digest(auth_header, expected):
            return None
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    # ------------------------------------------------------------------
    # Dynamic skill admin (opt-in, not part of A2A spec)
    # ------------------------------------------------------------------

    async def _add_skill(self, request: Request) -> JSONResponse:
        auth_err = self._check_admin_auth(request)
        if auth_err:
            return auth_err
        try:
            data = await request.json()
            skill = AgentSkill.model_validate(data)
        except Exception as exc:
            return JSONResponse(
                {"error": f"Invalid skill data: {exc}"},
                status_code=400,
            )
        self.agent_card.skills.append(skill)
        self._sync_a2a_card()
        return JSONResponse({"status": "ok", "skillId": skill.id})

    async def _remove_skill(self, request: Request, skill_id: str) -> JSONResponse:
        auth_err = self._check_admin_auth(request)
        if auth_err:
            return auth_err
        original_count = len(self.agent_card.skills)
        self.agent_card.skills = [s for s in self.agent_card.skills if s.id != skill_id]
        if len(self.agent_card.skills) == original_count:
            return JSONResponse(
                {"status": "not_found", "skillId": skill_id},
                status_code=404,
            )
        self._sync_a2a_card()
        return JSONResponse({"status": "ok", "skillId": skill_id})

    async def _list_skills(self, request: Request) -> JSONResponse:
        auth_err = self._check_admin_auth(request)
        if auth_err:
            return auth_err
        skills = [s.model_dump(by_alias=True, exclude_none=True) for s in self.agent_card.skills]
        return JSONResponse(skills)
