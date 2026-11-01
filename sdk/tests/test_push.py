"""Push notifications reach registered webhooks (taco.push)."""

from __future__ import annotations

import asyncio
import json

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from taco import (
    A2AServer,
    ConstructionAgentCard,
    ConstructionSkill,
    TacoClient,
    make_artifact,
    make_data_part,
)
from taco.push import is_public_http_url
from taco.types import Artifact, Task


def _receiver() -> tuple[Starlette, list[tuple[dict, bytes]]]:
    received: list[tuple[dict, bytes]] = []

    async def hook(request: Request) -> JSONResponse:
        received.append((dict(request.headers), await request.body()))
        return JSONResponse({"ok": True})

    return Starlette(routes=[Route("/hook", hook, methods=["POST"])]), received


def _agent(**kwargs) -> A2AServer:
    card = ConstructionAgentCard(
        name="Pusher",
        url="http://test",
        trade="electrical",
        csi_divisions=["26"],
        skills=[ConstructionSkill(id="e", task_type="estimate", output_schema="estimate-v1")],
    ).to_a2a()
    card.capabilities.push_notifications = True
    server = A2AServer(card, **kwargs)

    async def slow(task: Task, input_data: dict) -> Artifact:
        await asyncio.sleep(0.5)  # time to register the webhook first
        return make_artifact(parts=[make_data_part({"count": 120, "ratio": 0.5})])

    server.register_handler("estimate", slow)
    return server


async def _run(live_server, server: A2AServer, wait: float) -> list[tuple[dict, bytes]]:
    receiver, received = _receiver()
    async with (
        live_server(receiver) as hook_base,
        live_server(server.app) as agent_url,
        TacoClient(agent_url=agent_url) as client,
    ):
        task = await client.send_message("estimate", {}, return_immediately=True)
        await client.create_push_config(task.id, f"{hook_base}/hook", token="hook-secret")
        deadline = asyncio.get_running_loop().time() + wait
        while asyncio.get_running_loop().time() < deadline:
            if any(b'"completed"' in body or b"COMPLETED" in body for _, body in received):
                break
            await asyncio.sleep(0.1)
    return received


async def test_webhook_receives_events_with_integers(live_server):
    received = await _run(live_server, _agent(allow_private_push_urls=True), wait=5.0)

    assert received, "no push notification was delivered"
    assert all(h.get("x-a2a-notification-token") == "hook-secret" for h, _ in received)
    bodies = b"".join(body for _, body in received)
    assert b"120.0" not in bodies
    artifact_events = [json.loads(b) for _, b in received if b"count" in b]
    assert artifact_events, bodies[:500]
    assert b'"count":120' in bodies.replace(b" ", b"")


async def test_private_webhook_urls_are_refused_by_default(live_server, caplog):
    with caplog.at_level("WARNING", logger="taco.push"):
        received = await _run(live_server, _agent(), wait=1.5)
    assert received == []
    assert any("not a public" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize(
    ("url", "public"),
    [
        ("http://8.8.8.8/hook", True),
        ("https://1.1.1.1/hook", True),
        ("http://127.0.0.1:9000/hook", False),
        ("http://10.0.0.5/hook", False),
        ("http://192.168.1.10/hook", False),
        ("http://169.254.169.254/latest/meta-data", False),
        ("http://100.64.0.1/hook", False),
        ("http://[::1]/hook", False),
        ("http://[::ffff:127.0.0.1]/hook", False),
        ("ftp://8.8.8.8/hook", False),
        ("not a url", False),
    ],
)
async def test_is_public_http_url(url, public):
    assert await is_public_http_url(url) is public
