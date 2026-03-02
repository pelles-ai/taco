"""Pydantic models for the A2A (Agent-to-Agent) protocol wire format.

Covers Agent Cards, JSON-RPC messages, tasks, artifacts, and the
CAIP x-construction extensions. Uses camelCase aliases to match
the A2A JSON spec while keeping Pythonic snake_case internally.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class CaipBaseModel(BaseModel):
    """Base for all CAIP Pydantic models — camelCase alias support."""

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Construction domain literals (from spec)
# ---------------------------------------------------------------------------

Trade = Literal[
    "mechanical", "electrical", "plumbing", "structural",
    "civil", "architectural", "fire-protection", "general", "multi-trade",
]

ProjectType = Literal[
    "commercial", "residential", "healthcare", "education",
    "industrial", "infrastructure", "mixed-use",
]

Certification = Literal["SOC2", "ISO27001", "FedRAMP"]

Integration = Literal[
    "procore", "acc", "bluebeam", "plangrid",
    "p6", "ms-project", "sage", "viewpoint",
]

Availability = Literal["in-stock", "made-to-order", "backordered"]


# ---------------------------------------------------------------------------
# Task lifecycle
# ---------------------------------------------------------------------------

class TaskState(str, Enum):
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    INPUT_REQUIRED = "input-required"


# ---------------------------------------------------------------------------
# Message / Part / Artifact
# ---------------------------------------------------------------------------

class Part(CaipBaseModel):
    """A2A content unit. Supports text and structured data."""

    text: str | None = None
    structured_data: dict[str, Any] | None = Field(None, alias="structuredData")

    @model_validator(mode="after")
    def _check_has_content(self) -> Part:
        if self.text is None and self.structured_data is None:
            raise ValueError("Part must have at least 'text' or 'structuredData'")
        return self


class Message(CaipBaseModel):
    role: Literal["user", "agent"]
    parts: list[Part] = Field(min_length=1)


class Artifact(CaipBaseModel):
    """Typed output from an agent."""

    name: str | None = None
    description: str | None = None
    parts: list[Part] = Field(min_length=1)
    metadata: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class TaskStatus(CaipBaseModel):
    state: TaskState
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    message: Message | None = None


class Task(CaipBaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context_id: str | None = Field(None, alias="contextId")
    status: TaskStatus
    artifacts: list[Artifact] = Field(default_factory=list)
    history: list[Message] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent Card + CAIP extensions
# ---------------------------------------------------------------------------

class SkillConstructionExt(CaipBaseModel):
    """x-construction extension on a skill."""

    task_type: str = Field(alias="taskType")
    input_schema: str | None = Field(None, alias="inputSchema")
    output_schema: str = Field(alias="outputSchema")


class AgentSkill(CaipBaseModel):
    id: str
    name: str
    description: str
    x_construction: SkillConstructionExt | None = Field(
        None, alias="x-construction",
    )


class SecurityExt(CaipBaseModel):
    """x-construction.security sub-object for CAIP security metadata."""

    trust_tier: int | None = Field(None, alias="trustTier")
    scopes_offered: list[str] = Field(default_factory=list, alias="scopesOffered")
    project_scoped: bool | None = Field(None, alias="projectScoped")
    delegation_supported: bool | None = Field(None, alias="delegationSupported")
    extended_card_url: str | None = Field(None, alias="extendedCardUrl")


class AgentConstructionExt(CaipBaseModel):
    """Top-level x-construction extension on an Agent Card."""

    trade: Trade
    csi_divisions: list[str] = Field(default_factory=list, alias="csiDivisions")
    project_types: list[ProjectType] = Field(default_factory=list, alias="projectTypes")
    certifications: list[Certification] = Field(default_factory=list)
    data_formats: dict[str, list[str]] = Field(
        default_factory=dict, alias="dataFormats",
    )
    integrations: list[Integration] = Field(default_factory=list)
    security: SecurityExt | None = None


class AgentCard(CaipBaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    url: str
    version: str = "1.0.0"
    capabilities: dict[str, bool] = Field(
        default_factory=lambda: {"streaming": False, "pushNotifications": False},
    )
    skills: list[AgentSkill] = Field(default_factory=list)
    x_construction: AgentConstructionExt | None = Field(
        None, alias="x-construction",
    )


# ---------------------------------------------------------------------------
# JSON-RPC 2.0
# ---------------------------------------------------------------------------

class JsonRpcError(CaipBaseModel):
    """Structured JSON-RPC 2.0 error object."""

    code: int
    message: str
    data: Any = None


class JsonRpcRequest(CaipBaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class JsonRpcResponse(CaipBaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None = None
    result: dict[str, Any] | None = None
    error: JsonRpcError | None = None

    @model_validator(mode="after")
    def _check_result_xor_error(self) -> JsonRpcResponse:
        if self.result is not None and self.error is not None:
            raise ValueError("JSON-RPC response must not have both 'result' and 'error'")
        if self.result is None and self.error is None:
            raise ValueError("JSON-RPC response must have either 'result' or 'error'")
        return self
