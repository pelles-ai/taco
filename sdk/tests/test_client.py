"""Tests for taco.client — TacoClient async A2A client."""

from __future__ import annotations

import httpx
import pytest

from taco._compat import extract_structured_data
from taco.client import RpcError, TacoClient, TacoClientError
from taco.server import A2AServer
from taco.types import AgentCard


@pytest.fixture()
def test_client(sample_server: A2AServer):
    """TacoClient backed by an ASGI transport to the test server."""
    transport = httpx.ASGITransport(app=sample_server.app)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return TacoClient(agent_url="http://test", http_client=http_client)


class TestDiscover:
    async def test_discover_returns_agent_card(self, test_client: TacoClient):
        card = await test_client.discover()
        assert isinstance(card, AgentCard)
        assert card.name == "Test Agent"

    async def test_discover_caches(self, test_client: TacoClient):
        assert test_client.agent_card is None
        await test_client.discover()
        assert test_client.agent_card is not None
        assert test_client.agent_card.name == "Test Agent"

    async def test_discover_falls_back_to_legacy_path(self):
        """When /.well-known/agent-card.json 404s, fall back to /.well-known/agent.json."""
        legacy_card = {
            "name": "Legacy Agent",
            "description": "Only serves the legacy well-known path",
            "url": "http://legacy",
            "defaultInputModes": ["application/json"],
            "defaultOutputModes": ["application/json"],
            "capabilities": {"streaming": False},
            "skills": [],
        }

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/.well-known/agent.json":
                return httpx.Response(200, json=legacy_card)
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(transport=transport, base_url="http://legacy")
        async with TacoClient(agent_url="http://legacy", http_client=http_client) as client:
            card = await client.discover()
            assert card.name == "Legacy Agent"


class TestSendMessage:
    async def test_returns_completed_task(self, test_client: TacoClient):
        task = await test_client.send_message("test-task", {"key": "value"})
        assert task.status.state == "completed"
        # Extract data from the artifact
        assert len(task.artifacts) >= 1
        parts = task.artifacts[0].parts
        assert len(parts) >= 1
        data = extract_structured_data(parts[0])
        assert data == {"key": "value"}

    async def test_with_context_id(self, test_client: TacoClient):
        task = await test_client.send_message(
            "test-task",
            {"turn": 1},
            context_id="ctx-test",
        )
        # A2A SDK manages context_id — verify the task has one
        assert task.context_id is not None


class TestGetTask:
    async def test_get_existing_task(self, test_client: TacoClient):
        sent = await test_client.send_message("test-task", {"a": 1})
        fetched = await test_client.get_task(sent.id)
        assert fetched.id == sent.id
        assert fetched.status.state == "completed"


class TestListTasks:
    async def test_returns_all_tasks(self, test_client: TacoClient):
        # Create three tasks
        sent = []
        for i in range(3):
            t = await test_client.send_message("test-task", {"i": i})
            sent.append(t.id)

        tasks, cursor = await test_client.list_tasks()
        assert {t.id for t in tasks} >= set(sent)
        # All present in one page, no continuation cursor
        assert cursor is None

    async def test_pagination_with_limit(self, test_client: TacoClient):
        for i in range(3):
            await test_client.send_message("test-task", {"i": i})

        first, cursor = await test_client.list_tasks(limit=2)
        assert len(first) == 2
        assert cursor is not None

        second, cursor2 = await test_client.list_tasks(cursor=cursor, limit=2)
        # second page should contain the remaining task(s) without
        # overlapping the first page
        assert {t.id for t in first}.isdisjoint({t.id for t in second})

    async def test_overrides_protocol_version_header(self):
        """list_tasks must send A2A-Version: 1.0 since ListTasks is v1-only."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": "1", "result": {"tasks": []}},
            )

        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
        async with TacoClient(agent_url="http://test", http_client=http_client) as client:
            await client.list_tasks()

        assert captured[0].headers.get("a2a-version") == "1.0"


class TestCancelTask:
    async def test_cancel_completed_task_raises(self, test_client: TacoClient):
        """A2A SDK correctly rejects cancellation of completed tasks."""
        sent = await test_client.send_message("test-task", {"a": 1})
        with pytest.raises(RpcError):
            await test_client.cancel_task(sent.id)


class TestRunTask:
    async def test_run_task_returns_dict(self, test_client: TacoClient):
        result = await test_client.run_task(
            task_type="test-task",
            input_data={"x": 42},
        )
        assert isinstance(result, dict)
        assert result["status"]["state"] == "completed"


class TestRpcError:
    async def test_rpc_error_is_taco_client_error(self):
        err = RpcError(code=-1, message="test")
        assert isinstance(err, TacoClientError)


class TestContextManager:
    async def test_async_with(self, sample_server: A2AServer):
        transport = httpx.ASGITransport(app=sample_server.app)
        http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
        async with TacoClient(agent_url="http://test", http_client=http_client) as client:
            card = await client.discover()
            assert card.name == "Test Agent"

    async def test_close_without_context_manager(self, sample_server: A2AServer):
        transport = httpx.ASGITransport(app=sample_server.app)
        http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
        client = TacoClient(agent_url="http://test", http_client=http_client)
        task = await client.send_message("test-task", {"a": 1})
        assert task.status.state == "completed"
        await client.close()


class TestRpcErrorDetails:
    def test_rpc_error_attributes(self):
        err = RpcError(code=-32600, message="Invalid Request", data={"detail": "missing method"})
        assert err.code == -32600
        assert err.rpc_message == "Invalid Request"
        assert err.data == {"detail": "missing method"}
        assert "-32600" in str(err)

    def test_rpc_error_without_data(self):
        err = RpcError(code=-1, message="test")
        assert err.data is None


class TestMessageParams:
    def test_message_params_format(self):
        params = TacoClient._message_params("estimate", {"x": 1}, context_id="ctx-1")
        assert params["metadata"]["taskType"] == "estimate"
        assert "message" in params
        assert params["contextId"] == "ctx-1"

    def test_message_params_no_context_id(self):
        params = TacoClient._message_params("estimate", {"x": 1})
        assert "contextId" not in params


class TestProtocolHeaders:
    """Verify A2A-Version is sent on every request."""

    async def test_a2a_version_header_on_rpc_call(self):
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": "1", "result": {}},
            )

        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
        async with TacoClient(agent_url="http://test", http_client=http_client) as client:
            await client._rpc_call("message/send", {})

        assert captured, "expected at least one request"
        assert captured[0].headers.get("a2a-version") == "0.3"

    async def test_a2a_version_header_on_discover(self):
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200,
                json={
                    "name": "Mock",
                    "description": "x",
                    "url": "http://test",
                    "defaultInputModes": ["application/json"],
                    "defaultOutputModes": ["application/json"],
                    "capabilities": {"streaming": False},
                    "skills": [],
                },
            )

        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
        async with TacoClient(agent_url="http://test", http_client=http_client) as client:
            await client.discover()

        assert captured[0].headers.get("a2a-version") == "0.3"

    async def test_caller_headers_take_precedence(self):
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": "1", "result": {}},
            )

        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
        async with TacoClient(agent_url="http://test", http_client=http_client) as client:
            await client._rpc_call(
                "message/send",
                {},
                headers={"A2A-Version": "0.4-experimental"},
            )

        assert captured[0].headers.get("a2a-version") == "0.4-experimental"
