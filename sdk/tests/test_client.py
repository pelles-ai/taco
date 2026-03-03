"""Tests for caip.client — CAIPClient async A2A client."""

from __future__ import annotations

import httpx
import pytest

from caip.client import CAIPClient, CAIPClientError, RpcError
from caip.models import AgentCard
from caip.server import A2AServer


@pytest.fixture()
def test_client(sample_server: A2AServer):
    """CAIPClient backed by an ASGI transport to the test server."""
    transport = httpx.ASGITransport(app=sample_server.app)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return CAIPClient(agent_url="http://test", http_client=http_client)


class TestDiscover:
    async def test_discover_returns_agent_card(self, test_client: CAIPClient):
        card = await test_client.discover()
        assert isinstance(card, AgentCard)
        assert card.name == "Test Agent"

    async def test_discover_caches(self, test_client: CAIPClient):
        assert test_client.agent_card is None
        await test_client.discover()
        assert test_client.agent_card is not None
        assert test_client.agent_card.name == "Test Agent"


class TestSendMessage:
    async def test_returns_completed_task(self, test_client: CAIPClient):
        task = await test_client.send_message("test-task", {"key": "value"})
        assert task.status.state.value == "completed"
        assert task.artifacts[0].parts[0].structured_data == {"key": "value"}

    async def test_with_context_id(self, test_client: CAIPClient):
        task = await test_client.send_message(
            "test-task", {"turn": 1}, context_id="ctx-test",
        )
        assert task.context_id == "ctx-test"


class TestGetTask:
    async def test_get_existing_task(self, test_client: CAIPClient):
        sent = await test_client.send_message("test-task", {"a": 1})
        fetched = await test_client.get_task(sent.id)
        assert fetched.id == sent.id
        assert fetched.status.state.value == "completed"


class TestCancelTask:
    async def test_cancel_task(self, test_client: CAIPClient):
        sent = await test_client.send_message("test-task", {"a": 1})
        canceled = await test_client.cancel_task(sent.id)
        assert canceled.status.state.value == "canceled"


class TestRunTask:
    async def test_run_task_returns_dict(self, test_client: CAIPClient):
        result = await test_client.run_task(
            task_type="test-task", input_data={"x": 42},
        )
        assert isinstance(result, dict)
        assert result["status"]["state"] == "completed"


class TestRpcError:
    async def test_unknown_task_type(self, test_client: CAIPClient):
        with pytest.raises(RpcError) as exc_info:
            await test_client.send_message("nonexistent", {})
        assert exc_info.value.code == -32602

    async def test_rpc_error_is_caip_client_error(self):
        err = RpcError(code=-1, message="test")
        assert isinstance(err, CAIPClientError)


class TestContextManager:
    async def test_async_with(self, sample_server: A2AServer):
        transport = httpx.ASGITransport(app=sample_server.app)
        http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
        async with CAIPClient(agent_url="http://test", http_client=http_client) as client:
            card = await client.discover()
            assert card.name == "Test Agent"

    async def test_close_without_context_manager(self, sample_server: A2AServer):
        transport = httpx.ASGITransport(app=sample_server.app)
        http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
        client = CAIPClient(agent_url="http://test", http_client=http_client)
        task = await client.send_message("test-task", {"a": 1})
        assert task.status.state.value == "completed"
        await client.close()
