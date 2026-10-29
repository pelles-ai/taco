"""Regression tests for client, peer and cancel behaviour.

These run against real servers (ASGI or uvicorn) and check what actually
happens on the wire, not only the request params the client builds.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from taco import (
    A2AServer,
    ConstructionAgentCard,
    ConstructionSkill,
    MessageReplyError,
    TacoAgent,
    TacoClient,
    make_artifact,
    make_data_part,
)
from taco.types import Artifact, Task


def _card(name: str = "Agent", url: str = "http://test", task_type: str = "estimate"):
    return ConstructionAgentCard(
        name=name,
        url=url,
        trade="electrical",
        csi_divisions=["26"],
        skills=[
            ConstructionSkill(
                id=f"{task_type}-skill", task_type=task_type, output_schema="estimate-v1"
            )
        ],
    )


async def _echo(task: Task, input_data: dict) -> Artifact:
    return make_artifact(parts=[make_data_part({"contextId": task.context_id, **input_data})])


def _asgi_client(app, **kwargs) -> TacoClient:
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
    return TacoClient(agent_url="http://test", http_client=http, **kwargs)


class TestContextId:
    async def test_context_id_reaches_the_server(self):
        server = A2AServer(_card().to_a2a())
        server.register_handler("estimate", _echo)
        client = _asgi_client(server.app)

        first = await client.send_message("estimate", {"turn": 1}, context_id="ctx-rfi-42")
        second = await client.send_message("estimate", {"turn": 2}, context_id="ctx-rfi-42")

        assert first.context_id == "ctx-rfi-42"
        assert second.context_id == "ctx-rfi-42"
        tasks, _ = await client.list_tasks(context_id="ctx-rfi-42")
        assert {t.id for t in tasks} == {first.id, second.id}

    def test_context_id_is_on_the_message(self):
        params = TacoClient._message_params("estimate", {}, context_id="ctx-1")
        assert params["message"]["contextId"] == "ctx-1"
        assert "contextId" not in params


class TestHeaders:
    async def test_default_and_per_call_headers_reach_every_call(self):
        seen: list[dict[str, str]] = []

        async def app(scope, receive, send):
            seen.append({k.decode(): v.decode() for k, v in scope["headers"]})
            body = (
                b'{"jsonrpc":"2.0","id":"1","result":{"id":"t1","contextId":"c1",'
                b'"kind":"task","status":{"state":"completed"}}}'
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": body})

        client = _asgi_client(app, headers={"Authorization": "Bearer default"})
        await client.get_task("t1")
        await client.cancel_task("t1", headers={"Authorization": "Bearer per-call"})
        await client.send_message("estimate", {})

        assert [h["authorization"] for h in seen] == [
            "Bearer default",
            "Bearer per-call",
            "Bearer default",
        ]
        assert all(h["a2a-version"] == "0.3" for h in seen)


class TestMessageReply:
    async def test_message_reply_raises_a_clear_error(self):
        async def app(scope, receive, send):
            body = (
                b'{"jsonrpc":"2.0","id":"1","result":{"kind":"message","role":"agent",'
                b'"messageId":"m1","parts":[{"kind":"text","text":"hi"}]}}'
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": body})

        with pytest.raises(MessageReplyError) as exc_info:
            await _asgi_client(app).send_message("estimate", {})
        assert exc_info.value.reply.parts[0].root.text == "hi"


class TestCancel:
    async def test_cancel_stops_the_handler(self):
        finished: list[str] = []

        async def slow(task: Task, input_data: dict) -> Artifact:
            await asyncio.sleep(1.0)
            finished.append(task.id)
            return make_artifact(parts=[make_data_part({"done": True})])

        server = A2AServer(_card().to_a2a())
        server.register_handler("estimate", slow)
        client = _asgi_client(server.app)

        task = await client.send_message("estimate", {}, return_immediately=True)
        await asyncio.sleep(0.1)
        canceled = await client.cancel_task(task.id)
        assert canceled.status.state.value == "canceled"

        await asyncio.sleep(1.3)
        assert finished == []
        final = await client.get_task(task.id)
        assert final.status.state.value == "canceled"
        assert not final.artifacts


class TestCardUrl:
    async def test_empty_card_url_is_served_as_the_request_address(self, live_server):
        card = ConstructionAgentCard(name="No URL", trade="electrical", csi_divisions=["26"])
        server = A2AServer(card.to_a2a())
        async with live_server(server.app) as base_url, TacoClient(agent_url=base_url) as client:
            served = await client.discover()
        assert served.url == base_url


class TestPeers:
    async def test_send_to_peer_uses_the_discovered_url(self, live_server):
        """A peer whose card has no url (or a wrong one) is still reachable."""
        supplier = TacoAgent(_card("Supplier", url="http://wrong.invalid:1", task_type="quote"))
        supplier.register_handler("quote", _echo)

        async with live_server(supplier.app) as supplier_url:
            estimator = TacoAgent(_card("Estimator"), peers=[supplier_url])
            async with live_server(estimator.app):
                task = await estimator.send_to_peer("quote", {"item": "pipe"})

        assert task.status.state.value == "completed"
        assert task.artifacts[0].parts[0].root.data["item"] == "pipe"

    async def test_peer_is_matched_by_x_construction_task_type(self, live_server):
        card = ConstructionAgentCard(
            name="Supplier",
            url="http://wrong.invalid:1",
            trade="electrical",
            csi_divisions=["26"],
            skills=[ConstructionSkill(id="price-it", task_type="quote", output_schema="quote-v1")],
        )
        card_a2a = card.to_a2a()
        card_a2a.skills[0].tags = []  # only the x-construction taskType names it
        supplier = A2AServer(card_a2a)
        supplier.register_handler("quote", _echo)

        async with live_server(supplier.app) as supplier_url:
            estimator = TacoAgent(_card("Estimator"), peers=[supplier_url])
            async with live_server(estimator.app):
                task = await estimator.send_to_peer("quote", {})
        assert task.status.state.value == "completed"

    async def test_agents_that_list_each_other_both_connect(self, live_server):
        """Startup no longer blocks on discovery, so mutual peers find each other."""
        import socket

        ports = []
        for _ in range(2):
            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            ports.append(s.getsockname()[1])
            s.close()
        url_a, url_b = (f"http://127.0.0.1:{p}" for p in ports)

        agent_a = TacoAgent(
            _card("A", url=url_a, task_type="task-a"),
            peers=[url_b],
            peer_retry_delay=0.2,
            peer_startup_wait=0.2,
        )
        agent_b = TacoAgent(
            _card("B", url=url_b, task_type="task-b"),
            peers=[url_a],
            peer_retry_delay=0.2,
            peer_startup_wait=0.2,
        )
        agent_a.register_handler("task-a", _echo)
        agent_b.register_handler("task-b", _echo)

        import uvicorn

        servers = [
            uvicorn.Server(
                uvicorn.Config(agent.app, host="127.0.0.1", port=port, log_level="error")
            )
            for agent, port in ((agent_a, ports[0]), (agent_b, ports[1]))
        ]
        tasks = [asyncio.create_task(s.serve()) for s in servers]
        try:
            for _ in range(100):
                if all(s.started for s in servers):
                    break
                await asyncio.sleep(0.05)
            from_a = await agent_a.send_to_peer("task-b", {"from": "a"})
            from_b = await agent_b.send_to_peer("task-a", {"from": "b"})
        finally:
            for s in servers:
                s.should_exit = True
            await asyncio.gather(*tasks)

        assert from_a.status.state.value == "completed"
        assert from_b.status.state.value == "completed"

    async def test_peer_started_later_is_found_on_demand(self, live_server):
        import socket

        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()

        estimator = TacoAgent(
            _card("Estimator"),
            peers=[f"http://127.0.0.1:{port}"],
            peer_retry_attempts=1,
            peer_startup_wait=0.1,
        )
        supplier = TacoAgent(_card("Supplier", task_type="quote"))
        supplier.register_handler("quote", _echo)

        import uvicorn

        async with live_server(estimator.app):
            await asyncio.sleep(0.3)  # background discovery gives up
            server = uvicorn.Server(
                uvicorn.Config(supplier.app, host="127.0.0.1", port=port, log_level="error")
            )
            serve = asyncio.create_task(server.serve())
            try:
                while not server.started:
                    await asyncio.sleep(0.02)
                task = await estimator.send_to_peer("quote", {})
            finally:
                server.should_exit = True
                await serve
        assert task.status.state.value == "completed"
