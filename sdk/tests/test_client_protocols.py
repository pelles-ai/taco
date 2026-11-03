"""TacoClient speaks A2A v0.3 or v1 and returns the same results (ADR-0010).

The parity tests run every client operation once per protocol against a
TACO server and check both the result and the methods that went over the
wire. The other tests cover ``protocol="auto"``, version errors, and a plain
a2a-sdk v1 server with no TACO code in it.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
import pytest

from taco import TacoAgent
from taco.client import (
    MessageReplyError,
    ProtocolVersionError,
    RpcError,
    TacoClient,
    _protocol_for_card,
)
from taco.types import AgentCard, TaskState

from .test_wire_parity import _server, verify

PROTOCOLS = ("0.3", "1.0")
SEND = {"0.3": "message/send", "1.0": "SendMessage"}


@pytest.fixture(params=PROTOCOLS, ids=lambda v: f"v{v}")
def protocol(request: pytest.FixtureRequest) -> str:
    return request.param


class Sent(list):
    """The (A2A-Version, method) of every JSON-RPC request a client sent."""

    async def __call__(self, request: httpx.Request) -> None:
        if request.method == "POST":
            self.append((request.headers.get("a2a-version"), json.loads(request.content)["method"]))


def _client(app: Any, protocol: str, sent: Sent | None = None, **kwargs: Any) -> TacoClient:
    http = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        event_hooks={"request": [sent]} if sent is not None else {},
    )
    return TacoClient(agent_url="http://test", http_client=http, protocol=protocol, **kwargs)


class TestParity:
    async def test_send_message(self, protocol: str):
        server, _ = _server()
        sent = Sent()
        async with _client(server.app, protocol, sent) as client:
            task = await client.send_message("estimate", {"qty": 3})
        assert sent == [(protocol, SEND[protocol])]
        assert task.status.state == TaskState.completed
        data = task.artifacts[0].parts[0].root.data
        assert data == {"echo": {"qty": 3}, "total": 120, "rate": 1.5}
        assert isinstance(data["total"], int) and isinstance(data["echo"]["qty"], int)

    async def test_context_and_references_reach_the_handler(self, protocol: str):
        server, rec = _server()
        async with _client(server.app, protocol) as client:
            await client.send_message(
                "refs", {}, context_id="ctx-1", reference_task_ids=["rfi-1", "rfi-2"]
            )
        assert rec.seen == [("ctx-1", ["rfi-1", "rfi-2"])]

    async def test_failed_task_carries_the_handler_message(self, protocol: str):
        server, _ = _server()
        async with _client(server.app, protocol) as client:
            task = await client.send_message("picky", {})
        assert task.status.state == TaskState.failed
        assert "bom-v1 input has no lineItems" in task.status.message.parts[0].root.text

    async def test_return_immediately_then_get_then_cancel(self, protocol: str):
        server, rec = _server()
        sent = Sent()
        async with _client(server.app, protocol, sent) as client:
            task = await client.send_message("slow", {}, return_immediately=True)
            assert task.status.state in (TaskState.submitted, TaskState.working)
            await asyncio.wait_for(rec.started.wait(), 5)
            assert (await client.get_task(task.id)).status.state == TaskState.working
            assert (await client.cancel_task(task.id)).status.state == TaskState.canceled
            await asyncio.wait_for(rec.cancelled.wait(), 5)
        methods = {"0.3": ["tasks/get", "tasks/cancel"], "1.0": ["GetTask", "CancelTask"]}
        assert [m for _, m in sent[1:]] == methods[protocol]

    async def test_unknown_task_is_an_rpc_error_not_a_version_error(self, protocol: str):
        server, _ = _server()
        async with _client(server.app, protocol) as client:
            with pytest.raises(RpcError) as caught:
                await client.get_task("no-such-task")
        assert not isinstance(caught.value, ProtocolVersionError)

    async def test_run_task_returns_the_v03_shape(self, protocol: str):
        server, _ = _server()
        async with _client(server.app, protocol) as client:
            result = await client.run_task(task_type="estimate", input_data={})
        assert result["kind"] == "task"
        assert result["status"]["state"] == "completed"
        assert result["artifacts"][0]["parts"][0] == {
            "kind": "data",
            "data": {"echo": {}, "total": 120, "rate": 1.5},
        }

    async def test_push_configs(self, protocol: str):
        server, rec = _server()
        sent = Sent()
        async with _client(server.app, protocol, sent) as client:
            task = await client.send_message("slow", {}, return_immediately=True)
            created = await client.create_push_config(
                task.id, "https://hooks.example/taco", token="tok", config_id="cfg-1"
            )
            assert (created.id, created.url, created.token) == (
                "cfg-1",
                "https://hooks.example/taco",
                "tok",
            )
            assert [c.id for c in await client.list_push_configs(task.id)] == ["cfg-1"]
            assert (await client.get_push_config(task.id, "cfg-1")).url == created.url
            await client.delete_push_config(task.id, "cfg-1")
            assert await client.list_push_configs(task.id) == []
            # Let the task finish: a2a-sdk's server does not shut down
            # cleanly while a task it returned early is still running.
            rec.release.set()
            await _until_done(client, task.id)
        expected = {
            "0.3": "tasks/pushNotificationConfig/set",
            "1.0": "CreateTaskPushNotificationConfig",
        }
        assert sent[1] == (protocol, expected[protocol])

    async def test_bearer_token_and_list_tasks(self, protocol: str):
        server, _ = _server(token_verifier=verify)
        sent = Sent()
        async with _client(
            server.app, protocol, sent, headers={"Authorization": "Bearer estimator"}
        ) as client:
            task = await client.send_message("estimate", {})
            tasks, cursor = await client.list_tasks()
        assert [t.id for t in tasks] == [task.id]
        assert cursor is None
        # ListTasks only exists in v1, whatever the client's protocol.
        assert sent[-1] == ("1.0", "ListTasks")

    async def test_stream_message_events_match(self, live_server):
        """Streams yield the same v0.3-shaped events whichever version is on the wire."""
        stream = {"0.3": "message/stream", "1.0": "SendStreamingMessage"}
        results: dict[str, list[dict]] = {}
        for protocol in PROTOCOLS:
            server, _ = _server()
            sent = Sent()
            async with live_server(server.app) as url:
                http = httpx.AsyncClient(timeout=10, event_hooks={"request": [sent]})
                async with TacoClient(agent_url=url, http_client=http, protocol=protocol) as c:
                    events = [e async for e in c.stream_message("stream-estimate", {})]
                await http.aclose()
            assert sent == [(protocol, stream[protocol])]
            assert {e["event"] for e in events} == {"message"}
            results[protocol] = [_without_ids(e["data"]["result"]) for e in events]

        assert results["1.0"] == results["0.3"]
        assert [_event_summary(r) for r in results["1.0"]] == [
            ("task", "working", None, None),
            ("artifact-update", None, None, [{"chunk": 1}]),
            ("artifact-update", None, None, [{"chunk": 2}]),
            # The server closes the stream with the whole artifact.
            ("artifact-update", None, None, [{"chunk": 1}, {"chunk": 2}]),
            ("status-update", "completed", True, None),
        ]


_IDS = {"id", "taskId", "contextId", "artifactId", "messageId", "timestamp"}


def _without_ids(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _without_ids(v) for k, v in value.items() if k not in _IDS}
    if isinstance(value, list):
        return [_without_ids(v) for v in value]
    return value


async def _until_done(client: TacoClient, task_id: str) -> None:
    for _ in range(250):
        if (await client.get_task(task_id)).status.state == TaskState.completed:
            return
        await asyncio.sleep(0.02)
    raise AssertionError(f"task {task_id} did not complete")


def _event_summary(result: dict) -> tuple:
    status = result.get("status") or {}
    artifact = result.get("artifact") or {}
    data = [part["data"] for part in artifact["parts"]] if artifact else None
    return (result["kind"], status.get("state"), result.get("final"), data)


class TestAuto:
    async def test_taco_server_card_means_v1(self):
        server, _ = _server()
        sent = Sent()
        async with _client(server.app, "auto", sent) as client:
            assert await client.wire_protocol() == "1.0"
            await client.send_message("estimate", {})
            await client.send_message("estimate", {})
        assert sent == [("1.0", "SendMessage")] * 2

    async def test_card_is_fetched_once(self):
        server, _ = _server()
        fetched: list[str] = []

        async def count(request: httpx.Request) -> None:
            if request.method == "GET":
                fetched.append(request.url.path)

        http = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app),
            base_url="http://test",
            event_hooks={"request": [count]},
        )
        async with TacoClient(agent_url="http://test", http_client=http, protocol="auto") as c:
            await c.send_message("estimate", {})
            await c.get_task((await c.send_message("estimate", {})).id)
        assert fetched == ["/.well-known/agent-card.json"]

    def _card(self, **extra: Any) -> dict:
        return {"name": "Agent", "description": "An agent", "url": "http://agent", **extra}

    def _mock(self, card: dict | None, sent: Sent) -> TacoClient:
        http = httpx.AsyncClient(
            transport=httpx.MockTransport(self._handler(card)), event_hooks={"request": [sent]}
        )
        return TacoClient(agent_url="http://agent", http_client=http, protocol="auto")

    def _handler(self, card: dict | None):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, json=card) if card else httpx.Response(404)
            body = json.loads(request.content)
            task = {"id": "t-1", "contextId": "c-1", "status": {"state": "completed"}}
            if body["method"] == "SendMessage":
                return httpx.Response(
                    200, json={"jsonrpc": "2.0", "id": body["id"], "result": {"task": task}}
                )
            task["kind"] = "task"
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": task})

        return handler

    async def test_card_without_interfaces_means_v03(self):
        sent = Sent()
        async with self._mock(self._card(), sent) as client:
            await client.send_message("estimate", {})
        assert sent == [("0.3", "message/send")]

    async def test_v1_at_another_url_means_v03(self):
        interfaces = [
            {"url": "http://agent/v1", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}
        ]
        sent = Sent()
        async with self._mock(self._card(supportedInterfaces=interfaces), sent) as client:
            await client.send_message("estimate", {})
        assert sent == [("0.3", "message/send")]

    async def test_v1_over_another_binding_means_v03(self):
        interfaces = [{"url": "http://agent", "protocolBinding": "GRPC", "protocolVersion": "1.0"}]
        sent = Sent()
        async with self._mock(self._card(supportedInterfaces=interfaces), sent) as client:
            assert await client.wire_protocol() == "0.3"

    async def test_missing_card_means_v03_and_is_not_refetched(self, caplog):
        sent = Sent()
        with caplog.at_level(logging.WARNING, logger="taco.client"):
            async with self._mock(None, sent) as client:
                await client.send_message("estimate", {})
                await client.send_message("estimate", {})
        assert sent == [("0.3", "message/send")] * 2
        assert "speaking A2A 0.3" in caplog.text
        # One card fetch (and its legacy-path fallback), not one per call.
        assert caplog.text.count("Could not read the agent card") == 1

    async def test_unreachable_agent_raises_and_discovery_is_retried(self):
        sent = Sent()
        up = False
        v1 = {"url": "http://agent", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}
        agent = self._handler(self._card(supportedInterfaces=[v1]))

        def handler(request: httpx.Request) -> httpx.Response:
            if not up:
                raise httpx.ConnectError("connection refused", request=request)
            return agent(request)

        http = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), event_hooks={"request": [sent]}
        )
        async with TacoClient(agent_url="http://agent", http_client=http, protocol="auto") as c:
            with pytest.raises(httpx.ConnectError):
                await c.send_message("estimate", {})
            up = True
            await c.send_message("estimate", {})
        assert sent[-1] == ("1.0", "SendMessage")

    def test_protocol_for_card(self):
        v1 = {"url": "http://a/rpc", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}
        v1_only = {"name": "V1", "description": "d", "supportedInterfaces": [v1]}
        assert _protocol_for_card(v1_only) == "1.0"
        # A registered alias for the agent counts as its endpoint too.
        aliased = {**v1_only, "url": "http://public/rpc", "supportedInterfaces": [v1]}
        assert _protocol_for_card(aliased) == "0.3"
        assert _protocol_for_card(aliased, "http://a/rpc/") == "1.0"
        assert _protocol_for_card(AgentCard.model_validate(v1_only)) == "1.0"
        later = {**v1, "protocolVersion": "1.2"}
        assert _protocol_for_card({**v1_only, "supportedInterfaces": [later]}) == "1.0"


class TestVersionErrors:
    def _rejecting(self, code: int, *, content_type: str = "application/json") -> TacoClient:
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            payload = {"jsonrpc": "2.0", "id": body["id"], "error": {"code": code, "message": "no"}}
            return httpx.Response(
                200, content=json.dumps(payload), headers={"content-type": content_type}
            )

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return TacoClient(agent_url="http://old", http_client=http, protocol="1.0")

    @pytest.mark.parametrize("code", [-32601, -32009])
    async def test_rejected_version_names_the_version(self, code: int):
        async with self._rejecting(code) as client:
            with pytest.raises(ProtocolVersionError) as caught:
                await client.send_message("estimate", {})
        error = caught.value
        assert isinstance(error, RpcError) and error.code == code
        assert (error.protocol, error.method) == ("1.0", "SendMessage")
        assert "A2A 1.0" in str(error) and "SendMessage" in str(error)

    async def test_other_errors_stay_rpc_errors(self):
        async with self._rejecting(-32001) as client:
            with pytest.raises(RpcError) as caught:
                await client.get_task("t-1")
        assert type(caught.value) is RpcError

    async def test_stream_answered_with_a_json_error_raises(self):
        async with self._rejecting(-32009) as client:
            with pytest.raises(ProtocolVersionError) as caught:
                [e async for e in client.stream_message("estimate", {})]
        assert caught.value.method == "SendStreamingMessage"

    def test_unknown_protocol_is_rejected(self):
        with pytest.raises(ValueError, match="protocol"):
            TacoClient(agent_url="http://a", protocol="2.0")


def _plain_a2a_app() -> Any:
    """An a2a-sdk v1 server with no TACO code and no v0.3 compatibility."""
    from a2a.helpers import new_data_message, new_task_from_user_message
    from a2a.server.agent_execution import AgentExecutor
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
    from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
    from a2a.types import a2a_pb2 as pb
    from google.protobuf.json_format import ParseDict
    from starlette.applications import Starlette

    class Executor(AgentExecutor):
        async def execute(self, context, event_queue) -> None:
            if context.metadata.get("taskType") == "chat":
                reply = new_data_message({"hello": 1}, context_id=context.context_id)
                await event_queue.enqueue_event(reply)
                return
            task = context.current_task or new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
            updater = TaskUpdater(event_queue, task.id, task.context_id)
            await updater.start_work()
            data = pb.Part().data
            ParseDict({"total": 120, "rate": 1.5}, data)
            await updater.add_artifact([pb.Part(data=data)], name="result")
            await updater.complete()

        async def cancel(self, context, event_queue) -> None:
            return None

    card = pb.AgentCard(
        name="Plain v1 agent",
        description="a2a-sdk only",
        version="1.0.0",
        supported_interfaces=[
            pb.AgentInterface(
                url="http://plain", protocol_binding="JSONRPC", protocol_version="1.0"
            )
        ],
        capabilities=pb.AgentCapabilities(streaming=True),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[pb.AgentSkill(id="estimate", name="Estimate", description="d", tags=["x"])],
    )
    handler = DefaultRequestHandler(
        agent_executor=Executor(), task_store=InMemoryTaskStore(), agent_card=card
    )
    return Starlette(
        routes=[*create_agent_card_routes(card), *create_jsonrpc_routes(handler, rpc_url="/")]
    )


class TestPlainA2ASDKServer:
    def _client(self, protocol: str, sent: Sent | None = None) -> TacoClient:
        http = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_plain_a2a_app()),
            base_url="http://plain",
            event_hooks={"request": [sent]} if sent is not None else {},
        )
        return TacoClient(agent_url="http://plain", http_client=http, protocol=protocol)

    async def test_v1_send_and_get(self):
        async with self._client("1.0") as client:
            task = await client.send_message("estimate", {"qty": 1})
            assert task.status.state == TaskState.completed
            data = task.artifacts[0].parts[0].root.data
            assert data == {"total": 120, "rate": 1.5} and isinstance(data["total"], int)
            assert (await client.get_task(task.id)).id == task.id

    async def test_auto_reads_the_v1_card(self):
        sent = Sent()
        async with self._client("auto", sent) as client:
            card = await client.discover()
            task = await client.send_message("estimate", {})
        assert card.url == "http://plain"
        assert task.status.state == TaskState.completed
        assert sent == [("1.0", "SendMessage")]

    async def test_message_reply(self):
        async with self._client("1.0") as client:
            with pytest.raises(MessageReplyError) as caught:
                await client.send_message("chat", {})
        data = caught.value.reply.parts[0].root.data
        assert data == {"hello": 1} and isinstance(data["hello"], int)

    async def test_v03_is_rejected_with_a_version_error(self):
        async with self._client("0.3") as client:
            with pytest.raises(ProtocolVersionError) as caught:
                await client.send_message("estimate", {})
        assert (caught.value.protocol, caught.value.method) == ("0.3", "message/send")

    async def test_v1_stream(self, live_server):
        async with (
            live_server(_plain_a2a_app()) as url,
            TacoClient(agent_url=url, protocol="1.0") as client,
        ):
            events = [e async for e in client.stream_message("estimate", {})]
        kinds = [e["data"]["result"]["kind"] for e in events]
        assert kinds[0] == "task" and kinds[-1] == "status-update"
        artifact = next(e for e in events if e["data"]["result"]["kind"] == "artifact-update")
        assert artifact["data"]["result"]["artifact"]["parts"][0]["data"]["total"] == 120
        assert events[-1]["data"]["result"]["final"] is True


class TestTacoAgentPeers:
    def _agent(self, **kwargs: Any) -> TacoAgent:
        from taco import ConstructionAgentCard, ConstructionSkill

        card = ConstructionAgentCard(
            name="Router",
            url="http://router",
            trade="general",
            csi_divisions=[],
            skills=[ConstructionSkill(id="route", task_type="estimate", output_schema="e-v1")],
        )
        return TacoAgent(card, peers=["http://peer"], **kwargs)

    def test_peer_clients_use_the_peer_protocol(self):
        agent = self._agent(peer_protocol="auto")
        assert agent._get_or_create_client("http://peer").protocol == "auto"
        assert self._agent()._get_or_create_client("http://peer").protocol == "0.3"

    def test_unknown_peer_protocol_is_rejected(self):
        with pytest.raises(ValueError, match="peer_protocol"):
            self._agent(peer_protocol="v1")
