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


class TestPushNotificationConfigs:
    """CRUD over the v0.3 task/pushNotificationConfig RPCs."""

    @staticmethod
    def _make_mock_client(handler):
        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
        return TacoClient(agent_url="http://test", http_client=http_client)

    async def test_create_push_config_sends_correct_payload(self):
        captured: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "result": {
                        "taskId": "t-1",
                        "pushNotificationConfig": {
                            "id": "dashboard",
                            "url": "https://example.com/hook",
                        },
                    },
                },
            )

        async with self._make_mock_client(handler) as c:
            cfg = await c.create_push_config(
                "t-1",
                url="https://example.com/hook",
                config_id="dashboard",
            )

        payload = captured[0]
        assert payload["method"] == "tasks/pushNotificationConfig/set"
        assert payload["params"]["taskId"] == "t-1"
        assert payload["params"]["pushNotificationConfig"]["id"] == "dashboard"
        assert payload["params"]["pushNotificationConfig"]["url"] == "https://example.com/hook"
        assert cfg.id == "dashboard"
        assert cfg.url == "https://example.com/hook"

    async def test_list_push_configs_parses_array(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "result": [
                        {
                            "taskId": "t-1",
                            "pushNotificationConfig": {"id": "a", "url": "https://a"},
                        },
                        {
                            "taskId": "t-1",
                            "pushNotificationConfig": {"id": "b", "url": "https://b"},
                        },
                    ],
                },
            )

        async with self._make_mock_client(handler) as c:
            configs = await c.list_push_configs("t-1")

        assert [cfg.id for cfg in configs] == ["a", "b"]
        assert [cfg.url for cfg in configs] == ["https://a", "https://b"]

    async def test_get_push_config_by_id(self):
        captured: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "result": {
                        "taskId": "t-1",
                        "pushNotificationConfig": {"id": "audit", "url": "https://x"},
                    },
                },
            )

        async with self._make_mock_client(handler) as c:
            cfg = await c.get_push_config("t-1", "audit")

        payload = captured[0]
        assert payload["method"] == "tasks/pushNotificationConfig/get"
        assert payload["params"]["id"] == "t-1"
        assert payload["params"]["pushNotificationConfigId"] == "audit"
        assert cfg.id == "audit"

    async def test_delete_push_config(self):
        captured: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": "1", "result": None},
            )

        async with self._make_mock_client(handler) as c:
            await c.delete_push_config("t-1", "audit")

        payload = captured[0]
        assert payload["method"] == "tasks/pushNotificationConfig/delete"
        assert payload["params"]["id"] == "t-1"
        assert payload["params"]["pushNotificationConfigId"] == "audit"


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


class TestReferenceTaskIds:
    """``reference_task_ids`` threads follow-up tasks back to their predecessors."""

    async def test_message_params_includes_reference_task_ids(self):
        params = TacoClient._message_params(
            "rfi-response",
            {"answer": "use copper"},
            reference_task_ids=["t-rfi-original"],
        )
        msg = params["message"]
        # Pydantic alias serializes snake_case → camelCase
        assert msg["referenceTaskIds"] == ["t-rfi-original"]

    async def test_message_params_omits_field_when_absent(self):
        params = TacoClient._message_params("rfi-response", {"x": 1})
        assert "referenceTaskIds" not in params["message"]

    async def test_send_message_forwards_reference_task_ids(self):
        captured: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            payload = json.loads(request.content)
            captured.append(payload)
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "result": {
                        "id": "t-new",
                        "contextId": "c-1",
                        "status": {"state": "completed"},
                    },
                },
            )

        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
        async with TacoClient(agent_url="http://test", http_client=http_client) as client:
            await client.send_message(
                "rfi-response",
                {"answer": "yes"},
                reference_task_ids=["t-orig"],
            )

        sent_msg = captured[0]["params"]["message"]
        assert sent_msg["referenceTaskIds"] == ["t-orig"]


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


class TestReturnImmediately:
    """``return_immediately`` flips ``configuration.blocking=false`` on the wire."""

    def test_default_omits_configuration(self):
        params = TacoClient._message_params("estimate", {"x": 1})
        assert "configuration" not in params

    def test_true_sets_blocking_false(self):
        params = TacoClient._message_params("estimate", {"x": 1}, return_immediately=True)
        assert params["configuration"] == {"blocking": False}

    async def test_send_message_forwards_flag(self):
        captured: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "result": {
                        "id": "t-1",
                        "contextId": "c-1",
                        "status": {"state": "submitted"},
                    },
                },
            )

        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
        async with TacoClient(agent_url="http://test", http_client=http_client) as client:
            await client.send_message(
                "long-running",
                {"x": 1},
                return_immediately=True,
            )

        sent = captured[0]["params"]
        assert sent["configuration"] == {"blocking": False}


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
