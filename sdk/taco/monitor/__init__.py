"""TACO Agent Monitor — opt-in live tracing UI for A2A communications.

Usage::

    # Option 1: via A2AServer constructor
    server = A2AServer(agent_card, enable_monitor=True)

    # Option 2: explicit
    from taco.monitor import enable_monitor
    enable_monitor(server=server)
    # Monitor UI is now at /monitor on the server's port
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

from ._event_bus import EventBus, make_event
from ._server import MonitorServer

if TYPE_CHECKING:
    from ..client import TacoClient
    from ..registry import AgentRegistry
    from ..server import A2AServer

logger = logging.getLogger("taco.monitor")

__all__ = ["EventBus", "MonitorServer", "enable_monitor", "get_event_bus"]

# ---------------------------------------------------------------------------
# Singleton event bus
# ---------------------------------------------------------------------------

_default_bus: EventBus | None = None


def get_event_bus(max_events: int = 2000) -> EventBus:
    """Get or create the default (singleton) EventBus."""
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus(max_events=max_events)
    elif _default_bus.max_events != max_events:
        logger.warning(
            "EventBus already created with max_events=%d, ignoring requested %d",
            _default_bus.max_events,
            max_events,
        )
    return _default_bus


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def enable_monitor(
    *,
    server: A2AServer | None = None,
    client: TacoClient | None = None,
    registry: AgentRegistry | None = None,
    agent_name: str | None = None,
    max_events: int = 2000,
) -> None:
    """Enable the Agent Monitor for the given server/client/registry.

    Instruments the provided objects so their A2A traffic appears in the
    monitor UI, and mounts the monitor routes onto the server's app at
    ``/monitor``.
    """
    bus = get_event_bus(max_events)

    if server is not None:
        _instrument_server(server, bus)
        if agent_name is None:
            agent_name = server.agent_card.name

    if client is not None:
        _instrument_client(client, bus)

    if registry is not None:
        _instrument_registry(registry, bus)

    if server is not None:
        monitor = MonitorServer(bus, agent_name=agent_name or "TACO Agent")
        monitor.mount_on(server.app)


# ---------------------------------------------------------------------------
# Server instrumentation
# ---------------------------------------------------------------------------


def _instrument_server(server: A2AServer, bus: EventBus) -> None:
    """Add monitoring middleware and executor wrapper to an A2AServer."""
    _add_server_middleware(server, bus)
    _wrap_executor(server, bus)


def _add_server_middleware(server: A2AServer, bus: EventBus) -> None:
    """Add HTTP middleware that traces incoming JSON-RPC requests."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response as StarletteResponse

    agent_name = server.agent_card.name

    class _MonitorMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Any) -> Any:
            # Only trace JSON-RPC POST to /
            if request.method != "POST" or request.url.path != "/":
                return await call_next(request)

            body = await request.body()
            try:
                payload = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                return await call_next(request)

            method = payload.get("method", "unknown")
            params = payload.get("params", {})
            task_type = None
            if isinstance(params, dict):
                task_type = (params.get("metadata") or {}).get("taskType")

            label = task_type or method
            bus.emit(
                make_event(
                    kind="incoming_request",
                    method=method,
                    direction="in",
                    summary=f"Received {label} request",
                    payload=params if isinstance(params, dict) else None,
                    task_id=params.get("id") if isinstance(params, dict) else None,
                    task_type=task_type,
                    agent_name=agent_name,
                )
            )

            start = time.monotonic()
            response = await call_next(request)
            duration_ms = (time.monotonic() - start) * 1000

            # Read response body (consumed by iteration)
            resp_body = b""
            async for chunk in response.body_iterator:
                resp_body += chunk if isinstance(chunk, bytes) else chunk.encode()

            resp_data: dict[str, Any] | None = None
            error: str | None = None
            try:
                resp_data = json.loads(resp_body)
                if isinstance(resp_data, dict) and resp_data.get("error"):
                    err_obj = resp_data["error"]
                    error = (
                        err_obj.get("message", "Unknown error")
                        if isinstance(err_obj, dict)
                        else str(err_obj)
                    )
            except (json.JSONDecodeError, ValueError):
                pass

            bus.emit(
                make_event(
                    kind="incoming_response",
                    method=method,
                    direction="in",
                    summary=f"Sent {label} response",
                    payload=resp_data,
                    duration_ms=round(duration_ms, 1),
                    error=error,
                    task_type=task_type,
                    agent_name=agent_name,
                )
            )

            # Reconstruct the response since we consumed body_iterator
            return StarletteResponse(
                content=resp_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

    server.app.add_middleware(_MonitorMiddleware)


def _wrap_executor(server: A2AServer, bus: EventBus) -> None:
    """Wrap the executor's execute method to trace handler execution."""
    executor = server._executor
    original_execute = executor.execute
    agent_name = server.agent_card.name

    async def monitored_execute(context: Any, event_queue: Any) -> None:
        metadata = context.metadata or {}
        task_type = metadata.get("taskType", "unknown")
        task_id = context.task_id or "unknown"

        bus.emit(
            make_event(
                kind="handler_start",
                method=task_type,
                direction="internal",
                summary=f"Processing {task_type}",
                task_id=task_id,
                task_type=task_type,
                agent_name=agent_name,
            )
        )

        start = time.monotonic()
        try:
            await original_execute(context, event_queue)
            duration_ms = (time.monotonic() - start) * 1000
            bus.emit(
                make_event(
                    kind="handler_end",
                    method=task_type,
                    direction="internal",
                    summary=f"Completed {task_type}",
                    duration_ms=round(duration_ms, 1),
                    task_id=task_id,
                    task_type=task_type,
                    agent_name=agent_name,
                )
            )
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            bus.emit(
                make_event(
                    kind="handler_error",
                    method=task_type,
                    direction="internal",
                    summary=f"Failed processing {task_type}: {exc}",
                    duration_ms=round(duration_ms, 1),
                    error=str(exc),
                    task_id=task_id,
                    task_type=task_type,
                    agent_name=agent_name,
                )
            )
            raise

    executor.execute = monitored_execute  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Client instrumentation
# ---------------------------------------------------------------------------


def _instrument_client(client: TacoClient, bus: EventBus) -> None:
    """Wrap TacoClient methods to trace outgoing RPC calls."""
    original_rpc = client._rpc_call
    original_discover = client.discover
    agent_url = client.agent_url

    async def monitored_rpc_call(
        method: str,
        params: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        task_type = None
        if isinstance(params, dict):
            task_type = (params.get("metadata") or {}).get("taskType")

        label = task_type or method
        bus.emit(
            make_event(
                kind="outgoing_request",
                method=method,
                direction="out",
                summary=f"Calling peer with {label}",
                payload=params,
                task_type=task_type,
            )
        )

        start = time.monotonic()
        try:
            result = await original_rpc(method, params, **kwargs)
            duration_ms = (time.monotonic() - start) * 1000
            bus.emit(
                make_event(
                    kind="outgoing_response",
                    method=method,
                    direction="out",
                    summary=f"Got reply for {label}",
                    payload=result,
                    duration_ms=round(duration_ms, 1),
                    task_type=task_type,
                )
            )
            return result
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            bus.emit(
                make_event(
                    kind="outgoing_response",
                    method=method,
                    direction="out",
                    summary=f"Peer call failed for {label}: {exc}",
                    duration_ms=round(duration_ms, 1),
                    error=str(exc),
                    task_type=task_type,
                )
            )
            raise

    async def monitored_discover() -> Any:
        bus.emit(
            make_event(
                kind="discovery",
                method="discover",
                direction="out",
                summary=f"Looking up agent at {agent_url}",
            )
        )

        start = time.monotonic()
        try:
            card = await original_discover()
            duration_ms = (time.monotonic() - start) * 1000
            bus.emit(
                make_event(
                    kind="discovery",
                    method="discover",
                    direction="out",
                    summary=f"Found agent: {card.name}",
                    payload=card.model_dump(by_alias=True, exclude_none=True),
                    duration_ms=round(duration_ms, 1),
                )
            )
            return card
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            bus.emit(
                make_event(
                    kind="discovery",
                    method="discover",
                    direction="out",
                    summary=f"Discovery failed for {agent_url}: {exc}",
                    duration_ms=round(duration_ms, 1),
                    error=str(exc),
                )
            )
            raise

    client._rpc_call = monitored_rpc_call  # type: ignore[assignment]
    client.discover = monitored_discover  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Registry instrumentation
# ---------------------------------------------------------------------------


def _instrument_registry(registry: AgentRegistry, bus: EventBus) -> None:
    """Wrap AgentRegistry.register to trace agent discovery."""
    original_register = registry.register

    async def monitored_register(agent_url: str) -> Any:
        bus.emit(
            make_event(
                kind="discovery",
                method="register",
                direction="out",
                summary=f"Discovering peer at {agent_url}",
            )
        )

        start = time.monotonic()
        try:
            card = await original_register(agent_url)
            duration_ms = (time.monotonic() - start) * 1000
            bus.emit(
                make_event(
                    kind="discovery",
                    method="register",
                    direction="out",
                    summary=f"Peer discovered: {card.name} at {agent_url}",
                    payload=card.model_dump(by_alias=True, exclude_none=True),
                    duration_ms=round(duration_ms, 1),
                    agent_name=card.name,
                )
            )
            return card
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            bus.emit(
                make_event(
                    kind="discovery",
                    method="register",
                    direction="out",
                    summary=f"Peer discovery failed: {agent_url}",
                    duration_ms=round(duration_ms, 1),
                    error=str(exc),
                )
            )
            raise

    registry.register = monitored_register  # type: ignore[assignment]
