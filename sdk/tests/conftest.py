"""Shared test fixtures for the TACO SDK test suite."""

from __future__ import annotations

import pytest

from taco.types import (
    AgentCapabilities,
    AgentCard,
    AgentConstructionExt,
    AgentSkill,
    Artifact,
    SkillConstructionExt,
    Task,
)
from taco._compat import make_artifact, make_data_part
from taco.server import A2AServer


@pytest.fixture()
def sample_agent_card() -> AgentCard:
    return AgentCard(
        name="Test Agent",
        description="A test agent for unit testing",
        url="http://localhost:9999",
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="test-skill",
                name="Test Skill",
                description="A test skill",
                tags=["test-task"],
                x_construction=SkillConstructionExt(
                    task_type="test-task",
                    input_schema="bom-v1",
                    output_schema="estimate-v1",
                ),
            ),
        ],
        x_construction=AgentConstructionExt(
            trade="mechanical",
            csi_divisions=["23"],
            project_types=["commercial", "healthcare"],
        ),
    )


@pytest.fixture()
def sample_server(sample_agent_card: AgentCard) -> A2AServer:
    server = A2AServer(sample_agent_card)

    async def echo_handler(task: Task, input_data: dict) -> Artifact:
        return make_artifact(
            parts=[make_data_part(input_data)],
            name="echo-result",
            description="Echoed input",
            metadata={"schema": "test-v1"},
        )

    server.register_handler("test-task", echo_handler)
    return server


@pytest.fixture()
def sample_bom() -> dict:
    return {
        "projectId": "PRJ-TEST-001",
        "trade": "mechanical",
        "csiDivision": "23",
        "lineItems": [
            {
                "id": "LI-001",
                "description": "Test item 1",
                "quantity": 10,
                "unit": "EA",
                "size": "4 inch",
                "material": "copper",
            },
            {
                "id": "LI-002",
                "description": "Test item 2",
                "quantity": 100,
                "unit": "LF",
                "material": "steel",
            },
        ],
        "metadata": {
            "generatedBy": "test",
            "generatedAt": "2026-01-01T00:00:00Z",
            "confidence": 0.9,
        },
    }
