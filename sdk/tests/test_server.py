"""Tests for caip.server — A2A server protocol implementation."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx
import pytest

from caip.models import (
    AgentCard,
    Artifact,
    Part,
    Task,
    TaskState,
)
from caip.server import A2AServer


@pytest.fixture()
def client(sample_server: A2AServer):
    """HTTPX async client wired to the test server via ASGI transport."""
    transport = httpx.ASGITransport(app=sample_server.app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def _rpc(method: str, params: dict | None = None, rpc_id: str = "1") -> dict:
    return {"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params or {}}


def _msg_payload(
    method: str, task_type: str, input_data: dict, context_id: str | None = None,
) -> dict:
    params: dict = {
        "message": {
            "role": "user",
            "parts": [{"structuredData": input_data}],
        },
        "metadata": {"taskType": task_type},
    }
    if context_id:
        params["contextId"] = context_id
    return _rpc(method, params)


def _send_msg(task_type: str, input_data: dict, context_id: str | None = None) -> dict:
    return _msg_payload("message/send", task_type, input_data, context_id)


def _stream_msg(task_type: str, input_data: dict, context_id: str | None = None) -> dict:
    return _msg_payload("message/stream", task_type, input_data, context_id)


def _parse_sse(text: str) -> list[dict]:
    """Parse an SSE text stream into a list of {event, data} dicts."""
    events = []
    event_type = "message"
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("event:"):
            event_type = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_str = line[len("data:"):].strip()
            try:
                data = json.loads(data_str)
            except (json.JSONDecodeError, ValueError):
                data = data_str
            events.append({"event": event_type, "data": data})
            event_type = "message"
    return events


class TestAgentCardDiscovery:
    async def test_agent_card_endpoint(self, client: httpx.AsyncClient):
        resp = await client.get("/.well-known/agent.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Agent"
        assert data["url"] == "http://localhost:9999"

    async def test_agent_card_has_skills(self, client: httpx.AsyncClient):
        resp = await client.get("/.well-known/agent.json")
        data = resp.json()
        assert len(data["skills"]) == 1
        assert data["skills"][0]["x-construction"]["taskType"] == "test-task"

    async def test_agent_card_has_x_construction(self, client: httpx.AsyncClient):
        resp = await client.get("/.well-known/agent.json")
        data = resp.json()
        xc = data["x-construction"]
        assert xc["trade"] == "mechanical"
        assert "23" in xc["csiDivisions"]


class TestMessageSend:
    async def test_success(self, client: httpx.AsyncClient):
        payload = _send_msg("test-task", {"foo": "bar"})
        resp = await client.post("/", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["jsonrpc"] == "2.0"
        result = body["result"]
        assert result["status"]["state"] == "completed"
        assert result["artifacts"][0]["parts"][0]["structuredData"] == {"foo": "bar"}

    async def test_missing_task_type(self, client: httpx.AsyncClient):
        payload = _rpc("message/send", {
            "message": {"role": "user", "parts": [{"structuredData": {}}]},
            "metadata": {},
        })
        resp = await client.post("/", json=payload)
        body = resp.json()
        # With a single handler, it should auto-select
        assert "result" in body

    async def test_unknown_task_type(self, client: httpx.AsyncClient):
        payload = _send_msg("nonexistent", {})
        resp = await client.post("/", json=payload)
        body = resp.json()
        assert body["error"]["code"] == -32602
        assert "No handler" in body["error"]["message"]

    async def test_artifact_metadata(self, client: httpx.AsyncClient):
        payload = _send_msg("test-task", {"key": "value"})
        resp = await client.post("/", json=payload)
        body = resp.json()
        artifact = body["result"]["artifacts"][0]
        assert artifact["metadata"]["schema"] == "test-v1"
        assert artifact["name"] == "echo-result"


class TestTaskGetAndCancel:
    async def test_get_task(self, client: httpx.AsyncClient):
        # First create a task
        send_resp = await client.post("/", json=_send_msg("test-task", {"a": 1}))
        task_id = send_resp.json()["result"]["id"]

        # Then get it
        get_payload = _rpc("tasks/get", {"id": task_id})
        resp = await client.post("/", json=get_payload)
        body = resp.json()
        assert body["result"]["id"] == task_id
        assert body["result"]["status"]["state"] == "completed"

    async def test_get_nonexistent_task(self, client: httpx.AsyncClient):
        payload = _rpc("tasks/get", {"id": "nonexistent"})
        resp = await client.post("/", json=payload)
        body = resp.json()
        assert body["error"]["code"] == -32602

    async def test_cancel_task(self, client: httpx.AsyncClient):
        send_resp = await client.post("/", json=_send_msg("test-task", {"a": 1}))
        task_id = send_resp.json()["result"]["id"]

        cancel_payload = _rpc("tasks/cancel", {"id": task_id})
        resp = await client.post("/", json=cancel_payload)
        body = resp.json()
        assert body["result"]["status"]["state"] == "canceled"

    async def test_get_missing_id(self, client: httpx.AsyncClient):
        payload = _rpc("tasks/get", {})
        resp = await client.post("/", json=payload)
        body = resp.json()
        assert body["error"]["code"] == -32602


class TestMultiTurn:
    async def test_context_id_creates_new_task(self, client: httpx.AsyncClient):
        payload = _send_msg("test-task", {"turn": 1}, context_id="ctx-001")
        resp = await client.post("/", json=payload)
        body = resp.json()
        assert body["result"]["contextId"] == "ctx-001"
        assert body["result"]["status"]["state"] == "completed"

    async def test_context_id_resumes_task(self, client: httpx.AsyncClient):
        # Turn 1
        payload1 = _send_msg("test-task", {"turn": 1}, context_id="ctx-002")
        resp1 = await client.post("/", json=payload1)
        task_id = resp1.json()["result"]["id"]

        # Turn 2 with same context
        payload2 = _send_msg("test-task", {"turn": 2}, context_id="ctx-002")
        resp2 = await client.post("/", json=payload2)
        body2 = resp2.json()

        # Same task ID should be reused
        assert body2["result"]["id"] == task_id
        # History should have both messages
        assert len(body2["result"]["history"]) == 2

    async def test_different_context_ids_create_different_tasks(self, client: httpx.AsyncClient):
        payload1 = _send_msg("test-task", {"a": 1}, context_id="ctx-a")
        payload2 = _send_msg("test-task", {"b": 2}, context_id="ctx-b")
        resp1 = await client.post("/", json=payload1)
        resp2 = await client.post("/", json=payload2)
        assert resp1.json()["result"]["id"] != resp2.json()["result"]["id"]


class TestLRUEviction:
    async def test_eviction(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card, max_tasks=3)

        async def handler(task: Task, input_data: dict) -> Artifact:
            return Artifact(name="r", parts=[Part(structured_data=input_data)])

        server.register_handler("test-task", handler)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            task_ids = []
            for i in range(5):
                resp = await client.post("/", json=_send_msg("test-task", {"i": i}))
                task_ids.append(resp.json()["result"]["id"])

            # First two should be evicted
            for old_id in task_ids[:2]:
                resp = await client.post("/", json=_rpc("tasks/get", {"id": old_id}))
                assert resp.json()["error"]["code"] == -32602

            # Last three should still exist
            for new_id in task_ids[2:]:
                resp = await client.post("/", json=_rpc("tasks/get", {"id": new_id}))
                assert "result" in resp.json()


class TestErrorHandling:
    async def test_invalid_json(self, client: httpx.AsyncClient):
        resp = await client.post(
            "/",
            content=b"not json",
            headers={"content-type": "application/json"},
        )
        body = resp.json()
        assert body["error"]["code"] == -32700

    async def test_invalid_jsonrpc(self, client: httpx.AsyncClient):
        resp = await client.post("/", json={"not": "valid"})
        body = resp.json()
        assert body["error"]["code"] == -32600

    async def test_method_not_found(self, client: httpx.AsyncClient):
        payload = _rpc("nonexistent/method", {})
        resp = await client.post("/", json=payload)
        body = resp.json()
        assert body["error"]["code"] == -32601

    async def test_handler_exception(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card)

        async def failing_handler(task: Task, input_data: dict) -> Artifact:
            raise RuntimeError("boom")

        server.register_handler("test-task", failing_handler)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/", json=_send_msg("test-task", {}))
            body = resp.json()
            # Handler failures result in a completed response with failed task
            result = body["result"]
            assert result["status"]["state"] == "failed"


class TestMessageStream:
    """Tests for the message/stream SSE endpoint."""

    @pytest.fixture()
    def streaming_server(self, sample_agent_card: AgentCard) -> A2AServer:
        server = A2AServer(sample_agent_card)

        async def stream_handler(task: Task, input_data: dict) -> AsyncIterator[Part]:
            for i in range(3):
                yield Part(text=f"chunk-{i}")

        server.register_streaming_handler("test-task", stream_handler)
        return server

    @pytest.fixture()
    def streaming_client(self, streaming_server: A2AServer):
        transport = httpx.ASGITransport(app=streaming_server.app)
        return httpx.AsyncClient(transport=transport, base_url="http://test")

    async def test_stream_yields_update_and_complete_events(
        self, streaming_client: httpx.AsyncClient,
    ):
        payload = _stream_msg("test-task", {"key": "value"})
        resp = await streaming_client.post("/", json=payload)
        assert resp.status_code == 200

        events = _parse_sse(resp.text)
        update_events = [e for e in events if e["event"] == "update"]
        complete_events = [e for e in events if e["event"] == "complete"]

        assert len(update_events) == 3
        for i, ev in enumerate(update_events):
            assert ev["data"]["text"] == f"chunk-{i}"

        assert len(complete_events) == 1
        task_data = complete_events[0]["data"]
        assert task_data["status"]["state"] == "completed"
        assert len(task_data["artifacts"]) == 1
        assert len(task_data["artifacts"][0]["parts"]) == 3

    async def test_stream_sets_artifact_name(
        self, streaming_client: httpx.AsyncClient,
    ):
        payload = _stream_msg("test-task", {})
        resp = await streaming_client.post("/", json=payload)
        events = _parse_sse(resp.text)
        complete_event = [e for e in events if e["event"] == "complete"][0]
        assert complete_event["data"]["artifacts"][0]["name"] == "test-task-stream-result"

    async def test_stream_task_retrievable_after_completion(
        self, streaming_server: A2AServer,
    ):
        transport = httpx.ASGITransport(app=streaming_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Stream to create the task
            payload = _stream_msg("test-task", {"x": 1})
            resp = await client.post("/", json=payload)
            events = _parse_sse(resp.text)
            complete_event = [e for e in events if e["event"] == "complete"][0]
            task_id = complete_event["data"]["id"]

            # Retrieve via tasks/get
            get_resp = await client.post("/", json=_rpc("tasks/get", {"id": task_id}))
            body = get_resp.json()
            assert body["result"]["id"] == task_id
            assert body["result"]["status"]["state"] == "completed"

    async def test_stream_handler_error_yields_error_event(
        self, sample_agent_card: AgentCard,
    ):
        server = A2AServer(sample_agent_card)

        async def failing_stream(task: Task, input_data: dict) -> AsyncIterator[Part]:
            yield Part(text="ok")
            raise RuntimeError("stream-boom")

        server.register_streaming_handler("test-task", failing_stream)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/", json=_stream_msg("test-task", {}))
            events = _parse_sse(resp.text)

            update_events = [e for e in events if e["event"] == "update"]
            error_events = [e for e in events if e["event"] == "error"]

            # Should get the one successful chunk before the error
            assert len(update_events) == 1
            assert update_events[0]["data"]["text"] == "ok"

            assert len(error_events) == 1
            assert "stream-boom" in error_events[0]["data"]["error"]
            assert error_events[0]["data"]["task"]["status"]["state"] == "failed"

    async def test_stream_no_handler_returns_rpc_error(
        self, sample_agent_card: AgentCard,
    ):
        server = A2AServer(sample_agent_card)
        # Register only a non-streaming handler
        async def handler(task: Task, input_data: dict) -> Artifact:
            return Artifact(name="r", parts=[Part(text="ok")])

        server.register_handler("test-task", handler)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/", json=_stream_msg("test-task", {}))
            body = resp.json()
            assert body["error"]["code"] == -32602
            assert "No streaming handler" in body["error"]["message"]

    async def test_send_to_streaming_only_handler_returns_error(
        self, sample_agent_card: AgentCard,
    ):
        server = A2AServer(sample_agent_card)

        async def stream_handler(task: Task, input_data: dict) -> AsyncIterator[Part]:
            yield Part(text="chunk")

        server.register_streaming_handler("test-task", stream_handler)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Try message/send against a streaming-only handler
            resp = await client.post("/", json=_send_msg("test-task", {}))
            body = resp.json()
            assert body["error"]["code"] == -32602
            assert "only supports streaming" in body["error"]["message"]

    async def test_register_streaming_handler_enables_capability(
        self, sample_agent_card: AgentCard,
    ):
        server = A2AServer(sample_agent_card)
        assert server.agent_card.capabilities.get("streaming") is False

        async def stream_handler(task: Task, input_data: dict) -> AsyncIterator[Part]:
            yield Part(text="chunk")

        server.register_streaming_handler("test-task", stream_handler)
        assert server.agent_card.capabilities["streaming"] is True

    async def test_stream_with_context_id(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card)

        async def stream_handler(task: Task, input_data: dict) -> AsyncIterator[Part]:
            yield Part(text="hello")

        server.register_streaming_handler("test-task", stream_handler)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/", json=_stream_msg("test-task", {}, context_id="ctx-stream-1"),
            )
            events = _parse_sse(resp.text)
            complete_event = [e for e in events if e["event"] == "complete"][0]
            assert complete_event["data"]["contextId"] == "ctx-stream-1"

    async def test_stream_with_structured_data_parts(
        self, sample_agent_card: AgentCard,
    ):
        server = A2AServer(sample_agent_card)

        async def stream_handler(task: Task, input_data: dict) -> AsyncIterator[Part]:
            yield Part(structured_data={"progress": 50})
            yield Part(structured_data={"progress": 100})

        server.register_streaming_handler("test-task", stream_handler)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/", json=_stream_msg("test-task", {}))
            events = _parse_sse(resp.text)
            updates = [e for e in events if e["event"] == "update"]
            assert len(updates) == 2
            assert updates[0]["data"]["structuredData"]["progress"] == 50
            assert updates[1]["data"]["structuredData"]["progress"] == 100
