"""Tests for bearer-token auth (taco.auth) and card security declarations."""

from __future__ import annotations

import httpx
import pytest

from taco import (
    A2AServer,
    AgentCard,
    AuthContext,
    ConstructionAgentCard,
    ConstructionSkill,
    RpcError,
    SecurityExt,
    TacoClient,
    current_auth,
    make_artifact,
    make_data_part,
    task_scope,
)
from taco.types import Artifact, Task

TOKENS = {
    "alice-token": AuthContext(subject="alice", scopes=frozenset({"taco:task:estimate"})),
    "bob-token": AuthContext(subject="bob", scopes=frozenset({"taco:task:estimate"})),
    "no-scope-token": AuthContext(subject="carol", scopes=frozenset({"taco:task:takeoff"})),
}


async def verify(token: str) -> AuthContext | None:
    return TOKENS.get(token)


def _card(**kwargs) -> ConstructionAgentCard:
    return ConstructionAgentCard(
        name="Secured Estimator",
        url="http://test",
        trade="mechanical",
        csi_divisions=["23"],
        skills=[
            ConstructionSkill(id="estimate", task_type="estimate", output_schema="estimate-v1")
        ],
        security_schemes={"bearer": {"type": "http", "scheme": "bearer"}},
        security=[{"bearer": [task_scope("estimate")]}],
        **kwargs,
    )


seen_auth: list[AuthContext | None] = []


async def handler(task: Task, input_data: dict) -> Artifact:
    seen_auth.append(current_auth())
    return make_artifact(parts=[make_data_part({"ok": True})])


def _server(**kwargs) -> A2AServer:
    server = A2AServer(_card().to_a2a(), token_verifier=verify, **kwargs)
    server.register_handler("estimate", handler)
    return server


def _client(server: A2AServer, token: str | None = None) -> TacoClient:
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    return TacoClient(agent_url="http://test", http_client=http, headers=headers)


def _send_payload(task_type: str = "estimate") -> dict:
    return {
        "jsonrpc": "2.0",
        "id": "req-1",
        "method": "message/send",
        "params": {
            "message": {"role": "user", "parts": [{"kind": "data", "data": {}}], "messageId": "m1"},
            "metadata": {"taskType": task_type},
        },
    }


@pytest.fixture(autouse=True)
def _reset_seen():
    seen_auth.clear()


class TestBearerAuth:
    async def _post(self, server: A2AServer, headers: dict | None = None, task_type="estimate"):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app), base_url="http://test"
        ) as http:
            return await http.post("/", json=_send_payload(task_type), headers=headers or {})

    async def test_missing_token_is_401(self):
        resp = await self._post(_server())
        assert resp.status_code == 401
        assert resp.headers["www-authenticate"].startswith("Bearer")
        body = resp.json()
        assert body["id"] == "req-1" and body["error"]["code"] == -32000
        assert seen_auth == []

    async def test_invalid_token_is_401(self):
        resp = await self._post(_server(), {"Authorization": "Bearer forged"})
        assert resp.status_code == 401
        assert seen_auth == []

    async def test_non_bearer_scheme_is_401(self):
        resp = await self._post(_server(), {"Authorization": "Basic YWxpY2U6cHc="})
        assert resp.status_code == 401

    async def test_verifier_exception_is_401(self):
        async def broken(token: str) -> AuthContext | None:
            raise RuntimeError("IdP down")

        server = A2AServer(_card().to_a2a(), token_verifier=broken)
        server.register_handler("estimate", handler)
        resp = await self._post(server, {"Authorization": "Bearer alice-token"})
        assert resp.status_code == 401

    async def test_missing_task_scope_is_403(self):
        resp = await self._post(_server(), {"Authorization": "Bearer no-scope-token"})
        assert resp.status_code == 403
        assert "taco:task:estimate" in resp.json()["error"]["message"]
        assert seen_auth == []

    async def test_scope_check_can_be_turned_off(self):
        resp = await self._post(
            _server(require_task_scope=False), {"Authorization": "Bearer no-scope-token"}
        )
        assert resp.status_code == 200
        assert resp.json()["result"]["status"]["state"] == "completed"

    async def test_valid_token_runs_handler_with_current_auth(self):
        task = await _client(_server(), "alice-token").send_message("estimate", {})
        assert task.status.state.value == "completed"
        assert seen_auth == [TOKENS["alice-token"]]

    async def test_card_and_health_stay_public(self):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_server().app), base_url="http://test"
        ) as http:
            assert (await http.get("/.well-known/agent-card.json")).status_code == 200
            assert (await http.get("/health")).status_code == 200

    async def test_callers_only_see_their_own_tasks(self):
        server = _server()
        alice, bob = _client(server, "alice-token"), _client(server, "bob-token")
        task = await alice.send_message("estimate", {}, context_id="ctx-alice")

        assert (await alice.get_task(task.id)).id == task.id
        with pytest.raises(RpcError):
            await bob.get_task(task.id)
        bob_tasks, _ = await bob.list_tasks()
        assert bob_tasks == []
        alice_tasks, _ = await alice.list_tasks(context_id="ctx-alice")
        assert [t.id for t in alice_tasks] == [task.id]

    async def test_auth_errors_carry_cors_headers(self):
        server = A2AServer(_card().to_a2a(), token_verifier=verify, cors_origins=["https://app"])
        server.register_handler("estimate", handler)
        resp = await self._post(server, {"Origin": "https://app"})
        assert resp.status_code == 401
        assert resp.headers["access-control-allow-origin"] == "https://app"


class TestCardSecurityDeclaration:
    async def test_security_fields_are_served(self):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_server().app), base_url="http://test"
        ) as http:
            card = (await http.get("/.well-known/agent-card.json")).json()
        assert card["securitySchemes"] == {"bearer": {"type": "http", "scheme": "bearer"}}
        assert card["security"] == [{"bearer": ["taco:task:estimate"]}]

    async def test_discovered_card_keeps_security_and_unknown_fields(self):
        remote = {
            "name": "BuildRight",
            "description": "d",
            "url": "https://x/a2a",
            "version": "1.0.0",
            "protocolVersion": "0.3.0",
            "provider": {"organization": "BuildRight", "url": "https://buildright.example"},
            "securitySchemes": {"tacoOAuth": {"type": "oauth2", "flows": {}}},
            "security": [{"tacoOAuth": ["taco:task:estimate"]}],
            "skills": [],
            "x-construction": {"trade": "mechanical", "csiDivisions": ["22"]},
        }
        card = AgentCard.model_validate(remote)
        dumped = card.model_dump(mode="json", by_alias=True, exclude_none=True)
        for key in ("protocolVersion", "provider", "securitySchemes", "security"):
            assert dumped[key] == remote[key]

    def test_factory_sets_construction_security_and_certifications(self):
        card = _card(
            certifications=["SOC2"],
            construction_security=SecurityExt(
                trust_tier=1, scopes_offered=["taco:task:estimate"], project_scoped=True
            ),
        ).to_a2a()
        xc = card.model_dump(mode="json", by_alias=True, exclude_none=True)["x-construction"]
        assert xc["certifications"] == ["SOC2"]
        assert xc["security"]["trustTier"] == 1
        assert xc["security"]["projectScoped"] is True


class TestAuthWithJsonFileTaskStore:
    async def test_callers_only_see_their_own_tasks(self, tmp_path):
        from taco import JsonFileTaskStore

        store = JsonFileTaskStore(str(tmp_path / "tasks.json"))
        server = A2AServer(_card().to_a2a(), token_verifier=verify, task_store=store)
        server.register_handler("estimate", handler)
        alice, bob = _client(server, "alice-token"), _client(server, "bob-token")

        task = await alice.send_message("estimate", {})
        with pytest.raises(RpcError):
            await bob.get_task(task.id)
        assert (await bob.list_tasks())[0] == []
        assert [t.id for t in (await alice.list_tasks())[0]] == [task.id]
