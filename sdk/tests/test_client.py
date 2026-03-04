"""Tests for taco.client — TacoClient async A2A client."""

from __future__ import annotations

import httpx
import pytest

from taco.client import TacoClient, TacoClientError, RpcError
from taco.types import AgentCard
from taco._compat import extract_structured_data
from taco.server import A2AServer


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
            "test-task", {"turn": 1}, context_id="ctx-test",
        )
        # A2A SDK manages context_id — verify the task has one
        assert task.context_id is not None


class TestGetTask:
    async def test_get_existing_task(self, test_client: TacoClient):
        sent = await test_client.send_message("test-task", {"a": 1})
        fetched = await test_client.get_task(sent.id)
        assert fetched.id == sent.id
        assert fetched.status.state == "completed"


class TestCancelTask:
    async def test_cancel_completed_task_raises(self, test_client: TacoClient):
        """A2A SDK correctly rejects cancellation of completed tasks."""
        sent = await test_client.send_message("test-task", {"a": 1})
        with pytest.raises(RpcError):
            await test_client.cancel_task(sent.id)


class TestRunTask:
    async def test_run_task_returns_dict(self, test_client: TacoClient):
        result = await test_client.run_task(
            task_type="test-task", input_data={"x": 42},
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
