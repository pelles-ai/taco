"""Tests for caip.models — A2A protocol wire-format models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from caip.models import (
    AgentCard,
    AgentConstructionExt,
    AgentSkill,
    Artifact,
    JsonRpcError,
    JsonRpcResponse,
    Message,
    Part,
    SkillConstructionExt,
    Task,
    TaskState,
    TaskStatus,
)


class TestPart:
    def test_text_part(self):
        p = Part(text="hello")
        assert p.text == "hello"
        assert p.structured_data is None

    def test_structured_data_part(self):
        p = Part(structured_data={"key": "value"})
        assert p.structured_data == {"key": "value"}
        assert p.text is None

    def test_both_text_and_structured(self):
        p = Part(text="hello", structured_data={"key": "value"})
        assert p.text == "hello"
        assert p.structured_data == {"key": "value"}

    def test_empty_part_fails(self):
        with pytest.raises(ValidationError, match="must have at least"):
            Part()

    def test_none_values_fail(self):
        with pytest.raises(ValidationError, match="must have at least"):
            Part(text=None, structured_data=None)


class TestCamelCaseSerialization:
    def test_task_status_round_trip(self):
        ts = TaskStatus(state=TaskState.WORKING)
        data = ts.model_dump(by_alias=True)
        assert "state" in data
        ts2 = TaskStatus.model_validate(data)
        assert ts2.state == TaskState.WORKING

    def test_task_round_trip(self):
        task = Task(
            status=TaskStatus(state=TaskState.COMPLETED),
            context_id="ctx-123",
            metadata={"taskType": "test"},
        )
        data = task.model_dump(by_alias=True, exclude_none=True)
        assert "contextId" in data
        assert data["contextId"] == "ctx-123"
        task2 = Task.model_validate(data)
        assert task2.context_id == "ctx-123"

    def test_skill_construction_ext_aliases(self):
        ext = SkillConstructionExt(
            task_type="estimate",
            input_schema="bom-v1",
            output_schema="estimate-v1",
        )
        data = ext.model_dump(by_alias=True)
        assert data["taskType"] == "estimate"
        assert data["inputSchema"] == "bom-v1"
        assert data["outputSchema"] == "estimate-v1"

    def test_agent_card_x_construction_alias(self):
        card = AgentCard(
            name="Test",
            description="Test agent",
            url="http://localhost:9999",
            x_construction=AgentConstructionExt(
                trade="mechanical",
                csi_divisions=["23"],
            ),
        )
        data = card.model_dump(by_alias=True, exclude_none=True)
        assert "x-construction" in data
        assert data["x-construction"]["trade"] == "mechanical"


class TestJsonRpcResponse:
    def test_result_only(self):
        r = JsonRpcResponse(id="1", result={"ok": True})
        assert r.result == {"ok": True}
        assert r.error is None

    def test_error_only(self):
        r = JsonRpcResponse(id="1", error=JsonRpcError(code=-1, message="fail"))
        assert r.error.code == -1
        assert r.result is None

    def test_both_result_and_error_fails(self):
        with pytest.raises(ValidationError, match="must not have both"):
            JsonRpcResponse(
                id="1",
                result={"ok": True},
                error=JsonRpcError(code=-1, message="fail"),
            )

    def test_neither_result_nor_error_fails(self):
        with pytest.raises(ValidationError, match="must have either"):
            JsonRpcResponse(id="1")


class TestAgentCard:
    def test_full_construction_card(self, sample_agent_card: AgentCard):
        data = sample_agent_card.model_dump(by_alias=True, exclude_none=True)
        card2 = AgentCard.model_validate(data)
        assert card2.name == "Test Agent"
        assert card2.x_construction is not None
        assert card2.x_construction.trade == "mechanical"
        assert card2.x_construction.csi_divisions == ["23"]
        assert card2.skills[0].x_construction.task_type == "test-task"

    def test_empty_name_fails(self):
        with pytest.raises(ValidationError):
            AgentCard(name="", description="x", url="http://localhost")

    def test_empty_description_fails(self):
        with pytest.raises(ValidationError):
            AgentCard(name="x", description="", url="http://localhost")


class TestTaskState:
    def test_all_values(self):
        expected = {"working", "completed", "failed", "canceled", "input-required"}
        actual = {s.value for s in TaskState}
        assert actual == expected

    def test_string_value(self):
        assert TaskState.WORKING == "working"
        assert TaskState.COMPLETED == "completed"


class TestLiterals:
    def test_invalid_trade(self):
        with pytest.raises(ValidationError):
            AgentConstructionExt(trade="nonexistent")

    def test_valid_trade(self):
        ext = AgentConstructionExt(trade="electrical")
        assert ext.trade == "electrical"

    def test_invalid_project_type(self):
        with pytest.raises(ValidationError):
            AgentConstructionExt(trade="mechanical", project_types=["nonexistent"])


class TestMessage:
    def test_message_creation(self):
        m = Message(role="user", parts=[Part(text="hello")])
        assert m.role == "user"
        assert len(m.parts) == 1

    def test_message_empty_parts_fails(self):
        with pytest.raises(ValidationError):
            Message(role="user", parts=[])


class TestArtifact:
    def test_artifact_with_metadata(self):
        a = Artifact(
            name="test",
            description="desc",
            parts=[Part(text="data")],
            metadata={"schema": "test-v1"},
        )
        assert a.metadata["schema"] == "test-v1"
