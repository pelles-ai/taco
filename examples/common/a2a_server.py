"""Lightweight A2A-compliant server base class.

Each CAIP agent creates an A2AServer with an AgentCard and registers
async handlers for CAIP task types. The server provides:

- GET  /.well-known/agent.json   — A2A Agent Card discovery
- POST /                          — JSON-RPC 2.0 dispatch
- POST /admin/skills              — dynamic skill registration (demo)
- DELETE /admin/skills/{skill_id} — remove a skill (demo)
- GET  /admin/skills              — list current skills (demo)
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .a2a_models import (
    AgentCard,
    AgentSkill,
    Artifact,
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


class A2AServer:
    """Reusable FastAPI application implementing the A2A protocol."""

    def __init__(self, agent_card: AgentCard) -> None:
        self.agent_card = agent_card
        self.app = FastAPI(title=agent_card.name)
        self.tasks: dict[str, Task] = {}
        self._handlers: dict[str, TaskHandler] = {}

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # A2A endpoints
        self.app.get("/.well-known/agent.json")(self._serve_agent_card)
        self.app.post("/")(self._jsonrpc_dispatch)

        # Demo-only admin endpoints for dynamic skill registration
        self.app.post("/admin/skills")(self._add_skill)
        self.app.delete("/admin/skills/{skill_id}")(self._remove_skill)
        self.app.get("/admin/skills")(self._list_skills)

    def register_handler(self, task_type: str, handler: TaskHandler) -> None:
        """Register an async handler for a CAIP task type.

        Handler signature: async def handler(task: Task, input_data: dict) -> Artifact
        """
        self._handlers[task_type] = handler

    # ------------------------------------------------------------------
    # A2A endpoints
    # ------------------------------------------------------------------

    async def _serve_agent_card(self) -> JSONResponse:
        return JSONResponse(
            self.agent_card.model_dump(by_alias=True, exclude_none=True),
        )

    async def _jsonrpc_dispatch(self, request: Request) -> JSONResponse:
        body = await request.json()
        rpc = JsonRpcRequest(**body)

        dispatch: dict[str, Callable] = {
            "message/send": self._handle_message_send,
            "tasks/get": self._handle_get_task,
            "tasks/cancel": self._handle_cancel_task,
        }

        handler = dispatch.get(rpc.method)
        if not handler:
            return JSONResponse(
                JsonRpcResponse(
                    id=rpc.id,
                    error={
                        "code": -32601,
                        "message": f"Method not found: {rpc.method}",
                    },
                ).model_dump(exclude_none=True),
            )

        try:
            result = await handler(rpc)
        except Exception:
            logger.exception("Handler error for %s", rpc.method)
            return JSONResponse(
                JsonRpcResponse(
                    id=rpc.id,
                    error={"code": -32603, "message": "Internal error"},
                ).model_dump(exclude_none=True),
            )

        return JSONResponse(
            JsonRpcResponse(id=rpc.id, result=result).model_dump(exclude_none=True),
        )

    async def _handle_message_send(self, rpc: JsonRpcRequest) -> dict:
        """Receive a message, dispatch to the matching task handler, return task."""
        params = rpc.params
        message_data = params.get("message", {})
        parts = message_data.get("parts", [])

        # Extract structured data (the BOM or whatever input)
        input_data: dict = {}
        for part in parts:
            if part.get("structuredData"):
                input_data = part["structuredData"]
                break

        # Determine task type from metadata or fall back to first handler
        task_type = params.get("metadata", {}).get("taskType")
        if not task_type:
            task_type = next(iter(self._handlers), None)

        if not task_type or task_type not in self._handlers:
            return {
                "error": f"No handler for task type: {task_type}",
            }

        # Create task
        task = Task(
            status=TaskStatus(state=TaskState.WORKING),
            metadata={"taskType": task_type},
        )
        self.tasks[task.id] = task

        # Execute
        try:
            artifact = await self._handlers[task_type](task, input_data)
            task.artifacts = [artifact]
            task.status = TaskStatus(state=TaskState.COMPLETED)
        except Exception as exc:
            logger.exception("Task handler failed for %s", task_type)
            task.status = TaskStatus(
                state=TaskState.FAILED,
                message=Message(role="agent", parts=[Part(text=str(exc))]),
            )

        return task.model_dump(by_alias=True, exclude_none=True)

    async def _handle_get_task(self, rpc: JsonRpcRequest) -> dict:
        task_id = rpc.params.get("id")
        task = self.tasks.get(task_id)  # type: ignore[arg-type]
        if not task:
            return {"error": f"Task not found: {task_id}"}
        return task.model_dump(by_alias=True, exclude_none=True)

    async def _handle_cancel_task(self, rpc: JsonRpcRequest) -> dict:
        task_id = rpc.params.get("id")
        task = self.tasks.get(task_id)  # type: ignore[arg-type]
        if not task:
            return {"error": f"Task not found: {task_id}"}
        task.status = TaskStatus(state=TaskState.CANCELED)
        return task.model_dump(by_alias=True, exclude_none=True)

    # ------------------------------------------------------------------
    # Dynamic skill admin (demo-only, not part of A2A spec)
    # ------------------------------------------------------------------

    async def _add_skill(self, request: Request) -> dict:
        data = await request.json()
        skill = AgentSkill.model_validate(data)
        self.agent_card.skills.append(skill)
        return {"status": "ok", "skillId": skill.id}

    async def _remove_skill(self, skill_id: str) -> dict:
        self.agent_card.skills = [
            s for s in self.agent_card.skills if s.id != skill_id
        ]
        return {"status": "ok"}

    async def _list_skills(self) -> list[dict]:
        return [
            s.model_dump(by_alias=True, exclude_none=True)
            for s in self.agent_card.skills
        ]
