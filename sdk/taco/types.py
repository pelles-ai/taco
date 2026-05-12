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

# A2A SDK v1.0+ moved the wire-format types to protobuf. The Pydantic
# v0.3-shaped types we still rely on live at ``a2a.compat.v0_3.types``;
# re-exporting them here keeps the rest of TACO unaware of the shim.
from a2a._base import A2ABaseModel
from a2a.compat.v0_3.types import (  # noqa: F401 — re-exports
    AgentCapabilities,
    AgentExtension,
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
    PushNotificationAuthenticationInfo,
    PushNotificationConfig,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskPushNotificationConfig,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from a2a.server.tasks import InMemoryTaskStore, TaskStore  # noqa: F401 — re-export
from pydantic import Field

# ---------------------------------------------------------------------------
# v1.0 migration: TACO is now on a2a-sdk >=1.0.2 via the v0_3 compat layer.
# The next migration step (taco/V1_MIGRATION.md Phase 3) drops the compat
# shim and adopts native protobuf types — at that point this re-export
# block flips to ``from a2a.types import …``, the Part constructor
# flattens (``Part(text=…)`` instead of ``Part(root=TextPart(text=…))``),
# and enum literals upper-case (``TaskState.TASK_STATE_COMPLETED``).
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
# Formal A2A v1 extension declaration for x-construction
# ---------------------------------------------------------------------------

#: Canonical URI for the TACO ``x-construction`` agent-card extension.
#:
#: A2A v1 added ``AgentCapabilities.extensions[]`` — a formal way for
#: agents to advertise which protocol extensions they implement, identified
#: by URI. Cards carrying the inline ``x-construction`` field should also
#: list this URI under capabilities so v1-aware clients can negotiate.
X_CONSTRUCTION_EXTENSION_URI = "https://taco.construction/extensions/x-construction/v1"

_X_CONSTRUCTION_EXTENSION_DESCRIPTION = (
    "TACO construction-domain agent metadata: trade, CSI divisions, project "
    "types, certifications, data formats, integrations, security."
)


def apply_construction_extension_declaration(card: AgentCard) -> AgentCard:
    """Ensure ``card.capabilities.extensions[]`` advertises ``x-construction``.

    Mutates and returns ``card``. No-op if ``card.x_construction`` is ``None``
    or if the URI is already declared (idempotent — safe to call repeatedly).
    """
    if card.x_construction is None:
        return card
    if card.capabilities is None:
        card.capabilities = AgentCapabilities(streaming=False)
    existing = card.capabilities.extensions or []
    if any(ext.uri == X_CONSTRUCTION_EXTENSION_URI for ext in existing):
        return card
    card.capabilities.extensions = [
        *existing,
        AgentExtension(
            uri=X_CONSTRUCTION_EXTENSION_URI,
            description=_X_CONSTRUCTION_EXTENSION_DESCRIPTION,
            required=False,
        ),
    ]
    return card


# ---------------------------------------------------------------------------
# Deprecated aliases for JSON-RPC types (old casing)
# ---------------------------------------------------------------------------

JsonRpcError = JSONRPCError
JsonRpcRequest = JSONRPCRequest
JsonRpcResponse = JSONRPCResponse
