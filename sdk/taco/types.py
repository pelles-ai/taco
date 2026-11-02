"""TACO types — construction domain types and A2A SDK re-exports.

Construction-specific Literal types, extension models, and TACO
subclasses of AgentCard/AgentSkill that carry x-construction metadata.
Also re-exports core A2A types for convenience.

All A2A SDK type imports are centralized here so that only this file
(and ``_compat.py``) need to change when migrating to a2a-sdk v1.0.
Other TACO modules should import A2A types from ``taco.types``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

# A2A SDK v1.0+ moved the wire-format types to protobuf. The Pydantic
# v0.3-shaped types we still rely on live at ``a2a.compat.v0_3.types``;
# re-exporting them here keeps the rest of TACO unaware of the shim.
from a2a._base import A2ABaseModel
from a2a.compat.v0_3.types import (  # noqa: F401 — re-exports
    AgentCapabilities,
    AgentExtension,
    APIKeySecurityScheme,
    Artifact,
    AuthorizationCodeOAuthFlow,
    ClientCredentialsOAuthFlow,
    DataPart,
    FilePart,
    HTTPAuthSecurityScheme,
    ImplicitOAuthFlow,
    JSONRPCError,
    JSONRPCErrorResponse,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCSuccessResponse,
    Message,
    MutualTLSSecurityScheme,
    OAuth2SecurityScheme,
    OAuthFlows,
    OpenIdConnectSecurityScheme,
    Part,
    PasswordOAuthFlow,
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
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# v1.0 migration: TACO is on a2a-sdk >=1.1.1 via the v0_3 compat layer.
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
    """x-construction.security sub-object for TACO security metadata.

    Holds construction-specific security advertisements (trust tier, TACO
    scopes, project scoping, delegation). Also surfaces three v1-aware
    capability flags (``mtls_supported``, ``pkce_required``,
    ``device_code_supported``) so a registry or orchestrator can quickly
    filter agents on auth modality without parsing the full ``securitySchemes``
    block on the agent card.
    """

    trust_tier: int | None = Field(None, alias="trustTier")
    scopes_offered: list[str] = Field(default_factory=list, alias="scopesOffered")
    project_scoped: bool | None = Field(None, alias="projectScoped")
    delegation_supported: bool | None = Field(None, alias="delegationSupported")
    extended_card_url: str | None = Field(None, alias="extendedCardUrl")
    mtls_supported: bool | None = Field(None, alias="mtlsSupported")
    pkce_required: bool | None = Field(None, alias="pkceRequired")
    device_code_supported: bool | None = Field(None, alias="deviceCodeSupported")


# ---------------------------------------------------------------------------
# v1 OAuth flow mirrors
# ---------------------------------------------------------------------------
# A2A v1 added two OAuth features that the v0_3 compat layer's
# ``OAuthFlows`` model does not carry:
#   1. ``pkceRequired`` on AuthorizationCode flow
#   2. ``deviceCode`` flow (RFC 8628)
# These mirrors let users declare them today on TACO agent cards. When
# Phase 3 (epic #18) flips TACO to native v1 wire types, these models
# become straight pass-throughs to ``a2a.types``.


class AuthorizationCodeOAuthFlowV1(A2ABaseModel):
    """v1-shaped AuthorizationCode OAuth flow with optional ``pkceRequired``.

    Equivalent to ``a2a.compat.v0_3.types.AuthorizationCodeOAuthFlow`` plus
    the v1 ``pkce_required`` field (RFC 7636).
    """

    authorization_url: str = Field(alias="authorizationUrl")
    token_url: str = Field(alias="tokenUrl")
    refresh_url: str | None = Field(None, alias="refreshUrl")
    scopes: dict[str, str] = Field(default_factory=dict)
    pkce_required: bool | None = Field(None, alias="pkceRequired")


class DeviceCodeOAuthFlow(A2ABaseModel):
    """OAuth 2.0 Device Authorization Grant flow (RFC 8628).

    A2A v1 added this flow for headless / TV-style clients. The v0_3 compat
    layer's ``OAuthFlows`` does not include it, so TACO ships a Pydantic
    mirror that survives serialization round-trips and will become a direct
    pass-through to ``a2a.types`` after the v1 wire cutover (epic #18).
    """

    device_authorization_url: str = Field(alias="deviceAuthorizationUrl")
    token_url: str = Field(alias="tokenUrl")
    refresh_url: str | None = Field(None, alias="refreshUrl")
    scopes: dict[str, str] = Field(default_factory=dict)


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
    for construction-specific task routing metadata. Other A2A skill fields
    (e.g. ``security``) are kept as extra fields.
    """

    model_config = ConfigDict(extra="allow")

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


def _models_to_json(value: Any) -> Any:
    """Dump Pydantic models anywhere inside ``value`` to JSON-shaped dicts."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(value, Mapping):
        return {key: _models_to_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_models_to_json(item) for item in value]
    return value


class AgentCard(A2ABaseModel):
    """A2A AgentCard with TACO x-construction extension.

    Extends the standard agent card with an optional x-construction
    field for construction-specific agent metadata (trade, CSI divisions,
    project types, etc.).

    Standard A2A fields TACO does not model explicitly (``provider``,
    ``documentationUrl``, ``preferredTransport``, ``signatures``, ...) are
    kept as extra fields, so a card fetched from another agent round-trips
    without losing them.
    """

    model_config = ConfigDict(extra="allow")

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
    security_schemes: dict[str, dict[str, Any]] | None = Field(
        None,
        alias="securitySchemes",
        description="A2A security schemes by name, e.g. an oauth2 or http bearer scheme.",
    )
    security: list[dict[str, list[str]]] | None = Field(
        None,
        description="A2A security requirements: scheme name -> required scopes.",
    )
    x_construction: AgentConstructionExt | None = Field(
        None,
        alias="x-construction",
    )

    @field_validator("security_schemes", mode="before")
    @classmethod
    def _schemes_to_json(cls, value: Any) -> Any:
        # Scheme and flow models (taco.OAuth2SecurityScheme,
        # taco.DeviceCodeOAuthFlow, ...) may appear anywhere in the mapping.
        return _models_to_json(value)

    @model_validator(mode="before")
    @classmethod
    def _read_v1_card(cls, data: Any) -> Any:
        return with_v03_card_fields(data) if isinstance(data, dict) else data


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


#: A2A protocol versions a TACO server answers on its JSON-RPC endpoint, in
#: the order its card lists them (clients pick the first they support).
SERVED_PROTOCOL_VERSIONS = ("1.0", "0.3")


def construction_extension_params(card: AgentCard) -> dict[str, Any] | None:
    """``x-construction`` as A2A v1 readers see it (ADR-0010).

    A v1 card parser keeps the ``x-construction`` extension declaration in
    ``capabilities.extensions[]`` but drops the inline ``x-construction``
    fields. Its ``params`` therefore carry the same object as the card's
    inline field, plus ``skills``: each skill's ``x-construction`` by skill
    id. ``None`` when the card has no ``x-construction``.
    """
    if card.x_construction is None:
        return None
    params: dict[str, Any] = card.x_construction.model_dump(
        mode="json", by_alias=True, exclude_none=True
    )
    skills = {
        skill.id: skill.x_construction.model_dump(mode="json", by_alias=True, exclude_none=True)
        for skill in card.skills
        if skill.x_construction is not None
    }
    if skills:
        params["skills"] = skills
    return params


def _extension_params(data: dict[str, Any]) -> dict[str, Any] | None:
    capabilities = data.get("capabilities")
    extensions = (
        capabilities.get("extensions")
        if isinstance(capabilities, dict)
        else getattr(capabilities, "extensions", None)
    )
    for extension in extensions or []:
        uri = extension.get("uri") if isinstance(extension, dict) else extension.uri
        if uri == X_CONSTRUCTION_EXTENSION_URI:
            params = extension.get("params") if isinstance(extension, dict) else extension.params
            return params if isinstance(params, dict) else None
    return None


def with_v03_card_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Fill a card's v0.3 fields from its A2A v1 ones, when they are missing.

    A card written for A2A v1 alone has no top-level ``url`` (only
    ``supportedInterfaces``) and no inline ``x-construction`` (only the
    extension declaration's ``params``). This copies the first JSON-RPC
    interface's URL to ``url`` and the ``params`` to the inline
    ``x-construction`` fields of the card and its skills, so TACO's readers
    treat v1-only and dual cards alike. Fields already present win.
    """
    data = dict(data)
    if not data.get("url"):
        for interface in data.get("supportedInterfaces") or []:
            if (
                isinstance(interface, dict)
                and interface.get("url")
                and interface.get("protocolBinding", "JSONRPC") == "JSONRPC"
            ):
                data["url"] = interface["url"]
                break

    params = _extension_params(data)
    if not params:
        return data
    if data.get("x-construction") is None and data.get("x_construction") is None:
        data["x-construction"] = {k: v for k, v in params.items() if k != "skills"}
    skill_params = params.get("skills")
    if isinstance(skill_params, dict) and isinstance(data.get("skills"), list):
        data["skills"] = [
            {**skill, "x-construction": skill_params[skill["id"]]}
            if isinstance(skill, dict)
            and skill.get("id") in skill_params
            and skill.get("x-construction") is None
            and skill.get("x_construction") is None
            else skill
            for skill in data["skills"]
        ]
    return data


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
