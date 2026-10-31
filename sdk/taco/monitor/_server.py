"""MonitorServer — mount-based monitor UI for live A2A tracing."""

from __future__ import annotations

import asyncio
import hmac
import logging
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.requests import HTTPConnection

from ._event_bus import EventBus

logger = logging.getLogger("taco.monitor")


class MonitorServer:
    """Monitor web UI that mounts onto the agent's existing FastAPI app.

    Instead of running a separate uvicorn server, call :meth:`mount_on`
    to attach the monitor routes under a prefix (default ``/monitor``).

    The monitor shows every request and response payload the agent handles.
    It has no CORS headers (the UI is same-origin), its WebSocket rejects
    cross-site origins, and when ``auth_token`` is set every API call and the
    WebSocket require it (``Authorization: Bearer <token>``; the UI is opened
    as ``/monitor/#token=<token>``).
    """

    def __init__(
        self,
        event_bus: EventBus,
        *,
        agent_name: str = "TACO Agent",
        auth_token: str | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.agent_name = agent_name
        self.auth_token = auth_token

    def _authorized(self, conn: HTTPConnection, *, allow_query_token: bool = False) -> bool:
        if not self.auth_token:
            return True
        expected = f"Bearer {self.auth_token}"
        if hmac.compare_digest(conn.headers.get("authorization", ""), expected):
            return True
        # Browsers cannot set headers on a WebSocket handshake.
        token = conn.query_params.get("token", "") if allow_query_token else ""
        return bool(token) and hmac.compare_digest(token, self.auth_token)

    @staticmethod
    def _same_origin(conn: HTTPConnection) -> bool:
        """Reject cross-site browser WebSockets (no CORS applies to them)."""
        origin = conn.headers.get("origin")
        if origin is None:
            return True  # not a browser
        return urlsplit(origin).netloc == conn.headers.get("host", "")

    def build_app(self) -> FastAPI:
        """Create the FastAPI application with all monitor routes."""
        from ._ui import HTML_UI

        app = FastAPI(title=f"{self.agent_name} Monitor")

        bus = self.event_bus
        agent_name = self.agent_name

        def unauthorized() -> JSONResponse:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        @app.get("/", response_class=HTMLResponse)
        async def index() -> HTMLResponse:
            return HTMLResponse(HTML_UI)

        @app.get("/api/events")
        async def get_events(request: Request, limit: int = 200, offset: int = 0) -> JSONResponse:
            if not self._authorized(request):
                return unauthorized()
            return JSONResponse(bus.get_history(limit, offset))

        @app.get("/api/info")
        async def get_info(request: Request) -> JSONResponse:
            if not self._authorized(request):
                return unauthorized()
            return JSONResponse(
                {
                    "agentName": agent_name,
                    "eventCount": bus.event_count,
                    "maxEvents": bus.max_events,
                }
            )

        @app.post("/api/clear")
        async def clear_events(request: Request) -> JSONResponse:
            if not self._authorized(request):
                return unauthorized()
            bus.clear()
            return JSONResponse({"status": "ok"})

        @app.websocket("/ws")
        async def ws_endpoint(websocket: WebSocket) -> None:
            if not self._same_origin(websocket) or not self._authorized(
                websocket, allow_query_token=True
            ):
                await websocket.close(code=1008)
                return
            await websocket.accept()
            queue: asyncio.Queue[dict[str, Any]] = bus.subscribe()
            try:
                while True:
                    event = await queue.get()
                    await websocket.send_json(event)
            except WebSocketDisconnect:
                pass
            except Exception:
                logger.debug("WebSocket error", exc_info=True)
            finally:
                bus.unsubscribe(queue)

        return app

    def mount_on(self, parent_app: FastAPI, prefix: str = "/monitor") -> None:
        """Mount the monitor UI onto an existing FastAPI application."""
        parent_app.mount(prefix, self.build_app())
        logger.info("Monitor UI mounted at %s", prefix)
