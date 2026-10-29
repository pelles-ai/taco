"""Tests for the Agent Monitor: tracing outcomes, escaping and access control."""

from __future__ import annotations

import re

import httpx
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from taco import A2AServer, ConstructionAgentCard, ConstructionSkill, TacoTaskError
from taco._compat import make_artifact, make_data_part
from taco.monitor import _ui, get_event_bus
from taco.types import Artifact, Task

TOKEN = "s3cret-monitor-token"


@pytest.fixture(autouse=True)
def _clear_event_bus():
    """The monitor's event bus is process-wide; start each test empty."""
    get_event_bus().clear()
    yield
    get_event_bus().clear()


def _server(**kwargs) -> A2AServer:
    card = ConstructionAgentCard(
        name="Monitored Agent",
        url="http://test",
        trade="electrical",
        csi_divisions=["26"],
        skills=[
            ConstructionSkill(id="estimate", task_type="estimate", output_schema="estimate-v1")
        ],
    ).to_a2a()
    return A2AServer(card, enable_monitor=True, **kwargs)


def _send(task_type: str = "estimate", method: str = "message/send") -> dict:
    return {
        "jsonrpc": "2.0",
        "id": "1",
        "method": method,
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "data", "data": {}}],
                "messageId": "m-1",
            },
            "metadata": {"taskType": task_type},
        },
    }


def _client(server: A2AServer) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")


class TestOutcomeTracing:
    async def test_failed_handler_is_reported_as_failed(self):
        server = _server()

        async def boom(task: Task, input_data: dict) -> Artifact:
            raise RuntimeError("boom")

        server.register_handler("estimate", boom)
        async with _client(server) as client:
            await client.post("/", json=_send())
            events = (await client.get("/monitor/api/events")).json()

        handler_events = [e for e in events if e["kind"].startswith("handler")]
        assert [e["kind"] for e in handler_events] == ["handler_start", "handler_error"]
        assert "boom" not in (handler_events[-1]["error"] or "")

    async def test_successful_handler_is_reported_as_completed(self):
        server = _server()

        async def ok(task: Task, input_data: dict) -> Artifact:
            return make_artifact(parts=[make_data_part({"ok": True})])

        server.register_handler("estimate", ok)
        async with _client(server) as client:
            await client.post("/", json=_send())
            events = (await client.get("/monitor/api/events")).json()

        assert [e["kind"] for e in events if e["kind"].startswith("handler")] == [
            "handler_start",
            "handler_end",
        ]


class TestUiEscaping:
    def _render_event_source(self) -> str:
        match = re.search(r"function renderEvent\(ev\) \{.*?\n\}\n", _ui.HTML_UI, re.S)
        assert match, "renderEvent not found"
        return match.group(0)

    def _event_template(self) -> str:
        """The HTML template literal renderEvent builds for each event."""
        source = self._render_event_source()
        return source[source.index("let html = `") :]

    def test_every_event_field_is_escaped(self):
        """Caller-controlled text (method, task type, payload) must never reach
        innerHTML unescaped: the JSON-RPC method is copied straight from the
        request body."""
        template = self._event_template()
        for expr in re.findall(r"\$\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", template):
            if "ev." in expr or expr.strip() == "dur":
                assert re.search(r"escape(Html|Attr)\(", expr), f"unescaped: ${{{expr}}}"

    def test_no_inline_event_handlers_in_event_markup(self):
        assert "onclick=" not in self._event_template()

    async def test_raw_method_is_stored_but_rendered_escaped(self):
        server = _server()
        payload = {"jsonrpc": "2.0", "id": 1, "method": "<img src=x onerror=alert(1)>"}
        async with _client(server) as client:
            await client.post("/", json=payload)
            events = (await client.get("/monitor/api/events")).json()
        assert any(e["method"] == payload["method"] for e in events)
        assert "escapeHtml(ev.method" in self._render_event_source()


class TestAccessControl:
    async def test_no_cors_headers_on_monitor_api(self):
        async with _client(_server()) as client:
            resp = await client.get(
                "/monitor/api/events", headers={"Origin": "https://evil.example"}
            )
        assert resp.status_code == 200
        assert "access-control-allow-origin" not in resp.headers

    async def test_token_required_when_configured(self):
        async with _client(_server(monitor_auth_token=TOKEN)) as client:
            assert (await client.get("/monitor/api/events")).status_code == 401
            assert (await client.get("/monitor/api/info")).status_code == 401
            assert (await client.post("/monitor/api/clear")).status_code == 401
            wrong = {"Authorization": "Bearer nope"}
            assert (await client.get("/monitor/api/events", headers=wrong)).status_code == 401
            ok = {"Authorization": f"Bearer {TOKEN}"}
            assert (await client.get("/monitor/api/events", headers=ok)).status_code == 200
            # The page itself carries no data and stays reachable.
            assert (await client.get("/monitor/")).status_code == 200

    def test_websocket_rejects_cross_site_origin(self):
        with TestClient(_server().app) as client:
            with pytest.raises(WebSocketDisconnect) as exc_info:  # noqa: SIM117
                with client.websocket_connect(
                    "/monitor/ws", headers={"origin": "https://evil.example"}
                ) as ws:
                    ws.receive_json()
            assert exc_info.value.code == 1008

    def test_websocket_same_origin_receives_events(self):
        server = _server()

        async def ok(task: Task, input_data: dict) -> Artifact:
            return make_artifact(parts=[make_data_part({"ok": True})])

        server.register_handler("estimate", ok)
        with (
            TestClient(server.app) as client,
            client.websocket_connect("/monitor/ws", headers={"origin": "http://testserver"}) as ws,
        ):
            client.post("/", json=_send())
            assert ws.receive_json()["kind"] == "incoming_request"

    def test_websocket_requires_token_when_configured(self):
        server = _server(monitor_auth_token=TOKEN)
        with TestClient(server.app) as client:
            with pytest.raises(WebSocketDisconnect) as exc_info:  # noqa: SIM117
                with client.websocket_connect("/monitor/ws") as ws:
                    ws.receive_json()
            assert exc_info.value.code == 1008

            with client.websocket_connect(f"/monitor/ws?token={TOKEN}") as ws:
                client.post("/", json=_send("unknown"))
                assert ws.receive_json()["kind"] == "incoming_request"


class TestFailureMessages:
    async def _failed_text(self, handler) -> str:
        server = A2AServer(
            ConstructionAgentCard(
                name="Agent",
                url="http://test",
                trade="electrical",
                csi_divisions=["26"],
            ).to_a2a()
        )
        server.register_handler("estimate", handler)
        async with _client(server) as client:
            result = (await client.post("/", json=_send())).json()["result"]
        assert result["status"]["state"] == "failed"
        return result["status"]["message"]["parts"][0]["text"]

    async def test_internal_exception_text_is_not_returned(self, caplog):
        async def leaky(task: Task, input_data: dict) -> Artifact:
            raise RuntimeError("postgres://admin:hunter2@10.0.0.5/db")

        with caplog.at_level("ERROR", logger="a2a"):
            text = await self._failed_text(leaky)
        assert "hunter2" not in text
        error_id = re.search(r"error id ([0-9a-f]+)", text)
        assert error_id, text
        # The details are in the server log under the same id.
        assert any(error_id.group(1) in r.getMessage() and r.exc_info for r in caplog.records)

    async def test_taco_task_error_message_is_returned(self):
        async def picky(task: Task, input_data: dict) -> Artifact:
            raise TacoTaskError("bom-v1 input has no lineItems")

        assert await self._failed_text(picky) == "bom-v1 input has no lineItems"

    async def test_streaming_handler_exception_text_is_not_returned(self):
        server = A2AServer(
            ConstructionAgentCard(
                name="Agent", url="http://test", trade="electrical", csi_divisions=["26"]
            ).to_a2a()
        )

        async def leaky_stream(task: Task, input_data: dict):
            raise RuntimeError("api key sk-live-123")
            yield  # pragma: no cover

        server.register_streaming_handler("estimate", leaky_stream)
        async with _client(server) as client:
            result = (await client.post("/", json=_send())).json()["result"]
        text = result["status"]["message"]["parts"][0]["text"]
        assert "sk-live" not in text and "error id" in text
