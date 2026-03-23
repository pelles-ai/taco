"""TACO types — construction domain types and A2A SDK re-exports.

Construction-specific Literal types, extension models, and TACO
subclasses of AgentCard/AgentSkill that carry x-construction metadata.
Also re-exports core A2A types for convenience.

All A2A SDK type imports are centralized here so that only this file
(and ``_compat.py``) need to change when migrating to a2a-sdk v1.0.
Other TACO modules should import A2A types from ``taco.types``.
"""

from __future__ import annotations

from typing import Literal

from a2a._base import A2ABaseModel
from a2a.server.tasks import InMemoryTaskStore, TaskStore  # noqa: F401 — re-export
from a2a.types import (  # noqa: F401 — re-exports
    AgentCapabilities,
    Artifact,
    DataPart,
    FilePart,
    JSONRPCError,
    JSONRPCErrorResponse,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCSuccessResponse,
    Message,
    Part,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from pydantic import Field

# ---------------------------------------------------------------------------
# _V1_COMPAT: a2a-sdk v1.0 migration notes
#
# When a2a-sdk ships v1.0, it switches from Pydantic models to protobuf
# messages. Key changes:
#
#   Part(text="hello")            replaces Part(root=TextPart(text="hello"))
#   TaskState.TASK_STATE_COMPLETED replaces TaskState.completed
#   Role.ROLE_USER                 replaces Role.user
#   AgentCard.supported_interfaces replaces AgentCard.url
#
# Migration path:
#   1. Switch imports below to  from a2a.compat.v0_3.types import ...
#      (zero behavior change — v0.3 compat layer provides same API)
#   2. Update _compat.py helpers for new Part constructor
#   3. Incrementally adopt native v1.0 protobuf types
#
# The v0.3 compat layer is at: a2a.compat.v0_3.types
# ---------------------------------------------------------------------------

# Backward-compat alias
TacoBaseModel = A2ABaseModel

# ---------------------------------------------------------------------------
# Construction domain literals
# ---------------------------------------------------------------------------

Trade = Literal[
    "mechanical",
    "electrical",
    "plumbing",
    "structural",
    "civil",
    "architectural",
    "fire-protection",
    "general",
    "multi-trade",
]

ProjectType = Literal[
    "commercial",
    "residential",
    "healthcare",
    "education",
    "industrial",
    "infrastructure",
    "mixed-use",
]

Certification = Literal["SOC2", "ISO27001", "FedRAMP"]

Integration = Literal[
    "procore",
    "acc",
    "bluebeam",
    "plangrid",
    "p6",
    "ms-project",
    "sage",
    "viewpoint",
]

Availability = Literal["in-stock", "made-to-order", "backordered"]

BOMUnit = Literal["EA", "LF", "SF", "CF", "CY", "TON", "LB", "GAL", "LS"]

FlagSeverity = Literal["info", "warning", "error"]

RFICategory = Literal[
    "design-conflict",
    "missing-information",
    "clarification",
    "substitution",
    "coordination",
    "code-compliance",
]

RFIPriority = Literal["low", "medium", "high", "critical"]


# ---------------------------------------------------------------------------
# Construction extension models
# ---------------------------------------------------------------------------


class SkillConstructionExt(A2ABaseModel):
    """x-construction extension on a skill."""

    task_type: str = Field(alias="taskType")
    input_schema: str | None = Field(None, alias="inputSchema")
    output_schema: str = Field(alias="outputSchema")


class SecurityExt(A2ABaseModel):
    """x-construction.security sub-object for TACO security metadata."""

    trust_tier: int | None = Field(None, alias="trustTier")
    scopes_offered: list[str] = Field(default_factory=list, alias="scopesOffered")
    project_scoped: bool | None = Field(None, alias="projectScoped")
    delegation_supported: bool | None = Field(None, alias="delegationSupported")
    extended_card_url: str | None = Field(None, alias="extendedCardUrl")


class AgentConstructionExt(A2ABaseModel):
    """Top-level x-construction extension on an Agent Card."""

    trade: Trade
    csi_divisions: list[str] = Field(default_factory=list, alias="csiDivisions")
    project_types: list[ProjectType] = Field(default_factory=list, alias="projectTypes")
    certifications: list[Certification] = Field(default_factory=list)
    data_formats: dict[str, list[str]] = Field(
        default_factory=dict,
        alias="dataFormats",
    )
    integrations: list[Integration] = Field(default_factory=list)
    security: SecurityExt | None = None


# ---------------------------------------------------------------------------
# TACO Agent Card / Skill — A2A SDK types with x-construction
# ---------------------------------------------------------------------------


class AgentSkill(A2ABaseModel):
    """A2A AgentSkill with TACO x-construction extension.

    Extends the standard skill with an optional x-construction field
    for construction-specific task routing metadata.
    """

    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    input_modes: list[str] | None = Field(None, alias="inputModes")
    output_modes: list[str] | None = Field(None, alias="outputModes")
    examples: list[str] | None = None
    x_construction: SkillConstructionExt | None = Field(
        None,
        alias="x-construction",
    )


class AgentCard(A2ABaseModel):
    """A2A AgentCard with TACO x-construction extension.

    Extends the standard agent card with an optional x-construction
    field for construction-specific agent metadata (trade, CSI divisions,
    project types, etc.).
    """

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    url: str
    version: str = "1.0.0"
    default_input_modes: list[str] = Field(
        default_factory=lambda: ["application/json"],
        alias="defaultInputModes",
    )
    default_output_modes: list[str] = Field(
        default_factory=lambda: ["application/json"],
        alias="defaultOutputModes",
    )
    capabilities: AgentCapabilities = Field(
        default_factory=lambda: AgentCapabilities(streaming=False),
    )
    skills: list[AgentSkill] = Field(default_factory=list)
    x_construction: AgentConstructionExt | None = Field(
        None,
        alias="x-construction",
    )


# ---------------------------------------------------------------------------
# Helper functions for extracting x-construction from cards/skills
# ---------------------------------------------------------------------------


def get_construction_ext(card: AgentCard) -> AgentConstructionExt | None:
    """Extract x-construction extension from a TACO AgentCard."""
    return card.x_construction


def get_skill_construction_ext(skill: AgentSkill) -> SkillConstructionExt | None:
    """Extract x-construction extension from a TACO AgentSkill."""
    return skill.x_construction


# ---------------------------------------------------------------------------
# Deprecated aliases for JSON-RPC types (old casing)
# ---------------------------------------------------------------------------

JsonRpcError = JSONRPCError
JsonRpcRequest = JSONRPCRequest
JsonRpcResponse = JSONRPCResponse
