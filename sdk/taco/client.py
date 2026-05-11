"""TACO Client — communicate with TACO-compatible A2A agents."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

try:
    import httpx
except ImportError:
    raise ImportError(
        "Client dependencies not installed. Install with: pip install taco-agent[client]"
    ) from None

from ._compat import make_data_part, make_message
from .types import AgentCard, Task

_log = logging.getLogger("taco.client")

# A2A protocol version this client speaks. Sent on every request as the
# ``A2A-Version`` header so peers can negotiate (the v1 protocol added
# this header explicitly; v0.3 servers ignore it harmlessly).
A2A_PROTOCOL_VERSION = "0.3"


def _merge_protocol_headers(headers: dict[str, str] | None) -> dict[str, str]:
    """Add A2A-Version to caller headers without clobbering an explicit override."""
    merged: dict[str, str] = {"A2A-Version": A2A_PROTOCOL_VERSION}
    if headers:
        merged.update(headers)
    return merged


class TacoClientError(Exception):
    """Base exception for TACO client errors."""


class RpcError(TacoClientError):
    """A JSON-RPC error returned by the remote agent."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        self.code = code
        self.rpc_message = message
        self.data = data
        super().__init__(f"RPC error {code}: {message}")


class TacoClient:
    """Async client for sending tasks to a TACO-compatible agent."""

    def __init__(
        self,
        *,
        agent_url: str,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.agent_url = agent_url.rstrip("/")
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout)
        self._agent_card: AgentCard | None = None

    # -- context manager --

    async def __aenter__(self) -> TacoClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # -- discovery --

    async def discover(self) -> AgentCard:
        """Fetch and cache the agent's AgentCard.

        Tries the A2A v0.3+ path ``/.well-known/agent-card.json`` first,
        falling back to the legacy ``/.well-known/agent.json`` on 404.
        Sends the ``A2A-Version`` header so v1 peers can negotiate.
        """
        headers = _merge_protocol_headers(None)
        resp = await self._client.get(
            f"{self.agent_url}/.well-known/agent-card.json",
            headers=headers,
        )
        if resp.status_code == 404:
            resp = await self._client.get(
                f"{self.agent_url}/.well-known/agent.json",
                headers=headers,
            )
        resp.raise_for_status()
        self._agent_card = AgentCard.model_validate(resp.json())
        return self._agent_card

    @property
    def agent_card(self) -> AgentCard | None:
        return self._agent_card

    # -- JSON-RPC helpers --

    def _rpc_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }

    async def _rpc_call(
        self,
        method: str,
        params: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload = self._rpc_request(method, params)
        resp = await self._client.post(
            f"{self.agent_url}/",
            json=payload,
            headers=_merge_protocol_headers(headers),
        )
        resp.raise_for_status()
        body = resp.json()
        if "error" in body and body["error"] is not None:
            err = body["error"]
            raise RpcError(err["code"], err["message"], err.get("data"))
        return body.get("result", {})

    # -- task operations --

    @staticmethod
    def _message_params(
        task_type: str,
        input_data: dict[str, Any],
        context_id: str | None = None,
    ) -> dict[str, Any]:
        """Build the common params dict for message/send and message/stream."""
        msg = make_message("user", [make_data_part(input_data)])
        params: dict[str, Any] = {
            "message": msg.model_dump(mode="json", by_alias=True, exclude_none=True),
            "metadata": {"taskType": task_type},
        }
        if context_id is not None:
            params["contextId"] = context_id
        return params

    async def send_message(
        self,
        task_type: str,
        input_data: dict[str, Any],
        *,
        context_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Task:
        """Send a message to the agent and return the resulting Task."""
        params = self._message_params(task_type, input_data, context_id)
        result = await self._rpc_call("message/send", params, headers=headers)
        return Task.model_validate(result)

    async def get_task(self, task_id: str) -> Task:
        """Retrieve a task by ID."""
        result = await self._rpc_call("tasks/get", {"id": task_id})
        return Task.model_validate(result)

    async def cancel_task(self, task_id: str) -> Task:
        """Cancel a task by ID."""
        result = await self._rpc_call("tasks/cancel", {"id": task_id})
        return Task.model_validate(result)

    async def run_task(
        self,
        *,
        task_type: str,
        input_data: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Legacy convenience — send a message and return raw result dict."""
        params = self._message_params(task_type, input_data)
        return await self._rpc_call("message/send", params, headers=headers)

    async def list_tasks(
        self,
        *,
        cursor: str | None = None,
        limit: int | None = None,
        context_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[list[Task], str | None]:
        """List tasks visible to this caller via the v1 ``ListTasks`` RPC.

        Returns ``(tasks, next_cursor)``. Pass ``next_cursor`` back as
        ``cursor`` on a subsequent call to fetch the next page; a
        ``None`` cursor means there are no more results.

        ``ListTasks`` was added in A2A v1.0, so this method overrides
        the default ``A2A-Version: 0.3`` header with ``1.0`` for the
        request — v0.3-only peers will reject it.
        """
        params: dict[str, Any] = {}
        if cursor is not None:
            params["pageToken"] = cursor
        if limit is not None:
            params["pageSize"] = limit
        if context_id is not None:
            params["contextId"] = context_id

        merged_headers: dict[str, str] = {"A2A-Version": "1.0"}
        if headers:
            merged_headers.update(headers)

        result = await self._rpc_call("ListTasks", params, headers=merged_headers)
        # The v1 wire format returns SCREAMING_SNAKE enums; round-trip
        # through protobuf to get back our v0.3-shaped Pydantic Task.
        from a2a.compat.v0_3 import conversions
        from a2a.types.a2a_pb2 import Task as TaskPb
        from google.protobuf.json_format import ParseDict

        tasks: list[Task] = []
        for raw in result.get("tasks", []):
            pb = ParseDict(raw, TaskPb(), ignore_unknown_fields=True)
            tasks.append(conversions.to_compat_task(pb))
        next_cursor = result.get("nextPageToken") or None
        return tasks, next_cursor

    # -- streaming --

    async def stream_message(
        self,
        task_type: str,
        input_data: dict[str, Any],
        *,
        context_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Send a streaming message and yield SSE event dicts.

        Each yielded dict has ``event`` (str) and ``data`` (parsed JSON).
        """
        params = self._message_params(task_type, input_data, context_id)
        payload = self._rpc_request("message/stream", params)
        async with self._client.stream(
            "POST",
            f"{self.agent_url}/",
            json=payload,
            headers=_merge_protocol_headers(headers),
        ) as resp:
            resp.raise_for_status()
            event_type = "message"
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("event:"):
                    event_type = line[len("event:") :].strip()
                elif line.startswith("data:"):
                    data_str = line[len("data:") :].strip()
                    try:
                        data = json.loads(data_str)
                    except (json.JSONDecodeError, ValueError) as parse_err:
                        _log.warning(
                            "Failed to parse SSE data as JSON (event=%s): %s",
                            event_type,
                            parse_err,
                        )
                        data = data_str
                    yield {"event": event_type, "data": data}
                    event_type = "message"
