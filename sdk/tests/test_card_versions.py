"""The agent card advertises A2A v0.3 and v1 (ADR-0010).

A TACO server's card keeps every v0.3 field and adds ``supportedInterfaces``
and the ``x-construction`` extension's ``params``, so v0.3 and v1 readers
both find what they need. TACO's own readers accept cards written for v1
alone.
"""

from __future__ import annotations

import httpx
import pytest

from taco import AgentRegistry, ConstructionAgentCard, ConstructionSkill, TacoClient
from taco.server import A2AServer
from taco.types import (
    X_CONSTRUCTION_EXTENSION_URI,
    AgentCard,
    get_construction_ext,
    get_skill_construction_ext,
)

ADMIN_TOKEN = "admin-token"


async def _served(server: A2AServer, path: str = "/.well-known/agent-card.json") -> dict:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=server.app), base_url="http://served"
    ) as http:
        return (await http.get(path)).json()


def _extension(card: dict) -> dict:
    (extension,) = [
        e
        for e in card["capabilities"].get("extensions", [])
        if e["uri"] == X_CONSTRUCTION_EXTENSION_URI
    ]
    return extension


def _interface(url: str, version: str, binding: str = "JSONRPC") -> dict:
    return {"url": url, "protocolBinding": binding, "protocolVersion": version}


def _v1_only_card() -> dict:
    """A card from an implementation that writes A2A v1 fields alone."""
    return {
        "name": "V1 Electrical Agent",
        "description": "Writes its card for A2A v1 only",
        "version": "2.0.0",
        "supportedInterfaces": [
            _interface("https://v1.example/grpc", "1.0", binding="GRPC"),
            _interface("https://v1.example/rpc", "1.0"),
        ],
        "capabilities": {
            "streaming": True,
            "extensions": [
                {
                    "uri": X_CONSTRUCTION_EXTENSION_URI,
                    "params": {
                        "trade": "electrical",
                        "csiDivisions": ["26"],
                        "skills": {
                            "takeoff": {
                                "taskType": "quantity-takeoff",
                                "outputSchema": "quantity-takeoff-v1",
                            }
                        },
                    },
                }
            ],
        },
        "skills": [
            {"id": "takeoff", "name": "Takeoff", "description": "Counts devices", "tags": []},
            {"id": "chat", "name": "Chat", "description": "Not a TACO skill", "tags": []},
        ],
    }


class TestServedCard:
    async def test_both_versions_on_the_card_url(self, sample_server: A2AServer):
        card = await _served(sample_server)
        assert card["url"] == "http://localhost:9999"
        assert card["protocolVersion"] == "0.3.0"
        assert card["supportedInterfaces"] == [
            _interface("http://localhost:9999", "1.0"),
            _interface("http://localhost:9999", "0.3"),
        ]

    async def test_legacy_path_serves_the_same_card(self, sample_server: A2AServer):
        assert await _served(sample_server, "/.well-known/agent.json") == await _served(
            sample_server
        )

    async def test_interfaces_use_the_request_address_when_the_card_has_no_url(
        self, sample_agent_card: AgentCard
    ):
        sample_agent_card.url = ""
        card = await _served(A2AServer(sample_agent_card))
        assert card["url"] == "http://served"
        assert {i["url"] for i in card["supportedInterfaces"]} == {"http://served"}

    async def test_extension_params_mirror_the_inline_fields(self, sample_server: A2AServer):
        card = await _served(sample_server)
        extension = _extension(card)
        assert extension["required"] is False
        params = extension["params"]
        skills = params.pop("skills")
        assert params == card["x-construction"]
        assert skills == {s["id"]: s["x-construction"] for s in card["skills"]}
        assert skills["test-skill"]["taskType"] == "test-task"

    async def test_construction_card_declares_the_extension_once(self):
        card = ConstructionAgentCard(
            name="Estimator",
            url="http://est",
            trade="mechanical",
            csi_divisions=["23"],
            skills=[ConstructionSkill(id="est", task_type="estimate", output_schema="estimate-v1")],
        ).to_a2a()
        served = await _served(A2AServer(card))
        uris = [e["uri"] for e in served["capabilities"]["extensions"]]
        assert uris == [X_CONSTRUCTION_EXTENSION_URI]
        assert _extension(served)["params"]["skills"] == {
            "est": {"taskType": "estimate", "outputSchema": "estimate-v1"}
        }

    async def test_serving_leaves_the_card_unchanged(self, sample_server: A2AServer):
        before = sample_server.agent_card.model_dump(by_alias=True)
        await _served(sample_server)
        assert sample_server.agent_card.model_dump(by_alias=True) == before

    async def test_params_follow_admin_skill_changes(self, sample_agent_card: AgentCard):
        server = A2AServer(sample_agent_card, enable_admin=True, admin_auth_token=ADMIN_TOKEN)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app),
            base_url="http://served",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        ) as http:
            added = await http.post(
                "/admin/skills",
                json={
                    "id": "rfi",
                    "name": "RFI",
                    "description": "Drafts RFIs",
                    "x-construction": {"taskType": "rfi-generation", "outputSchema": "rfi-v1"},
                },
            )
            assert added.status_code == 200
            await http.delete("/admin/skills/test-skill")
            card = (await http.get("/.well-known/agent-card.json")).json()
        assert _extension(card)["params"]["skills"] == {
            "rfi": {"taskType": "rfi-generation", "outputSchema": "rfi-v1"}
        }

    async def test_card_without_x_construction_has_no_extension(self):
        card = AgentCard(name="Plain", description="No construction metadata", url="http://p")
        served = await _served(A2AServer(card))
        assert "x-construction" not in served
        assert not served["capabilities"].get("extensions")
        assert [i["protocolVersion"] for i in served["supportedInterfaces"]] == ["1.0", "0.3"]

    async def test_interfaces_set_on_the_card_are_kept(self, sample_agent_card: AgentCard):
        own = [_interface("https://public/a2a", "0.3")]
        card = AgentCard.model_validate(
            {
                **sample_agent_card.model_dump(by_alias=True, exclude_none=True),
                "supportedInterfaces": own,
                "protocolVersion": "0.3.0",
            }
        )
        served = await _served(A2AServer(card))
        assert served["supportedInterfaces"] == own


class TestA2ASDKReaders:
    async def test_v1_parser_keeps_construction_params(self, sample_server: A2AServer):
        from a2a.client.card_resolver import parse_agent_card
        from google.protobuf.json_format import MessageToDict

        parsed = parse_agent_card(await _served(sample_server))
        assert [i.protocol_version for i in parsed.supported_interfaces][0] == "1.0"
        (extension,) = [
            e for e in parsed.capabilities.extensions if e.uri == X_CONSTRUCTION_EXTENSION_URI
        ]
        params = MessageToDict(extension.params)
        assert params["trade"] == "mechanical"
        assert params["skills"]["test-skill"]["taskType"] == "test-task"

    async def test_v03_model_reads_the_card(self, sample_server: A2AServer):
        from a2a.compat.v0_3.types import AgentCard as V03AgentCard

        card = V03AgentCard.model_validate(await _served(sample_server))
        assert card.url == "http://localhost:9999"
        assert card.protocol_version == "0.3.0"


class TestTacoReaders:
    def test_agent_card_reads_a_v1_only_card(self):
        card = AgentCard.model_validate(_v1_only_card())
        assert card.url == "https://v1.example/rpc"
        xc = get_construction_ext(card)
        assert xc is not None and xc.trade == "electrical" and xc.csi_divisions == ["26"]
        takeoff, chat = card.skills
        assert get_skill_construction_ext(takeoff).task_type == "quantity-takeoff"
        assert get_skill_construction_ext(chat) is None

    def test_inline_fields_win_over_params(self):
        data = _v1_only_card()
        data["url"] = "https://inline/rpc"
        data["x-construction"] = {"trade": "mechanical"}
        data["skills"][0]["x-construction"] = {"taskType": "estimate", "outputSchema": "e-v1"}
        card = AgentCard.model_validate(data)
        assert card.url == "https://inline/rpc"
        assert card.x_construction.trade == "mechanical"
        assert card.skills[0].x_construction.task_type == "estimate"

    def test_served_card_round_trips(self, sample_agent_card: AgentCard):
        from taco.server import _advertised_card

        served = _advertised_card(sample_agent_card, "http://base")
        card = AgentCard.model_validate(served)
        assert card.x_construction == sample_agent_card.x_construction
        assert card.skills[0].x_construction == sample_agent_card.skills[0].x_construction

    def test_card_without_any_url_is_still_rejected(self):
        data = _v1_only_card()
        del data["supportedInterfaces"]
        with pytest.raises(ValueError, match="url"):
            AgentCard.model_validate(data)

    async def test_client_and_registry_read_a_v1_only_card(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_v1_only_card())

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        async with TacoClient(agent_url="http://v1", http_client=http) as client:
            card = await client.discover()
        assert card.url == "https://v1.example/rpc"

        registry = AgentRegistry()
        registry.register_card("http://v1", card)
        assert registry.find(trade="electrical", task_type="quantity-takeoff") == [card]
        assert registry.find(task_type="estimate") == []
