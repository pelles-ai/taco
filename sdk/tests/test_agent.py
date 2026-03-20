"""Tests for taco.agent — TacoAgent bidirectional agent."""

from __future__ import annotations

import json
import os
import tempfile

import httpx
import pytest

from taco._compat import make_artifact, make_data_part
from taco.agent import TacoAgent
from taco.agent_card import ConstructionAgentCard, ConstructionSkill
from taco.types import Artifact, InMemoryTaskStore, Task


@pytest.fixture()
def construction_card() -> ConstructionAgentCard:
    return ConstructionAgentCard(
        name="Test Agent",
        description="A test agent",
        url="http://localhost:9999",
        trade="electrical",
        csi_divisions=["26"],
        skills=[
            ConstructionSkill(
                id="test-task",
                name="Test Task",
                description="A test task",
                task_type="test-task",
                output_schema="test-v1",
            ),
        ],
    )


class TestTacoAgentBasics:
    def test_creates_server(self, construction_card: ConstructionAgentCard):
        agent = TacoAgent(construction_card)
        assert agent.app is not None
        assert agent.server is not None
        assert agent.agent_card is construction_card

    def test_register_handler(self, construction_card: ConstructionAgentCard):
        agent = TacoAgent(construction_card)

        async def handler(task: Task, input_data: dict) -> Artifact:
            return make_artifact(parts=[make_data_part(input_data)])

        agent.register_handler("test-task", handler)
        assert "test-task" in agent.server._executor._handlers

    def test_no_peers_by_default(self, construction_card: ConstructionAgentCard):
        agent = TacoAgent(construction_card)
        assert agent.registry is None

    def test_enable_monitor_flag(self, construction_card: ConstructionAgentCard):
        agent = TacoAgent(construction_card, enable_monitor=True)
        assert agent._has_monitor is True

    def test_disable_monitor_by_default(self, construction_card: ConstructionAgentCard):
        agent = TacoAgent(construction_card)
        assert agent._has_monitor is False


class TestTacoAgentMonitorMount:
    async def test_monitor_routes_mounted(self, construction_card: ConstructionAgentCard):
        """When enable_monitor=True, /monitor routes should be accessible."""
        agent = TacoAgent(construction_card, enable_monitor=True)

        async def handler(task: Task, input_data: dict) -> Artifact:
            return make_artifact(parts=[make_data_part(input_data)])

        agent.register_handler("test-task", handler)

        transport = httpx.ASGITransport(app=agent.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Monitor info endpoint
            resp = await client.get("/monitor/api/info")
            assert resp.status_code == 200
            info = resp.json()
            assert info["agentName"] == "Test Agent"

            # Monitor events endpoint
            resp = await client.get("/monitor/api/events")
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)

            # Monitor HTML UI
            resp = await client.get("/monitor/")
            assert resp.status_code == 200
            assert "TACO Agent Monitor" in resp.text

    async def test_monitor_not_mounted_when_disabled(
        self, construction_card: ConstructionAgentCard
    ):
        """When enable_monitor is not set, /monitor should not exist."""
        agent = TacoAgent(construction_card)

        transport = httpx.ASGITransport(app=agent.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/monitor/api/info")
            assert resp.status_code == 404


class TestTacoAgentPeerLoading:
    def test_load_peers_from_list(self, construction_card: ConstructionAgentCard):
        urls = ["http://localhost:8001", "http://localhost:8002"]
        result = TacoAgent._load_peers(urls)
        assert result == urls

    def test_load_peers_from_yaml(self, construction_card: ConstructionAgentCard):
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
        ) as f:
            f.write("agents:\n  - url: http://localhost:8001\n  - url: http://localhost:8002\n")
            f.flush()
            path = f.name

        try:
            result = TacoAgent._load_peers(path)
            assert result == ["http://localhost:8001", "http://localhost:8002"]
        finally:
            os.unlink(path)

    def test_load_peers_from_json(self, construction_card: ConstructionAgentCard):
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            json.dump({"agents": [{"url": "http://localhost:9001"}]}, f)
            f.flush()
            path = f.name

        try:
            result = TacoAgent._load_peers(path)
            assert result == ["http://localhost:9001"]
        finally:
            os.unlink(path)


class TestTacoAgentTaskStore:
    def test_task_store_forwarded(self, construction_card: ConstructionAgentCard):
        """Passing task_store to TacoAgent should forward to the underlying server."""
        custom_store = InMemoryTaskStore()
        agent = TacoAgent(construction_card, task_store=custom_store)
        assert agent.server._task_store is custom_store

    def test_default_task_store(self, construction_card: ConstructionAgentCard):
        """Without task_store, the server should use InMemoryTaskStore."""
        agent = TacoAgent(construction_card)
        assert isinstance(agent.server._task_store, InMemoryTaskStore)


class TestSendToPeerErrors:
    async def test_no_peers_raises(self, construction_card: ConstructionAgentCard):
        agent = TacoAgent(construction_card)
        with pytest.raises(ValueError, match="No peers configured"):
            await agent.send_to_peer("data-query", {"query": "test"})
