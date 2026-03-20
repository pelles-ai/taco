"""Tests for taco.server — A2A server protocol implementation."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from taco._compat import (
    make_artifact,
    make_data_part,
    make_text_part,
)
from taco.server import A2AServer
from taco.task_store import JsonFileTaskStore
from taco.types import (
    AgentCard,
    Artifact,
    InMemoryTaskStore,
    Part,
    Task,
)


@pytest.fixture()
def client(sample_server: A2AServer):
    """HTTPX async client wired to the test server via ASGI transport."""
    transport = httpx.ASGITransport(app=sample_server.app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def _rpc(method: str, params: dict | None = None, rpc_id: str = "1") -> dict:
    return {"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params or {}}


def _msg_payload(
    method: str,
    task_type: str,
    input_data: dict,
    context_id: str | None = None,
) -> dict:
    """Build a JSON-RPC message/send or message/stream payload.

    Uses the A2A SDK message format with DataPart.
    """
    msg = {
        "role": "user",
        "parts": [{"kind": "data", "data": input_data}],
        "messageId": "test-msg-1",
    }
    params: dict = {
        "message": msg,
        "metadata": {"taskType": task_type},
    }
    if context_id:
        params["contextId"] = context_id
    return _rpc(method, params)


def _send_msg(task_type: str, input_data: dict, context_id: str | None = None) -> dict:
    return _msg_payload("message/send", task_type, input_data, context_id)


class TestAgentCardDiscovery:
    async def test_agent_card_endpoint(self, client: httpx.AsyncClient):
        # TACO serves its own card at /.well-known/agent-card.json
        resp = await client.get("/.well-known/agent-card.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Agent"
        assert data["url"] == "http://localhost:9999"

    async def test_agent_card_has_skills(self, client: httpx.AsyncClient):
        resp = await client.get("/.well-known/agent-card.json")
        data = resp.json()
        assert len(data["skills"]) == 1
        assert data["skills"][0]["x-construction"]["taskType"] == "test-task"

    async def test_agent_card_has_x_construction(self, client: httpx.AsyncClient):
        resp = await client.get("/.well-known/agent-card.json")
        data = resp.json()
        xc = data["x-construction"]
        assert xc["trade"] == "mechanical"
        assert "23" in xc["csiDivisions"]

    async def test_agent_card_also_at_old_path(self, client: httpx.AsyncClient):
        """A2A SDK also serves at /.well-known/agent.json for backward compat."""
        resp = await client.get("/.well-known/agent.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Agent"


class TestMessageSend:
    async def test_success(self, client: httpx.AsyncClient):
        payload = _send_msg("test-task", {"foo": "bar"})
        resp = await client.post("/", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["jsonrpc"] == "2.0"
        result = body["result"]
        assert result["status"]["state"] == "completed"
        # The echo handler returns input as DataPart
        artifacts = result["artifacts"]
        assert len(artifacts) >= 1
        parts = artifacts[0]["parts"]
        assert len(parts) >= 1
        # DataPart has 'data' key in A2A SDK format
        assert parts[0]["data"] == {"foo": "bar"}

    async def test_missing_task_type(self, client: httpx.AsyncClient):
        payload = _rpc(
            "message/send",
            {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "data", "data": {}}],
                    "messageId": "test-1",
                },
                "metadata": {},
            },
        )
        resp = await client.post("/", json=payload)
        body = resp.json()
        # With a single handler, it should auto-select
        assert "result" in body

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

    async def test_cancel_completed_task_returns_error(self, client: httpx.AsyncClient):
        """A2A SDK correctly rejects cancellation of already-completed tasks."""
        send_resp = await client.post("/", json=_send_msg("test-task", {"a": 1}))
        task_id = send_resp.json()["result"]["id"]

        cancel_payload = _rpc("tasks/cancel", {"id": task_id})
        resp = await client.post("/", json=cancel_payload)
        body = resp.json()
        assert "error" in body


class TestErrorHandling:
    async def test_invalid_json(self, client: httpx.AsyncClient):
        resp = await client.post(
            "/",
            content=b"not json",
            headers={"content-type": "application/json"},
        )
        body = resp.json()
        # A2A SDK returns error for invalid JSON
        assert "error" in body

    async def test_handler_exception(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card)

        async def failing_handler(task: Task, input_data: dict) -> Artifact:
            raise RuntimeError("boom")

        server.register_handler("test-task", failing_handler)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/", json=_send_msg("test-task", {}))
            body = resp.json()
            result = body["result"]
            assert result["status"]["state"] == "failed"

    async def test_wrong_task_type(self, sample_agent_card: AgentCard):
        """Sending a nonexistent taskType should return failed state."""
        server = A2AServer(sample_agent_card)

        async def noop_handler(task: Task, input_data: dict) -> Artifact:
            return make_artifact(parts=[make_data_part(input_data)])

        server.register_handler("real-task", noop_handler)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/", json=_send_msg("nonexistent", {}))
            body = resp.json()
            result = body["result"]
            assert result["status"]["state"] == "failed"


class TestStreamingHandler:
    async def test_streaming_handler_success(self, sample_agent_card: AgentCard):
        """Streaming handler yielding parts should complete with artifact."""
        server = A2AServer(sample_agent_card)

        async def stream_handler(task: Task, input_data: dict) -> AsyncIterator[Part]:
            yield make_text_part("chunk-1")
            yield make_text_part("chunk-2")

        server.register_streaming_handler("stream-task", stream_handler)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/", json=_send_msg("stream-task", {}))
            body = resp.json()
            result = body["result"]
            assert result["status"]["state"] == "completed"
            assert len(result["artifacts"]) >= 1

    async def test_streaming_handler_error(self, sample_agent_card: AgentCard):
        """Streaming handler that raises should result in failed state."""
        server = A2AServer(sample_agent_card)

        async def bad_stream(task: Task, input_data: dict) -> AsyncIterator[Part]:
            yield make_text_part("partial")
            raise RuntimeError("stream broke")

        server.register_streaming_handler("bad-stream", bad_stream)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/", json=_send_msg("bad-stream", {}))
            body = resp.json()
            result = body["result"]
            assert result["status"]["state"] == "failed"


class TestMultipleHandlers:
    async def test_multiple_handlers_missing_task_type(self, sample_agent_card: AgentCard):
        """With 2+ handlers and no taskType, should fail (not auto-select)."""
        server = A2AServer(sample_agent_card)

        async def handler_a(task: Task, input_data: dict) -> Artifact:
            return make_artifact(parts=[make_data_part({"from": "a"})])

        async def handler_b(task: Task, input_data: dict) -> Artifact:
            return make_artifact(parts=[make_data_part({"from": "b"})])

        server.register_handler("task-a", handler_a)
        server.register_handler("task-b", handler_b)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = _rpc(
                "message/send",
                {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "data", "data": {}}],
                        "messageId": "test-multi",
                    },
                    "metadata": {},
                },
            )
            resp = await client.post("/", json=payload)
            body = resp.json()
            result = body["result"]
            assert result["status"]["state"] == "failed"


class TestA2ASDKCardConversion:
    async def test_a2a_sdk_card_has_skills_and_capabilities(self, client: httpx.AsyncClient):
        """Verify /.well-known/agent.json (A2A SDK path) has skills, streaming, version."""
        resp = await client.get("/.well-known/agent.json")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["skills"]) >= 1
        assert data["skills"][0]["name"] == "Test Skill"
        assert "capabilities" in data
        assert "version" in data


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client: httpx.AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["agent"] == "Test Agent"
        assert "version" in data
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], float)

    async def test_health_lists_handlers(self, client: httpx.AsyncClient):
        resp = await client.get("/health")
        data = resp.json()
        assert "test-task" in data["handlers"]


class TestCORSBehavior:
    async def test_no_cors_by_default(self, sample_agent_card: AgentCard):
        """Without cors_origins, no CORS headers should be present."""
        server = A2AServer(sample_agent_card)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get(
                "/health",
                headers={"Origin": "http://example.com"},
            )
            assert resp.status_code == 200
            assert "access-control-allow-origin" not in resp.headers

    async def test_cors_with_explicit_wildcard(self, sample_agent_card: AgentCard):
        """With cors_origins=['*'], CORS headers should be present."""
        server = A2AServer(sample_agent_card, cors_origins=["*"])

        async def handler(task: Task, input_data: dict) -> Artifact:
            return make_artifact(parts=[make_data_part(input_data)])

        server.register_handler("test-task", handler)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get(
                "/health",
                headers={"Origin": "http://example.com"},
            )
            assert resp.status_code == 200
            assert resp.headers.get("access-control-allow-origin") == "*"


class TestAdminEndpoints:
    async def test_add_skill(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card, enable_admin=True)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/admin/skills",
                json={
                    "id": "new-skill",
                    "name": "New Skill",
                    "description": "A new skill",
                },
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"
            assert resp.json()["skillId"] == "new-skill"
            # Verify skill was added
            assert len(server.agent_card.skills) == 2

    async def test_remove_skill(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card, enable_admin=True)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.delete("/admin/skills/test-skill")
            assert resp.status_code == 200
            assert len(server.agent_card.skills) == 0

    async def test_remove_nonexistent_skill(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card, enable_admin=True)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.delete("/admin/skills/nonexistent")
            assert resp.status_code == 404

    async def test_list_skills(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card, enable_admin=True)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/admin/skills")
            assert resp.status_code == 200
            skills = resp.json()
            assert len(skills) == 1
            assert skills[0]["name"] == "Test Skill"


class TestAdminAuth:
    async def test_admin_auth_required(self, sample_agent_card: AgentCard):
        """Admin endpoints should return 401 without valid token."""
        server = A2AServer(sample_agent_card, enable_admin=True, admin_auth_token="secret-token")
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/admin/skills")
            assert resp.status_code == 401

    async def test_admin_auth_wrong_token(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card, enable_admin=True, admin_auth_token="secret-token")
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get(
                "/admin/skills",
                headers={"Authorization": "Bearer wrong-token"},
            )
            assert resp.status_code == 401

    async def test_admin_auth_valid_token(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card, enable_admin=True, admin_auth_token="secret-token")
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get(
                "/admin/skills",
                headers={"Authorization": "Bearer secret-token"},
            )
            assert resp.status_code == 200
            assert len(resp.json()) == 1

    async def test_admin_add_skill_with_auth(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card, enable_admin=True, admin_auth_token="secret-token")
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            # Without token — 401
            resp = await c.post(
                "/admin/skills",
                json={"id": "x", "name": "X", "description": "X"},
            )
            assert resp.status_code == 401

            # With token — 200
            resp = await c.post(
                "/admin/skills",
                json={"id": "x", "name": "X", "description": "X"},
                headers={"Authorization": "Bearer secret-token"},
            )
            assert resp.status_code == 200

    async def test_admin_remove_skill_with_auth(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card, enable_admin=True, admin_auth_token="secret-token")
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.delete("/admin/skills/test-skill")
            assert resp.status_code == 401

            resp = await c.delete(
                "/admin/skills/test-skill",
                headers={"Authorization": "Bearer secret-token"},
            )
            assert resp.status_code == 200

    async def test_no_auth_when_no_token_set(self, sample_agent_card: AgentCard):
        """Admin endpoints should work without auth when no token is configured."""
        server = A2AServer(sample_agent_card, enable_admin=True)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/admin/skills")
            assert resp.status_code == 200

    async def test_add_skill_invalid_data_returns_400(self, sample_agent_card: AgentCard):
        """POST /admin/skills with invalid data should return 400."""
        server = A2AServer(sample_agent_card, enable_admin=True)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/admin/skills",
                json={"not_a_valid_field": True},
            )
            assert resp.status_code == 400
            assert "error" in resp.json()

    async def test_add_skill_syncs_a2a_card(self, sample_agent_card: AgentCard):
        """Adding a skill should update the A2A SDK card at /.well-known/agent.json."""
        server = A2AServer(sample_agent_card, enable_admin=True)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            # Initial card has 1 skill
            resp = await c.get("/.well-known/agent.json")
            initial_skills = resp.json()["skills"]
            assert len(initial_skills) == 1

            # Add a skill
            await c.post(
                "/admin/skills",
                json={"id": "new-skill", "name": "New Skill", "description": "Added"},
            )

            # A2A SDK card should now reflect the new skill
            resp = await c.get("/.well-known/agent.json")
            updated_skills = resp.json()["skills"]
            assert len(updated_skills) == 2

    async def test_remove_skill_syncs_a2a_card(self, sample_agent_card: AgentCard):
        """Removing a skill should update the A2A SDK card at /.well-known/agent.json."""
        server = A2AServer(sample_agent_card, enable_admin=True)
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            # Remove the existing skill
            await c.delete("/admin/skills/test-skill")

            # A2A SDK card should now have 0 skills
            resp = await c.get("/.well-known/agent.json")
            updated_skills = resp.json()["skills"]
            assert len(updated_skills) == 0


class TestCustomTaskStore:
    async def test_custom_store_receives_tasks(self, sample_agent_card: AgentCard):
        """Passing a custom TaskStore to A2AServer should be used for task storage."""
        custom_store = InMemoryTaskStore()
        server = A2AServer(sample_agent_card, task_store=custom_store)

        async def echo_handler(task: Task, input_data: dict) -> Artifact:
            return make_artifact(parts=[make_data_part(input_data)])

        server.register_handler("test-task", echo_handler)

        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post("/", json=_send_msg("test-task", {"x": 1}))
            body = resp.json()
            task_id = body["result"]["id"]

            # The task should be in our custom store
            stored = await custom_store.get(task_id)
            assert stored is not None
            assert stored.id == task_id
            assert stored.status.state.value == "completed"

    def test_task_store_attribute(self, sample_agent_card: AgentCard):
        """A2AServer should expose _task_store attribute."""
        custom_store = InMemoryTaskStore()
        server = A2AServer(sample_agent_card, task_store=custom_store)
        assert server._task_store is custom_store

    def test_default_task_store(self, sample_agent_card: AgentCard):
        """Without task_store param, A2AServer should use InMemoryTaskStore."""
        server = A2AServer(sample_agent_card)
        assert isinstance(server._task_store, InMemoryTaskStore)


class TestJsonFileTaskStoreIntegration:
    async def test_end_to_end_persistence(self, sample_agent_card: AgentCard, tmp_path):
        """JsonFileTaskStore + A2AServer: task survives across store instances."""
        store_path = str(tmp_path / "tasks.json")
        store = JsonFileTaskStore(store_path)
        server = A2AServer(sample_agent_card, task_store=store)

        async def echo_handler(task: Task, input_data: dict) -> Artifact:
            return make_artifact(parts=[make_data_part(input_data)])

        server.register_handler("test-task", echo_handler)

        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post("/", json=_send_msg("test-task", {"key": "value"}))
            body = resp.json()
            task_id = body["result"]["id"]

        # Load a fresh store from the same file — task should be persisted
        store2 = JsonFileTaskStore(store_path)
        persisted = await store2.get(task_id)
        assert persisted is not None
        assert persisted.id == task_id
        assert persisted.status.state.value == "completed"
