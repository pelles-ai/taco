"""Lightweight A2A-compliant server base class.

Each TACO agent creates an A2AServer with an AgentCard and registers
async handlers for TACO task types. The server provides:

- GET  /.well-known/agent.json   — A2A Agent Card discovery
- POST /                          — JSON-RPC 2.0 dispatch
- GET  /health                    — Health check endpoint

When ``enable_admin=True``:

- POST /admin/skills              — dynamic skill registration
- DELETE /admin/skills/{skill_id} — remove a skill
- GET  /admin/skills              — list current skills

Internally wraps the official A2A SDK server infrastructure
(``A2AFastAPIApplication``, ``DefaultRequestHandler``, etc.).
"""

from __future__ import annotations

import hmac
import logging
import time
import uuid
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

from a2a.server.agent_execution import AgentExecutor
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskStore
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ._compat import (
    extract_structured_data,
    make_artifact,
    make_text_part,
)
from .types import (
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

logger = logging.getLogger("a2a")

TaskHandler = Callable[[Task, dict], Coroutine[Any, Any, Artifact]]
StreamingTaskHandler = Callable[[Task, dict], AsyncIterator[Part]]


class _TacoAgentExecutor(AgentExecutor):
    """Bridge between TACO task handlers and the A2A SDK AgentExecutor ABC."""

    def __init__(self) -> None:
        self._handlers: dict[str, TaskHandler] = {}
        self._streaming_handlers: dict[str, StreamingTaskHandler] = {}

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
        await eq.enqueue_event(
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
            )
        )

    @staticmethod
    async def _emit_completed(
        eq: EventQueue,
        task_id: str,
        ctx_id: str,
    ) -> None:
        await eq.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=ctx_id,
                status=TaskStatus(state=TaskState.completed),
                final=True,
            )
        )

    # ------------------------------------------------------------------

    async def execute(self, context, event_queue: EventQueue) -> None:
        """Dispatch to the registered TACO handler for this task type."""
        metadata = context.metadata
        message = context.message
        task_id = context.task_id or str(uuid.uuid4())
        context_id = context.context_id or str(uuid.uuid4())

        try:
            task_type = self._resolve_task_type(metadata)
        except ValueError as exc:
            await self._emit_failure(event_queue, task_id, context_id, str(exc))
            return

        input_data = self._extract_input(message) if message else {}

        # Build a TACO-style Task object for the handler
        task = context.current_task
        if task is None:
            task = Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.working),
                metadata={"taskType": task_type},
            )

        # Check if it's a streaming-only handler called via send
        is_streaming = task_type in self._streaming_handlers
        is_regular = task_type in self._handlers

        if is_regular:
            try:
                artifact = await self._handlers[task_type](task, input_data)
                await event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        task_id=task_id,
                        context_id=context_id,
                        artifact=artifact,
                        append=False,
                    )
                )
                await self._emit_completed(event_queue, task_id, context_id)
            except Exception as exc:
                logger.exception("Task handler failed for %s", task_type)
                await self._emit_failure(
                    event_queue,
                    task_id,
                    context_id,
                    f"Task handler failed for type '{task_type}': {exc}",
                )
        elif is_streaming:
            try:
                collected_parts: list[Part] = []
                handler = self._streaming_handlers[task_type]
                async for part in handler(task, input_data):
                    collected_parts.append(part)
                    await event_queue.enqueue_event(
                        TaskArtifactUpdateEvent(
                            task_id=task_id,
                            context_id=context_id,
                            artifact=make_artifact(
                                parts=[part],
                                name=f"{task_type}-stream-chunk",
                            ),
                            append=True,
                        )
                    )

                if collected_parts:
                    await event_queue.enqueue_event(
                        TaskArtifactUpdateEvent(
                            task_id=task_id,
                            context_id=context_id,
                            artifact=make_artifact(
                                parts=collected_parts,
                                name=f"{task_type}-stream-result",
                            ),
                            append=False,
                        )
                    )
                await self._emit_completed(event_queue, task_id, context_id)
            except Exception as exc:
                logger.exception("Streaming handler error for %s", task_type)
                await self._emit_failure(
                    event_queue,
                    task_id,
                    context_id,
                    f"Streaming handler failed for type '{task_type}': {exc}",
                )
        else:
            await self._emit_failure(
                event_queue,
                task_id,
                context_id,
                f"No handler for task type: {task_type}",
            )

    async def cancel(self, context, event_queue: EventQueue) -> None:
        """Handle task cancellation."""
        task_id = context.task_id or str(uuid.uuid4())
        context_id = context.context_id or str(uuid.uuid4())
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.canceled),
                final=True,
            )
        )


class A2AServer:
    """Reusable FastAPI application implementing the A2A protocol.

    Wraps the official A2A SDK server infrastructure while maintaining
    TACO's handler registration API.
    """

    def __init__(
        self,
        agent_card: AgentCard,
        *,
        task_store: TaskStore | None = None,
        cors_origins: list[str] | None = None,
        enable_admin: bool = False,
        admin_auth_token: str | None = None,
        enable_monitor: bool = False,
    ) -> None:
        self.agent_card = agent_card
        self._executor = _TacoAgentExecutor()
        self._start_time = time.monotonic()
        self._admin_auth_token = admin_auth_token

        # Convert TACO AgentCard to A2A SDK AgentCard for the app
        self._a2a_card = self._to_a2a_sdk_card(agent_card)

        self._task_store = task_store or InMemoryTaskStore()
        request_handler = DefaultRequestHandler(
            agent_executor=self._executor,
            task_store=self._task_store,
        )
        self._a2a_app = A2AFastAPIApplication(
            agent_card=self._a2a_card,
            http_handler=request_handler,
        )

        self.app = self._a2a_app.build(
            agent_card_url="/.well-known/agent.json",
        )
        self.app.title = agent_card.name

        # CORS: only add middleware when explicitly provided
        if cors_origins is not None:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_origins,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Health endpoint
        self.app.get("/health")(self._health)

        # Also serve the new standard path
        self.app.get("/.well-known/agent-card.json")(self._serve_agent_card)

        # Admin endpoints (opt-in)
        if enable_admin:
            if not admin_auth_token:
                logger.warning(
                    "Admin endpoints enabled without admin_auth_token — endpoints are unprotected"
                )
            self.app.post("/admin/skills")(self._add_skill)
            self.app.delete("/admin/skills/{skill_id}")(self._remove_skill)
            self.app.get("/admin/skills")(self._list_skills)

        # Agent Monitor (opt-in) — mounts at /monitor on this app
        if enable_monitor:
            from .monitor import enable_monitor as _enable_monitor

            _enable_monitor(server=self, agent_name=agent_card.name)

    @staticmethod
    def _to_a2a_sdk_card(card: AgentCard):
        """Convert TACO AgentCard to upstream a2a.types.AgentCard."""
        from a2a.types import (
            AgentCapabilities as A2ACapabilities,
        )
        from a2a.types import (
            AgentCard as A2AAgentCard,
        )
        from a2a.types import (
            AgentSkill as A2AAgentSkill,
        )

        skills = []
        for s in card.skills:
            a2a_skill = A2AAgentSkill(
                id=s.id,
                name=s.name,
                description=s.description,
                tags=s.tags or [],
                input_modes=s.input_modes,
                output_modes=s.output_modes,
            )
            skills.append(a2a_skill)

        return A2AAgentCard(
            name=card.name,
            description=card.description,
            url=card.url,
            version=card.version,
            default_input_modes=card.default_input_modes,
            default_output_modes=card.default_output_modes,
            capabilities=A2ACapabilities(
                streaming=card.capabilities.streaming if card.capabilities else False,
            ),
            skills=skills,
        )

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
        """
        self._executor._streaming_handlers[task_type] = handler
        if self.agent_card.capabilities:
            self.agent_card.capabilities.streaming = True

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

    async def _serve_agent_card(self) -> JSONResponse:
        return JSONResponse(
            self.agent_card.model_dump(by_alias=True, exclude_none=True),
        )

    # ------------------------------------------------------------------
    # A2A SDK card sync
    # ------------------------------------------------------------------

    def _sync_a2a_card(self) -> None:
        """Re-sync the A2A SDK card after TACO agent_card mutations."""
        self._a2a_card = self._to_a2a_sdk_card(self.agent_card)
        self._a2a_app.agent_card = self._a2a_card
        self._a2a_app.handler.agent_card = self._a2a_card

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
