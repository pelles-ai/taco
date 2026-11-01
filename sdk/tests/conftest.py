"""Shared test fixtures for the TACO SDK test suite."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest

from taco._compat import make_artifact, make_data_part
from taco.server import A2AServer
from taco.types import (
    AgentCapabilities,
    AgentCard,
    AgentConstructionExt,
    AgentSkill,
    Artifact,
    SkillConstructionExt,
    Task,
)


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


@asynccontextmanager
async def _serve_live(app: Any) -> AsyncIterator[str]:
    """Run ``app`` under a real uvicorn server on a free port; yield its URL.

    ``httpx.ASGITransport`` buffers whole responses, so streaming, lifespan
    and middleware behaviour need a real server to be tested honestly.
    """
    import uvicorn

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    serve_task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        while not server.started:
            if serve_task.done():
                serve_task.result()
            await asyncio.sleep(0.01)
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await serve_task
        sock.close()


@pytest.fixture()
def live_server():
    """Factory: ``async with live_server(app) as base_url: ...``."""
    return _serve_live
