"""Tests for taco.agent_card — ConstructionSkill and ConstructionAgentCard factories."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from taco.agent_card import ConstructionAgentCard, ConstructionSkill
from taco.types import AgentCard, AgentSkill


class TestConstructionSkill:
    def test_to_a2a_basic(self):
        skill = ConstructionSkill(
            id="gen-estimate",
            name="Generate Estimate",
            description="Generates cost estimates",
            task_type="estimate",
            input_schema="bom-v1",
            output_schema="estimate-v1",
        )
        a2a = skill.to_a2a()
        assert isinstance(a2a, AgentSkill)
        assert a2a.id == "gen-estimate"
        assert a2a.name == "Generate Estimate"
        assert a2a.description == "Generates cost estimates"
        assert a2a.tags == ["estimate"]
        assert a2a.x_construction is not None
        assert a2a.x_construction.task_type == "estimate"
        assert a2a.x_construction.input_schema == "bom-v1"
        assert a2a.x_construction.output_schema == "estimate-v1"

    def test_to_a2a_x_construction_populated(self):
        skill = ConstructionSkill(
            id="gen-rfi",
            task_type="rfi",
            output_schema="rfi-v1",
        )
        a2a = skill.to_a2a()
        xc = a2a.x_construction
        assert xc is not None
        assert xc.task_type == "rfi"
        assert xc.input_schema is None
        assert xc.output_schema == "rfi-v1"

    def test_to_a2a_serializes_correctly(self):
        skill = ConstructionSkill(
            id="test",
            task_type="test",
            output_schema="test-v1",
        )
        a2a = skill.to_a2a()
        data = a2a.model_dump(by_alias=True, exclude_none=True)
        assert data["x-construction"]["taskType"] == "test"
        assert data["x-construction"]["outputSchema"] == "test-v1"

    def test_default_name_and_description(self):
        skill = ConstructionSkill(
            id="my-skill",
            task_type="test",
            output_schema="test-v1",
        )
        assert skill.name == "my-skill"
        assert "my-skill" in skill.description


class TestConstructionAgentCard:
    def test_to_a2a_basic(self):
        card = ConstructionAgentCard(
            name="Test Agent",
            description="A test agent",
            url="http://localhost:8001",
            trade="mechanical",
            csi_divisions=["23"],
            project_types=["commercial"],
        )
        a2a = card.to_a2a()
        assert isinstance(a2a, AgentCard)
        assert a2a.name == "Test Agent"
        assert a2a.url == "http://localhost:8001"
        assert a2a.x_construction is not None
        assert a2a.x_construction.trade == "mechanical"
        assert a2a.x_construction.csi_divisions == ["23"]
        assert a2a.x_construction.project_types == ["commercial"]

    def test_to_a2a_with_skills(self):
        skill = ConstructionSkill(
            id="est",
            task_type="estimate",
            output_schema="estimate-v1",
        )
        card = ConstructionAgentCard(
            name="Agent",
            trade="electrical",
            csi_divisions=["26"],
            skills=[skill],
        )
        a2a = card.to_a2a()
        assert len(a2a.skills) == 1
        assert a2a.skills[0].x_construction.task_type == "estimate"

    def test_to_a2a_x_construction_populated(self):
        card = ConstructionAgentCard(
            name="Agent",
            trade="plumbing",
            csi_divisions=["22"],
            data_formats={"input": ["bom-v1"], "output": ["estimate-v1"]},
            integrations=["procore"],
        )
        a2a = card.to_a2a()
        xc = a2a.x_construction
        assert xc is not None
        assert xc.trade == "plumbing"
        assert xc.data_formats == {"input": ["bom-v1"], "output": ["estimate-v1"]}
        assert xc.integrations == ["procore"]

    def test_serve_import_error(self):
        card = ConstructionAgentCard(
            name="Agent",
            trade="mechanical",
            csi_divisions=["23"],
        )
        with (
            patch.dict("sys.modules", {"uvicorn": None}),
            pytest.raises(ImportError, match="Server dependencies"),
        ):
            card.serve()

    def test_to_a2a_round_trip(self):
        card = ConstructionAgentCard(
            name="Round Trip Agent",
            description="Testing round trip",
            url="http://localhost:9000",
            trade="structural",
            csi_divisions=["03"],
            project_types=["residential"],
        )
        a2a = card.to_a2a()
        data = a2a.model_dump(by_alias=True, exclude_none=True)
        restored = AgentCard.model_validate(data)
        assert restored.name == "Round Trip Agent"
        assert restored.x_construction.trade == "structural"


class TestExtensionDeclaration:
    """``to_a2a()`` advertises the formal x-construction URI alongside the inline field."""

    def test_capabilities_extensions_declares_uri(self):
        from taco import X_CONSTRUCTION_EXTENSION_URI

        card = ConstructionAgentCard(
            name="A",
            trade="mechanical",
            csi_divisions=["23"],
        ).to_a2a()
        assert card.capabilities is not None
        uris = [ext.uri for ext in (card.capabilities.extensions or [])]
        assert X_CONSTRUCTION_EXTENSION_URI in uris

    def test_apply_construction_extension_declaration_is_idempotent(self):
        from taco import X_CONSTRUCTION_EXTENSION_URI, apply_construction_extension_declaration

        card = ConstructionAgentCard(name="A", trade="mechanical", csi_divisions=["23"]).to_a2a()
        before = len(card.capabilities.extensions or [])
        apply_construction_extension_declaration(card)
        apply_construction_extension_declaration(card)
        after = len(card.capabilities.extensions or [])
        assert before == after == 1
        assert card.capabilities.extensions[0].uri == X_CONSTRUCTION_EXTENSION_URI

    def test_no_declaration_when_x_construction_absent(self):
        from taco import AgentCard, apply_construction_extension_declaration

        plain = AgentCard(name="Plain", description="plain", url="http://plain")
        apply_construction_extension_declaration(plain)
        # No capabilities, or no extensions list — either way, no URI added.
        extensions = (plain.capabilities.extensions if plain.capabilities else None) or []
        assert extensions == []

    def test_extension_serialized_in_json(self):
        from taco import X_CONSTRUCTION_EXTENSION_URI

        card = ConstructionAgentCard(name="A", trade="mechanical", csi_divisions=["23"]).to_a2a()
        j = card.model_dump(by_alias=True, exclude_none=True)
        extensions = j.get("capabilities", {}).get("extensions", [])
        assert any(e.get("uri") == X_CONSTRUCTION_EXTENSION_URI for e in extensions)
        # The inline field is preserved for back-compat with non-v1 readers.
        assert "x-construction" in j
