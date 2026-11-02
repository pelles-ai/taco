"""Wire parity: every scenario runs once over A2A v0.3 and once over v1.

ADR-0010 moves TACO to the v1 wire format by negotiation: a TACO server
answers both dialects on the same endpoint, advertises both on its card, and
the handler-facing API does not change. These tests pin down that the two
dialects behave the same.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx
import pytest

from taco import (
    A2AServer,
    AuthContext,
    ConstructionAgentCard,
    ConstructionSkill,
    SecurityExt,
    TacoTaskError,
    current_auth,
    make_artifact,
    make_data_part,
)
from taco.types import (
    Artifact,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
)

from ._wire import WIRE_VERSIONS, Wire, WireError

TASK_TYPES = ("estimate", "stream-estimate", "slow", "picky", "boom", "whoami", "refs")

TOKENS = {
    "estimator": AuthContext(subject="estimator", scopes=frozenset({"taco:task:estimate"})),
    "prj-1": AuthContext(
        subject="prj-1",
        scopes=frozenset({"taco:task:estimate", "taco:project:PRJ-1:write"}),
    ),
    "takeoff-only": AuthContext(subject="carol", scopes=frozenset({"taco:task:takeoff"})),
}


async def verify(token: str) -> AuthContext | None:
    return TOKENS.get(token)


@dataclass
class Recorder:
    """What the handlers saw, and a gate to hold the slow one open."""

    release: asyncio.Event = field(default_factory=asyncio.Event)
    started: asyncio.Event = field(default_factory=asyncio.Event)
    cancelled: asyncio.Event = field(default_factory=asyncio.Event)
    seen: list[tuple[str | None, list[str] | None]] = field(default_factory=list)


def _artifact(data: dict) -> Artifact:
    return make_artifact(parts=[make_data_part(data)], name="result")


def _server(*, project_scoped: bool = False, **kwargs) -> tuple[A2AServer, Recorder]:
    card = ConstructionAgentCard(
        name="Parity Agent",
        url="http://test",
        trade="mechanical",
        csi_divisions=["23"],
        skills=[
            ConstructionSkill(id=t, task_type=t, output_schema="estimate-v1") for t in TASK_TYPES
        ],
        construction_security=SecurityExt(project_scoped=True) if project_scoped else None,
    ).to_a2a()
    card.capabilities.push_notifications = True
    server = A2AServer(card, allow_private_push_urls=True, **kwargs)
    rec = Recorder()

    async def estimate(task: Task, data: dict) -> Artifact:
        return _artifact({"echo": data, "total": 120, "rate": 1.5})

    async def stream_estimate(task: Task, data: dict) -> AsyncIterator:
        for chunk in (1, 2):
            yield make_data_part({"chunk": chunk})

    async def slow(task: Task, data: dict) -> Artifact:
        rec.started.set()
        try:
            await rec.release.wait()
        except asyncio.CancelledError:
            rec.cancelled.set()
            raise
        return _artifact({"done": True})

    async def picky(task: Task, data: dict) -> Artifact:
        raise TacoTaskError("bom-v1 input has no lineItems")

    async def boom(task: Task, data: dict) -> Artifact:
        raise RuntimeError("postgres://admin:hunter2@10.0.0.5/db")

    async def whoami(task: Task, data: dict) -> Artifact:
        auth = current_auth()
        return _artifact({"subject": auth.subject if auth else None})

    async def refs(task: Task, data: dict) -> Artifact:
        rec.seen.append((task.context_id, task.history[-1].reference_task_ids))
        return _artifact({"ok": True})

    for task_type, handler in {
        "estimate": estimate,
        "slow": slow,
        "picky": picky,
        "boom": boom,
        "whoami": whoami,
        "refs": refs,
    }.items():
        server.register_handler(task_type, handler)
    server.register_streaming_handler("stream-estimate", stream_estimate)
    return server, rec


def _http(server: A2AServer) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")


@pytest.fixture(params=WIRE_VERSIONS, ids=lambda v: f"v{v}")
def wire(request: pytest.FixtureRequest) -> Wire:
    return Wire(request.param)


def _data(task: Task) -> dict:
    return task.artifacts[0].parts[0].root.data


def _status_text(task: Task) -> str:
    return task.status.message.parts[0].root.text


class TestSend:
    async def test_completes_with_the_handler_artifact(self, wire: Wire):
        server, _ = _server()
        async with _http(server) as http:
            task = await wire.send(http, "estimate", {"qty": 120, "items": [1, 2]})
        assert task.status.state == TaskState.completed
        assert task.metadata == {"taskType": "estimate"}
        assert _data(task) == {"echo": {"qty": 120, "items": [1, 2]}, "total": 120, "rate": 1.5}

    async def test_whole_numbers_stay_integers_on_the_wire(self, wire: Wire):
        server, _ = _server()
        async with _http(server) as http:
            result = await wire.call(http, "send", wire.send_params("estimate", {"qty": 120}))
        data = wire.raw_artifact_data(result)
        assert type(data["total"]) is int and type(data["echo"]["qty"]) is int
        assert data["rate"] == 1.5

    async def test_taco_task_error_text_reaches_the_caller(self, wire: Wire):
        server, _ = _server()
        async with _http(server) as http:
            task = await wire.send(http, "picky", {})
        assert task.status.state == TaskState.failed
        assert _status_text(task) == "bom-v1 input has no lineItems"

    async def test_internal_errors_stay_internal(self, wire: Wire):
        server, _ = _server()
        async with _http(server) as http:
            task = await wire.send(http, "boom", {})
        assert task.status.state == TaskState.failed
        text = _status_text(task)
        assert "hunter2" not in text and "error id" in text

    async def test_unknown_and_missing_task_types_fail_the_task(self, wire: Wire):
        server, _ = _server()
        async with _http(server) as http:
            unknown = await wire.send(http, "no-such-type", {})
            params = wire.send_params("estimate", {})
            del params["metadata"]
            missing = wire.sent_task(await wire.call(http, "send", params))
        assert unknown.status.state == TaskState.failed
        assert "no-such-type" in _status_text(unknown)
        assert missing.status.state == TaskState.failed
        assert "Missing metadata.taskType" in _status_text(missing)

    async def test_context_and_references_reach_the_handler(self, wire: Wire):
        server, rec = _server()
        async with _http(server) as http:
            task = await wire.send(
                http, "refs", {}, context_id="ctx-1", reference_task_ids=["t-a", "t-b"]
            )
        assert task.context_id == "ctx-1"
        assert rec.seen == [("ctx-1", ["t-a", "t-b"])]


class TestStream:
    async def test_working_then_chunks_then_completed(self, wire: Wire, live_server):
        # A real server: httpx's ASGI transport buffers the event stream.
        server, _ = _server()
        async with (
            live_server(server.app) as url,
            httpx.AsyncClient(base_url=url, timeout=10) as http,
        ):
            events = await wire.stream(http, "stream-estimate", {})

        first, *middle, last = events
        assert isinstance(first, Task) and first.status.state == TaskState.working
        artifacts = [e for e in middle if isinstance(e, TaskArtifactUpdateEvent)]
        assert [a.artifact.parts[0].root.data for a in artifacts[:2]] == [
            {"chunk": 1},
            {"chunk": 2},
        ]
        assert isinstance(last, TaskStatusUpdateEvent)
        assert last.status.state == TaskState.completed
        assert {e.task_id for e in events[1:]} == {first.id}


class TestTaskLifecycle:
    async def test_return_immediately_then_get_then_cancel(self, wire: Wire):
        server, rec = _server()
        async with _http(server) as http:
            task = await wire.send(http, "slow", {}, return_immediately=True)
            assert task.status.state in (TaskState.submitted, TaskState.working)
            await asyncio.wait_for(rec.started.wait(), 5)

            assert (await wire.get(http, task.id)).status.state == TaskState.working
            canceled = await wire.cancel(http, task.id)
            assert canceled.status.state == TaskState.canceled
            assert (await wire.get(http, task.id)).status.state == TaskState.canceled
            # CancelTask answers once cancellation is requested; the handler
            # is interrupted on a later turn of the event loop.
            await asyncio.wait_for(rec.cancelled.wait(), 5)

    async def test_unknown_task_is_an_rpc_error(self, wire: Wire):
        server, _ = _server()
        async with _http(server) as http:
            with pytest.raises(WireError):
                await wire.get(http, "no-such-task")


class TestPush:
    async def test_configs_and_delivery(self, wire: Wire, live_server):
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        received: list[tuple[dict, dict]] = []

        async def hook(request: Request) -> JSONResponse:
            received.append((dict(request.headers), await request.json()))
            return JSONResponse({"ok": True})

        server, rec = _server()
        receiver = Starlette(routes=[Route("/hook", hook, methods=["POST"])])
        async with live_server(receiver) as hook_base, _http(server) as http:
            task = await wire.send(http, "slow", {}, return_immediately=True)
            created = await wire.push_set(http, task.id, "cfg-1", f"{hook_base}/hook", token="tok")
            assert (created.id, created.url) == ("cfg-1", f"{hook_base}/hook")
            assert [c.id for c in await wire.push_list(http, task.id)] == ["cfg-1"]
            assert (await wire.push_get(http, task.id, "cfg-1")).url == f"{hook_base}/hook"

            rec.release.set()
            for _ in range(200):
                if any(_completed(body) for _, body in received):
                    break
                await asyncio.sleep(0.02)

            await wire.push_delete(http, task.id, "cfg-1")
            assert await wire.push_list(http, task.id) == []

        headers, body = next((h, b) for h, b in received if _completed(b))
        assert headers["x-a2a-notification-token"] == "tok"
        # Push payloads use the v1 event shape whichever dialect registered them.
        assert body["statusUpdate"]["taskId"] == task.id


def _completed(body: dict) -> bool:
    status = (body.get("statusUpdate") or body.get("task") or {}).get("status") or {}
    return status.get("state") == "TASK_STATE_COMPLETED"


class TestBearerAuth:
    async def test_missing_token_is_401(self, wire: Wire):
        server, _ = _server(token_verifier=verify)
        async with _http(server) as http:
            resp = await wire.post(http, "send", wire.send_params("whoami", {}))
        assert resp.status_code == 401
        assert resp.headers["www-authenticate"].startswith("Bearer")

    async def test_token_without_the_task_scope_is_403(self, wire: Wire):
        server, _ = _server(token_verifier=verify)
        async with _http(server) as http:
            resp = await wire.post(
                http,
                "send",
                wire.send_params("estimate", {}),
                headers={"Authorization": "Bearer takeoff-only"},
            )
        assert resp.status_code == 403
        assert "taco:task:estimate" in resp.json()["error"]["message"]

    async def test_handler_sees_the_caller(self, wire: Wire):
        server, _ = _server(token_verifier=verify, require_task_scope=False)
        async with _http(server) as http:
            task = await wire.send(
                http, "whoami", {}, headers={"Authorization": "Bearer estimator"}
            )
        assert _data(task) == {"subject": "estimator"}

    async def test_project_scope_is_enforced(self, wire: Wire):
        server, _ = _server(token_verifier=verify, project_scoped=True)
        auth = {"Authorization": "Bearer prj-1"}
        async with _http(server) as http:
            other = await wire.post(
                http, "send", wire.send_params("estimate", {"projectId": "PRJ-2"}), auth
            )
            own = await wire.send(http, "estimate", {"projectId": "PRJ-1"}, headers=auth)
        assert other.status_code == 403
        assert "taco:project:PRJ-2" in other.json()["error"]["message"]
        assert own.status.state == TaskState.completed


class TestMonitor:
    async def test_requests_and_handlers_are_traced(self, wire: Wire):
        server, _ = _server(enable_monitor=True)
        async with _http(server) as http:
            await wire.send(http, "estimate", {})
        events = server.monitor_event_bus.get_history()
        incoming = [e for e in events if e["kind"] == "incoming_request"]
        assert [(e["method"], e["task_type"]) for e in incoming] == [
            (wire.method("send"), "estimate")
        ]
        kinds = [e["kind"] for e in events if e["kind"].startswith("handler")]
        assert kinds == ["handler_start", "handler_end"]


class TestDialectMismatch:
    """Each dialect needs its own A2A-Version; a mismatch is refused."""

    async def test_v1_method_without_the_v1_header(self):
        server, _ = _server()
        params = Wire("1.0").send_params("estimate", {})
        async with _http(server) as http:
            payload = (await http.post("/", json=Wire("1.0").body("send", params))).json()
        assert payload["error"]["code"] == -32009

    async def test_v03_method_with_the_v1_header(self):
        server, _ = _server()
        params = Wire("0.3").send_params("estimate", {})
        async with _http(server) as http:
            resp = await http.post(
                "/", json=Wire("0.3").body("send", params), headers={"A2A-Version": "1.0"}
            )
        assert "error" in resp.json()


class TestStockA2AClient:
    """a2a-sdk's own client completes a TACO task in either dialect.

    The card a TACO server serves lists a v1 interface, so the client speaks
    v1. Given a card without one (as served before ADR-0010), it falls back to
    v0.3.
    """

    async def _run(self, legacy_card: bool) -> tuple[list[tuple[str | None, str]], dict]:
        import json

        from a2a.client import ClientConfig, ClientFactory
        from a2a.client.card_resolver import parse_agent_card
        from a2a.types import a2a_pb2 as pb
        from google.protobuf.json_format import MessageToDict, ParseDict

        server, _ = _server()
        sent: list[tuple[str | None, str]] = []

        async def record(request: httpx.Request) -> None:
            if request.method == "POST":
                sent.append(
                    (request.headers.get("a2a-version"), json.loads(request.content)["method"])
                )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app),
            base_url="http://test",
            event_hooks={"request": [record]},
        ) as http:
            card = (await http.get("/.well-known/agent-card.json")).json()
            if legacy_card:
                del card["supportedInterfaces"], card["protocolVersion"]
            client = ClientFactory(ClientConfig(httpx_client=http, streaming=False)).create(
                parse_agent_card(card)
            )
            data = pb.Part().data
            ParseDict({"qty": 120}, data)
            request = pb.SendMessageRequest(
                message=pb.Message(
                    message_id="m-1", role=pb.Role.ROLE_USER, parts=[pb.Part(data=data)]
                )
            )
            request.metadata.update({"taskType": "estimate"})
            results = [r async for r in client.send_message(request)]

        first = results[0][0] if isinstance(results[0], tuple) else results[0]
        result = MessageToDict(first)
        return sent, result.get("task", result)

    async def test_card_as_served_uses_v1(self):
        sent, task = await self._run(legacy_card=False)
        assert sent == [("1.0", "SendMessage")]
        assert task["status"]["state"] == "TASK_STATE_COMPLETED"
        assert task["artifacts"][0]["parts"][0]["data"]["total"] == 120

    async def test_legacy_card_uses_v03(self):
        sent, task = await self._run(legacy_card=True)
        assert sent == [("0.3", "message/send")]
        assert task["status"]["state"] == "TASK_STATE_COMPLETED"
        assert task["artifacts"][0]["parts"][0]["data"]["total"] == 120
