"""Lightweight A2A-compliant server base class.

Each CAIP agent creates an A2AServer with an AgentCard and registers
async handlers for CAIP task types. The server provides:

- GET  /.well-known/agent.json   — A2A Agent Card discovery
- POST /                          — JSON-RPC 2.0 dispatch

When ``enable_admin=True``:

- POST /admin/skills              — dynamic skill registration
- DELETE /admin/skills/{skill_id} — remove a skill
- GET  /admin/skills              — list current skills
"""

from __future__ import annotations

import json as _json
import logging
from collections import OrderedDict
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import (
    AgentCard,
    AgentSkill,
    Artifact,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    Message,
    Part,
    Task,
    TaskState,
    TaskStatus,
)

logger = logging.getLogger("a2a")

TaskHandler = Callable[[Task, dict], Coroutine[Any, Any, Artifact]]
StreamingTaskHandler = Callable[[Task, dict], AsyncIterator[Part]]


class _TaskError(Exception):
    """Internal error raised by handlers to produce proper JSON-RPC errors."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.rpc_message = message


class A2AServer:
    """Reusable FastAPI application implementing the A2A protocol."""

    def __init__(
        self,
        agent_card: AgentCard,
        *,
        cors_origins: list[str] | None = None,
        enable_admin: bool = False,
        max_tasks: int = 10_000,
    ) -> None:
        self.agent_card = agent_card
        self.app = FastAPI(title=agent_card.name)
        self._tasks: OrderedDict[str, Task] = OrderedDict()
        self._context_index: dict[str, str] = {}  # context_id -> task_id
        self._max_tasks = max_tasks
        self._handlers: dict[str, TaskHandler] = {}
        self._streaming_handlers: dict[str, StreamingTaskHandler] = {}

        if cors_origins is None:
            cors_origins = ["*"]
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # A2A endpoints
        self.app.get("/.well-known/agent.json")(self._serve_agent_card)
        self.app.post("/")(self._jsonrpc_dispatch)

        # Admin endpoints (opt-in)
        if enable_admin:
            self.app.post("/admin/skills")(self._add_skill)
            self.app.delete("/admin/skills/{skill_id}")(self._remove_skill)
            self.app.get("/admin/skills")(self._list_skills)

    def register_handler(self, task_type: str, handler: TaskHandler) -> None:
        """Register an async handler for a CAIP task type.

        Handler signature: async def handler(task: Task, input_data: dict) -> Artifact
        """
        self._handlers[task_type] = handler

    def register_streaming_handler(
        self, task_type: str, handler: StreamingTaskHandler,
    ) -> None:
        """Register an async streaming handler for a CAIP task type.

        Handler signature: async def handler(task: Task, input_data: dict) -> AsyncIterator[Part]
        """
        self._streaming_handlers[task_type] = handler
        self.agent_card.capabilities["streaming"] = True

    # ------------------------------------------------------------------
    # A2A endpoints
    # ------------------------------------------------------------------

    async def _serve_agent_card(self) -> JSONResponse:
        return JSONResponse(
            self.agent_card.model_dump(by_alias=True, exclude_none=True),
        )

    async def _jsonrpc_dispatch(self, request: Request) -> JSONResponse:
        # Parse raw JSON
        try:
            body = await request.json()
        except Exception:
            logger.exception("Failed to parse JSON-RPC request body")
            return self._error_response(
                request_id=None, code=-32700, message="Parse error: invalid JSON",
            )

        # Validate JSON-RPC structure
        try:
            rpc = JsonRpcRequest(**body) if isinstance(body, dict) else None
            if rpc is None:
                raise ValueError("Request body must be a JSON object")
        except Exception as exc:
            logger.warning("Invalid JSON-RPC request: %s", exc)
            request_id = body.get("id") if isinstance(body, dict) else None
            return self._error_response(
                request_id=request_id, code=-32600,
                message=f"Invalid request: {exc}",
            )

        dispatch: dict[str, Callable] = {
            "message/send": self._handle_message_send,
            "message/stream": self._handle_message_stream,
            "tasks/get": self._handle_get_task,
            "tasks/cancel": self._handle_cancel_task,
        }

        handler = dispatch.get(rpc.method)
        if not handler:
            return self._error_response(
                request_id=rpc.id, code=-32601,
                message=f"Method not found: {rpc.method}",
            )

        try:
            result = await handler(rpc)
        except _TaskError as exc:
            return self._error_response(
                request_id=rpc.id, code=exc.code, message=exc.rpc_message,
            )
        except Exception as exc:
            logger.exception("Handler error for %s", rpc.method)
            return self._error_response(
                request_id=rpc.id, code=-32603,
                message="Internal error",
                data=f"{type(exc).__name__}: {exc}",
            )

        # SSE responses bypass JSON-RPC wrapping
        if not isinstance(result, dict):
            return result

        return JSONResponse(
            JsonRpcResponse(id=rpc.id, result=result).model_dump(
                by_alias=True, exclude_none=True,
            ),
        )

    def _extract_input(self, params: dict) -> tuple[dict, str, Message]:
        """Extract input_data, task_type, and user message from RPC params."""
        message_data = params.get("message", {})
        parts = message_data.get("parts", [])

        input_data: dict = {}
        structured_parts = [p for p in parts if p.get("structuredData")]
        if not structured_parts:
            logger.warning(
                "message received with no structuredData parts; "
                "handler will receive empty input",
            )
        else:
            if len(structured_parts) > 1:
                logger.warning(
                    "message received %d structuredData parts; using first",
                    len(structured_parts),
                )
            input_data = structured_parts[0]["structuredData"]

        task_type = params.get("metadata", {}).get("taskType")
        if not task_type:
            all_handlers = set(self._handlers) | set(self._streaming_handlers)
            if len(all_handlers) == 1:
                task_type = next(iter(all_handlers))
                logger.info(
                    "No taskType specified; using sole registered handler: %s",
                    task_type,
                )
            else:
                available = sorted(all_handlers)
                raise _TaskError(
                    -32602,
                    f"Missing metadata.taskType. Available: {available}",
                )

        # Build the user message
        msg_parts = [Part.model_validate(p) for p in parts]
        if not msg_parts:
            msg_parts = [Part(text="(empty message)")]
        user_message = Message(role="user", parts=msg_parts)

        return input_data, task_type, user_message

    def _get_or_create_task(
        self, task_type: str, context_id: str | None, user_message: Message,
    ) -> tuple[Task, bool]:
        """Return (task, is_continuation). Creates or resumes a task."""
        # Multi-turn: look up existing task by context_id
        if context_id is not None:
            existing_task_id = self._context_index.get(context_id)
            if existing_task_id and existing_task_id in self._tasks:
                task = self._tasks[existing_task_id]
                task.history.append(user_message)
                task.status = TaskStatus(state=TaskState.WORKING)
                return task, True

        # Evict oldest tasks if at capacity
        while len(self._tasks) >= self._max_tasks:
            evicted_id, evicted_task = self._tasks.popitem(last=False)
            if evicted_task.context_id:
                self._context_index.pop(evicted_task.context_id, None)

        # Create new task
        task = Task(
            status=TaskStatus(state=TaskState.WORKING),
            metadata={"taskType": task_type},
        )
        if context_id is not None:
            task.context_id = context_id
            self._context_index[context_id] = task.id
        task.history.append(user_message)
        self._tasks[task.id] = task
        return task, False

    async def _handle_message_send(self, rpc: JsonRpcRequest) -> dict:
        """Receive a message, dispatch to the matching task handler, return task."""
        params = rpc.params
        input_data, task_type, user_message = self._extract_input(params)
        context_id = params.get("contextId")

        if task_type not in self._handlers:
            if task_type in self._streaming_handlers:
                raise _TaskError(
                    -32602,
                    f"Task type '{task_type}' only supports streaming. "
                    f"Use message/stream instead of message/send.",
                )
            raise _TaskError(
                -32602, f"No handler for task type: {task_type}",
            )

        task, _ = self._get_or_create_task(task_type, context_id, user_message)

        # Execute
        try:
            artifact = await self._handlers[task_type](task, input_data)
            task.artifacts = [artifact]
            task.status = TaskStatus(state=TaskState.COMPLETED)
        except Exception:
            logger.exception("Task handler failed for %s", task_type)
            task.status = TaskStatus(
                state=TaskState.FAILED,
                message=Message(
                    role="agent",
                    parts=[Part(text=f"Task handler failed for type '{task_type}'")],
                ),
            )

        return task.model_dump(by_alias=True, exclude_none=True)

    async def _handle_message_stream(self, rpc: JsonRpcRequest):
        """Handle streaming message — returns an SSE response."""
        try:
            from sse_starlette.sse import EventSourceResponse
        except ImportError:
            raise _TaskError(
                -32603,
                "Streaming not available: sse-starlette not installed",
            )

        params = rpc.params
        input_data, task_type, user_message = self._extract_input(params)
        context_id = params.get("contextId")

        if task_type not in self._streaming_handlers:
            raise _TaskError(
                -32602, f"No streaming handler for task type: {task_type}",
            )

        task, _ = self._get_or_create_task(task_type, context_id, user_message)

        async def event_generator():
            try:
                handler = self._streaming_handlers[task_type]
                collected_parts: list[Part] = []
                async for part in handler(task, input_data):
                    collected_parts.append(part)
                    yield {
                        "event": "update",
                        "data": _json.dumps(
                            part.model_dump(by_alias=True, exclude_none=True),
                        ),
                    }

                # Mark complete
                if collected_parts:
                    task.artifacts = [Artifact(
                        name=f"{task_type}-stream-result",
                        parts=collected_parts,
                    )]
                task.status = TaskStatus(state=TaskState.COMPLETED)
                yield {
                    "event": "complete",
                    "data": _json.dumps(
                        task.model_dump(by_alias=True, exclude_none=True),
                    ),
                }
            except Exception as exc:
                logger.exception("Streaming handler error for %s", task_type)
                task.status = TaskStatus(
                    state=TaskState.FAILED,
                    message=Message(
                        role="agent",
                        parts=[Part(text=str(exc))],
                    ),
                )
                yield {
                    "event": "error",
                    "data": _json.dumps({
                        "error": f"{type(exc).__name__}: {exc}",
                        "task": task.model_dump(by_alias=True, exclude_none=True),
                    }),
                }

        return EventSourceResponse(event_generator())

    def _require_task(self, rpc: JsonRpcRequest) -> Task:
        """Extract and validate the task ID from RPC params, return the task."""
        task_id = rpc.params.get("id")
        if not task_id:
            raise _TaskError(-32602, "Missing required parameter: 'id'")
        task = self._tasks.get(task_id)
        if not task:
            raise _TaskError(-32602, f"Task not found: {task_id}")
        return task

    async def _handle_get_task(self, rpc: JsonRpcRequest) -> dict:
        task = self._require_task(rpc)
        return task.model_dump(by_alias=True, exclude_none=True)

    async def _handle_cancel_task(self, rpc: JsonRpcRequest) -> dict:
        task = self._require_task(rpc)
        task.status = TaskStatus(state=TaskState.CANCELED)
        return task.model_dump(by_alias=True, exclude_none=True)

    # ------------------------------------------------------------------
    # Dynamic skill admin (opt-in, not part of A2A spec)
    # ------------------------------------------------------------------

    async def _add_skill(self, request: Request) -> JSONResponse:
        try:
            data = await request.json()
            skill = AgentSkill.model_validate(data)
        except Exception as exc:
            return JSONResponse(
                {"error": f"Invalid skill data: {exc}"}, status_code=400,
            )
        self.agent_card.skills.append(skill)
        return JSONResponse({"status": "ok", "skillId": skill.id})

    async def _remove_skill(self, skill_id: str) -> JSONResponse:
        original_count = len(self.agent_card.skills)
        self.agent_card.skills = [
            s for s in self.agent_card.skills if s.id != skill_id
        ]
        if len(self.agent_card.skills) == original_count:
            return JSONResponse(
                {"status": "not_found", "skillId": skill_id}, status_code=404,
            )
        return JSONResponse({"status": "ok", "skillId": skill_id})

    async def _list_skills(self) -> list[dict]:
        return [
            s.model_dump(by_alias=True, exclude_none=True)
            for s in self.agent_card.skills
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _error_response(
        *,
        request_id: str | int | None,
        code: int,
        message: str,
        data: Any = None,
    ) -> JSONResponse:
        """Build a spec-compliant JSON-RPC 2.0 error response."""
        error = JsonRpcError(code=code, message=message, data=data)
        resp = JsonRpcResponse(id=request_id, error=error)
        return JSONResponse(resp.model_dump(by_alias=True, exclude_none=True))
