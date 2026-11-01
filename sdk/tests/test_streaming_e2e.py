"""End-to-end streaming tests against a real uvicorn server.

``httpx.ASGITransport`` buffers whole responses, so these tests run the app
under uvicorn and read the SSE stream over a socket.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator

import pytest

from taco import (
    A2AServer,
    ConstructionAgentCard,
    ConstructionSkill,
    Part,
    TacoClient,
    Task,
    make_artifact,
    make_data_part,
    make_text_part,
)

CHUNK_DELAY = 0.3


def _card() -> ConstructionAgentCard:
    return ConstructionAgentCard(
        name="Streaming Agent",
        url="http://127.0.0.1",
        trade="mechanical",
        csi_divisions=["23"],
        skills=[
            ConstructionSkill(
                id="estimate",
                task_type="estimate",
                input_schema="bom-v1",
                output_schema="estimate-v1",
            )
        ],
    )


async def _slow_stream(task: Task, input_data: dict) -> AsyncIterator[Part]:
    for i in range(3):
        yield make_text_part(f"chunk {i}")
        await asyncio.sleep(CHUNK_DELAY)


async def _collect(base_url: str) -> list[tuple[float, dict]]:
    """Stream an estimate and return (arrival time, event data) pairs."""
    events: list[tuple[float, dict]] = []
    start = time.monotonic()
    async with TacoClient(agent_url=base_url) as client:
        async for event in client.stream_message("estimate", {"lineItems": []}):
            events.append((time.monotonic() - start, event["data"]))
    return events


def _results(events: list[tuple[float, dict]]) -> list[dict]:
    return [data["result"] for _, data in events if isinstance(data, dict) and "result" in data]


@pytest.mark.parametrize("enable_monitor", [False, True])
async def test_streaming_handler_registered_after_init_streams(live_server, enable_monitor):
    """The documented pattern: build the server, then register a stream handler."""
    server = A2AServer(_card().to_a2a(), enable_monitor=enable_monitor)
    server.register_streaming_handler("estimate", _slow_stream)

    async with live_server(server.app) as base_url:
        events = await _collect(base_url)

    results = _results(events)
    errors = [data for _, data in events if isinstance(data, dict) and "error" in data]
    assert not errors, errors

    chunks = [r for r in results if r.get("kind") == "artifact-update"]
    texts = [p["text"] for r in chunks for p in r["artifact"]["parts"] if p.get("kind") == "text"]
    assert texts[:3] == ["chunk 0", "chunk 1", "chunk 2"]

    final = results[-1]
    assert final["kind"] == "status-update"
    assert final["status"]["state"] == "completed"
    assert final["final"] is True

    # Chunks must arrive as they are produced, not all at the end.
    first_chunk_at = next(t for t, data in events if data.get("result", {}).get("append") is False)
    last_event_at = events[-1][0]
    assert last_event_at - first_chunk_at >= 2 * CHUNK_DELAY * 0.8


async def test_card_and_handler_agree_on_streaming(live_server):
    server = A2AServer(_card().to_a2a())
    server.register_streaming_handler("estimate", _slow_stream)

    async with live_server(server.app) as base_url, TacoClient(agent_url=base_url) as client:
        card = await client.discover()
    assert card.capabilities.streaming is True
    assert server._a2a_card_pb.capabilities.streaming is True


async def test_stream_prefers_streaming_handler_and_send_prefers_regular(live_server):
    """With both handler kinds registered, each request style gets its own."""
    server = A2AServer(_card().to_a2a())

    async def regular(task: Task, input_data: dict):
        return make_artifact(parts=[make_data_part({"via": "regular"})], name="result")

    async def streaming(task: Task, input_data: dict) -> AsyncIterator[Part]:
        yield make_data_part({"via": "streaming"})

    server.register_handler("estimate", regular)
    server.register_streaming_handler("estimate", streaming)

    async with live_server(server.app) as base_url:
        async with TacoClient(agent_url=base_url) as client:
            sent = await client.send_message("estimate", {})
        streamed = _results(await _collect(base_url))

    assert sent.artifacts[0].parts[0].root.data == {"via": "regular"}
    stream_data = [
        p["data"]
        for r in streamed
        if r.get("kind") == "artifact-update"
        for p in r["artifact"]["parts"]
        if p.get("kind") == "data"
    ]
    assert stream_data and all(d == {"via": "streaming"} for d in stream_data)
