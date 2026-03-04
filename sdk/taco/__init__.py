"""TACO — The A2A Construction Open-standard SDK"""

__version__ = "0.2.0"

# A2A protocol models (via types.py which re-exports from a2a-sdk)
from .types import (
    AgentCapabilities,
    AgentCard,
    AgentConstructionExt,
    AgentSkill,
    Artifact,
    Availability,
    BOMUnit,
    Certification,
    DataPart,
    FlagSeverity,
    Integration,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    Message,
    Part,
    ProjectType,
    RFICategory,
    RFIPriority,
    Role,
    SecurityExt,
    SkillConstructionExt,
    TacoBaseModel,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
    Trade,
    get_construction_ext,
    get_skill_construction_ext,
    # Deprecated aliases (old casing)
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
)

# Compatibility helpers
from ._compat import (
    extract_structured_data,
    extract_text,
    make_artifact,
    make_data_part,
    make_message,
    make_text_part,
)

# TACO data schemas
from .schemas import (
    BOMAlternate,
    BOMFlaggedItem,
    BOMLineItem,
    BOMMetadata,
    BOMSchema,
    BOMV1,
    BOMSourceDocument,
    ChangeOrderSchema,
    EstimateLineItem,
    EstimateMetadata,
    EstimateSummary,
    EstimateV1,
    QuoteLineItem,
    QuoteMetadata,
    QuoteSummary,
    QuoteTerms,
    QuoteV1,
    RFIAssignee,
    RFICoordinates,
    RFIMetadata,
    RFIReference,
    RFISchema,
    RFIV1,
    ScheduleSchema,
)

# Convenience factories
from .agent_card import ConstructionAgentCard, ConstructionSkill

__all__ = [
    # A2A protocol models
    "AgentCapabilities",
    "AgentCard",
    "AgentConstructionExt",
    "AgentSkill",
    "Artifact",
    "Availability",
    "BOMUnit",
    "Certification",
    "DataPart",
    "FlagSeverity",
    "Integration",
    "JSONRPCError",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JsonRpcError",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "Message",
    "Part",
    "ProjectType",
    "RFICategory",
    "RFIPriority",
    "Role",
    "SecurityExt",
    "SkillConstructionExt",
    "TacoBaseModel",
    "Task",
    "TaskState",
    "TaskStatus",
    "TextPart",
    "Trade",
    "get_construction_ext",
    "get_skill_construction_ext",
    # Compatibility helpers
    "extract_structured_data",
    "extract_text",
    "make_artifact",
    "make_data_part",
    "make_message",
    "make_text_part",
    # TACO data schemas
    "BOMAlternate",
    "BOMFlaggedItem",
    "BOMLineItem",
    "BOMMetadata",
    "BOMSchema",
    "BOMSourceDocument",
    "BOMV1",
    "ChangeOrderSchema",
    "EstimateLineItem",
    "EstimateMetadata",
    "EstimateSummary",
    "EstimateV1",
    "QuoteLineItem",
    "QuoteMetadata",
    "QuoteSummary",
    "QuoteTerms",
    "QuoteV1",
    "RFIAssignee",
    "RFICoordinates",
    "RFIMetadata",
    "RFIReference",
    "RFISchema",
    "RFIV1",
    "ScheduleSchema",
    # Server (lazy — requires taco[server])
    "A2AServer",
    "TaskHandler",
    "StreamingTaskHandler",
    # Convenience factories
    "ConstructionAgentCard",
    "ConstructionSkill",
    # Client (lazy — requires taco[client])
    "TacoClient",
    "TacoClientError",
    "RpcError",
    "AgentRegistry",
]


_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # name -> (module, install hint)
    "A2AServer": (".server", "taco-agent[server]"),
    "TaskHandler": (".server", "taco-agent[server]"),
    "StreamingTaskHandler": (".server", "taco-agent[server]"),
    "TacoClient": (".client", "taco-agent[client]"),
    "TacoClientError": (".client", "taco-agent[client]"),
    "RpcError": (".client", "taco-agent[client]"),
    "AgentRegistry": (".registry", "taco-agent[client]"),
}


def __getattr__(name: str):
    entry = _LAZY_IMPORTS.get(name)
    if entry is None:
        raise AttributeError(f"module 'taco' has no attribute {name!r}")
    module_path, install_hint = entry
    try:
        import importlib
        module = importlib.import_module(module_path, package=__name__)
    except ImportError:
        raise ImportError(
            f"Dependencies not installed. Install with: pip install {install_hint}"
        ) from None
    return getattr(module, name)
