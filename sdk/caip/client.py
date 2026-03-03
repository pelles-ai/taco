"""CAIP Client — communicate with CAIP-compatible A2A agents."""

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
        "Client dependencies not installed. Install with: pip install caip[client]"
    ) from None

from .models import AgentCard, Task

_log = logging.getLogger("caip.client")


class CAIPClientError(Exception):
    """Base exception for CAIP client errors."""


class RpcError(CAIPClientError):
    """A JSON-RPC error returned by the remote agent."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        self.code = code
        self.rpc_message = message
        self.data = data
        super().__init__(f"RPC error {code}: {message}")


class CAIPClient:
    """Async client for sending tasks to a CAIP-compatible agent."""

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

    async def __aenter__(self) -> CAIPClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # -- discovery --

    async def discover(self) -> AgentCard:
        """Fetch and cache the agent's AgentCard."""
        resp = await self._client.get(f"{self.agent_url}/.well-known/agent.json")
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

    async def _rpc_call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = self._rpc_request(method, params)
        resp = await self._client.post(f"{self.agent_url}/", json=payload)
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
        params: dict[str, Any] = {
            "message": {
                "role": "user",
                "parts": [{"structuredData": input_data}],
            },
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
    ) -> Task:
        """Send a message to the agent and return the resulting Task."""
        params = self._message_params(task_type, input_data, context_id)
        result = await self._rpc_call("message/send", params)
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
        self, *, task_type: str, input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Legacy convenience — send a message and return raw result dict."""
        params = self._message_params(task_type, input_data)
        return await self._rpc_call("message/send", params)

    # -- streaming --

    async def stream_message(
        self,
        task_type: str,
        input_data: dict[str, Any],
        *,
        context_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Send a streaming message and yield SSE event dicts.

        Each yielded dict has ``event`` (str) and ``data`` (parsed JSON).
        """
        params = self._message_params(task_type, input_data, context_id)
        payload = self._rpc_request("message/stream", params)
        async with self._client.stream(
            "POST", f"{self.agent_url}/", json=payload,
        ) as resp:
            resp.raise_for_status()
            event_type = "message"
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("event:"):
                    event_type = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_str = line[len("data:"):].strip()
                    try:
                        data = json.loads(data_str)
                    except (json.JSONDecodeError, ValueError) as parse_err:
                        _log.warning(
                            "Failed to parse SSE data as JSON (event=%s): %s",
                            event_type, parse_err,
                        )
                        data = data_str
                    yield {"event": event_type, "data": data}
                    event_type = "message"
