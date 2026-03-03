"""Tests for caip.registry — AgentRegistry in-memory discovery."""

from __future__ import annotations

import pytest

from caip.models import (
    AgentCard,
    AgentConstructionExt,
    AgentSkill,
    SkillConstructionExt,
)
from caip.registry import AgentRegistry


def _make_card(
    name: str,
    trade: str,
    task_types: list[str],
    csi_divisions: list[str] | None = None,
    project_types: list[str] | None = None,
) -> AgentCard:
    return AgentCard(
        name=name,
        description=f"Agent: {name}",
        url=f"http://localhost/{name.lower().replace(' ', '-')}",
        skills=[
            AgentSkill(
                id=f"skill-{tt}",
                name=f"Skill for {tt}",
                description=f"Handles {tt}",
                x_construction=SkillConstructionExt(
                    task_type=tt,
                    output_schema=f"{tt}-v1",
                ),
            )
            for tt in task_types
        ],
        x_construction=AgentConstructionExt(
            trade=trade,
            csi_divisions=csi_divisions or [],
            project_types=project_types or [],
        ),
    )


@pytest.fixture()
def registry() -> AgentRegistry:
    reg = AgentRegistry()
    reg.register_card(
        "http://localhost:8001",
        _make_card("Estimator", "mechanical", ["estimate"], ["23"], ["commercial"]),
    )
    reg.register_card(
        "http://localhost:8002",
        _make_card("Supplier", "multi-trade", ["quote"], ["22", "23"], ["commercial", "healthcare"]),
    )
    reg.register_card(
        "http://localhost:8003",
        _make_card("RFI Agent", "electrical", ["rfi"], ["26"], ["education"]),
    )
    return reg


class TestFind:
    def test_find_by_trade(self, registry: AgentRegistry):
        results = registry.find(trade="mechanical")
        assert len(results) == 1
        assert results[0].name == "Estimator"

    def test_find_by_task_type(self, registry: AgentRegistry):
        results = registry.find(task_type="quote")
        assert len(results) == 1
        assert results[0].name == "Supplier"

    def test_find_by_csi_division(self, registry: AgentRegistry):
        results = registry.find(csi_division="23")
        assert len(results) == 2
        names = {r.name for r in results}
        assert "Estimator" in names
        assert "Supplier" in names

    def test_find_by_project_type(self, registry: AgentRegistry):
        results = registry.find(project_type="healthcare")
        assert len(results) == 1
        assert results[0].name == "Supplier"

    def test_find_combined_filters(self, registry: AgentRegistry):
        results = registry.find(trade="multi-trade", csi_division="23")
        assert len(results) == 1
        assert results[0].name == "Supplier"

    def test_find_no_matches(self, registry: AgentRegistry):
        results = registry.find(trade="civil")
        assert results == []

    def test_find_all(self, registry: AgentRegistry):
        results = registry.find()
        assert len(results) == 3


class TestListAgents:
    def test_list_all(self, registry: AgentRegistry):
        agents = registry.list_agents()
        assert len(agents) == 3

    def test_list_empty(self):
        reg = AgentRegistry()
        assert reg.list_agents() == []


class TestRemove:
    def test_remove_existing(self, registry: AgentRegistry):
        result = registry.remove("http://localhost:8001")
        assert result is True
        assert len(registry.list_agents()) == 2

    def test_remove_nonexistent(self, registry: AgentRegistry):
        result = registry.remove("http://localhost:9999")
        assert result is False
        assert len(registry.list_agents()) == 3

    def test_remove_trailing_slash(self, registry: AgentRegistry):
        result = registry.remove("http://localhost:8001/")
        assert result is True


class TestRegisterCard:
    def test_direct_registration(self):
        reg = AgentRegistry()
        card = _make_card("Test", "mechanical", ["test"])
        reg.register_card("http://localhost:5000", card)
        assert len(reg.list_agents()) == 1
        assert reg.list_agents()[0].name == "Test"
