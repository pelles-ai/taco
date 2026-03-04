"""Backward-compatible re-exports of TACO and A2A types.

In TACO 0.2+ the canonical definitions live in ``taco.types`` (for
construction-specific types and A2A re-exports). This module exists
for backward compatibility — existing code that imports from
``taco.models`` continues to work.
"""

from .types import (  # noqa: F401
    # A2A SDK re-exports
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
    # Construction types
    AgentCard,
    AgentConstructionExt,
    AgentSkill,
    Availability,
    BOMUnit,
    Certification,
    FlagSeverity,
    Integration,
    ProjectType,
    RFICategory,
    RFIPriority,
    SecurityExt,
    SkillConstructionExt,
    TacoBaseModel,
    Trade,
    # Helpers
    get_construction_ext,
    get_skill_construction_ext,
    # Deprecated aliases (old casing)
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
)
