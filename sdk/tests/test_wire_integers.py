"""Whole numbers go over the wire as JSON integers, not ``120.0``.

A2A v1 carries DataPart payloads as protobuf Struct (all numbers are
doubles); the server rewrites its JSON-RPC responses and SSE events, and the
client restores integers in whatever it receives.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx
import pytest

from taco import (
    A2AServer,
    ConstructionAgentCard,
    ConstructionSkill,
    Part,
    TacoClient,
    make_artifact,
    make_data_part,
)
from taco.types import Artifact, Task

PAYLOAD = {"projectId": "PRJ-1", "count": 120, "ratio": 0.5, "items": [{"qty": 3}]}


def _server(**kwargs) -> A2AServer:
    server = A2AServer(
        ConstructionAgentCard(
            name="Wire",
            url="http://test",
            trade="electrical",
            csi_divisions=["26"],
            skills=[
                ConstructionSkill(id="estimate", task_type="estimate", output_schema="estimate-v1")
            ],
        ),
        **kwargs,
    )

    async def echo(task: Task, input_data: dict) -> Artifact:
        return make_artifact(parts=[make_data_part(input_data)], name="echo")

    async def stream(task: Task, input_data: dict) -> AsyncIterator[Part]:
        yield make_data_part(input_data)

    server.register_handler("estimate", echo)
    server.register_streaming_handler("estimate", stream)
    return server


def _rpc(method: str, params: dict) -> dict:
    return {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}


def _send_params() -> dict:
    return {
        "message": {
            "role": "user",
            "parts": [{"kind": "data", "data": PAYLOAD}],
            "messageId": "m-1",
        },
        "metadata": {"taskType": "estimate"},
    }


def _assert_ints(raw: bytes) -> None:
    assert b'"count":120' in raw.replace(b" ", b""), raw[:400]
    assert b"120.0" not in raw
    assert b'"ratio":0.5' in raw.replace(b" ", b"")


@pytest.mark.parametrize("enable_monitor", [False, True])
async def test_send_get_and_stream_responses_carry_integers(live_server, enable_monitor):
    server = _server(enable_monitor=enable_monitor)
    async with live_server(server.app) as base_url, httpx.AsyncClient() as http:
        sent = await http.post(f"{base_url}/", json=_rpc("message/send", _send_params()))
        _assert_ints(sent.content)
        task_id = sent.json()["result"]["id"]

        got = await http.post(f"{base_url}/", json=_rpc("tasks/get", {"id": task_id}))
        _assert_ints(got.content)

        async with http.stream(
            "POST", f"{base_url}/", json=_rpc("message/stream", _send_params())
        ) as resp:
            raw = b"".join([chunk async for chunk in resp.aiter_bytes()])
        assert raw.count(b"data:") >= 3
        _assert_ints(raw)
        for line in raw.splitlines():
            if line.startswith(b"data:"):
                json.loads(line[len(b"data:") :])  # every event is still valid JSON


async def test_client_restores_integers_from_list_tasks():
    server = _server()
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")
    client = TacoClient(agent_url="http://test", http_client=http)

    sent = await client.send_message("estimate", PAYLOAD)
    assert sent.artifacts[0].parts[0].root.data == PAYLOAD
    assert isinstance(sent.artifacts[0].parts[0].root.data["count"], int)

    tasks, _ = await client.list_tasks(include_artifacts=True)
    for data in (
        tasks[0].history[0].parts[0].root.data,
        tasks[0].artifacts[0].parts[0].root.data,
    ):
        assert data == PAYLOAD
        assert isinstance(data["count"], int)
        assert isinstance(data["items"][0]["qty"], int)

    without, _ = await client.list_tasks()
    assert not without[0].artifacts
