"""CAIP — Construction A2A Interoperability Protocol SDK"""

__version__ = "0.1.0"

# A2A protocol models
from .models import (
    AgentCard,
    AgentConstructionExt,
    AgentSkill,
    Artifact,
    Availability,
    BOMUnit,
    CaipBaseModel,
    Certification,
    FlagSeverity,
    Integration,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    Message,
    Part,
    ProjectType,
    RFICategory,
    RFIPriority,
    SecurityExt,
    SkillConstructionExt,
    Task,
    TaskState,
    TaskStatus,
    Trade,
)

# CAIP data schemas
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
    "AgentCard",
    "AgentConstructionExt",
    "AgentSkill",
    "Artifact",
    "Availability",
    "BOMUnit",
    "CaipBaseModel",
    "Certification",
    "FlagSeverity",
    "Integration",
    "JsonRpcError",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "Message",
    "Part",
    "ProjectType",
    "RFICategory",
    "RFIPriority",
    "SecurityExt",
    "SkillConstructionExt",
    "Task",
    "TaskState",
    "TaskStatus",
    "Trade",
    # CAIP data schemas
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
    # Server (lazy — requires caip[server])
    "A2AServer",
    "TaskHandler",
    "StreamingTaskHandler",
    # Convenience factories
    "ConstructionAgentCard",
    "ConstructionSkill",
    # Client (lazy — requires caip[client])
    "CAIPClient",
    "CAIPClientError",
    "RpcError",
    "AgentRegistry",
]


_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # name -> (module, install hint)
    "A2AServer": (".server", "caip[server]"),
    "TaskHandler": (".server", "caip[server]"),
    "StreamingTaskHandler": (".server", "caip[server]"),
    "CAIPClient": (".client", "caip[client]"),
    "CAIPClientError": (".client", "caip[client]"),
    "RpcError": (".client", "caip[client]"),
    "AgentRegistry": (".registry", "caip[client]"),
}


def __getattr__(name: str):
    entry = _LAZY_IMPORTS.get(name)
    if entry is None:
        raise AttributeError(f"module 'caip' has no attribute {name!r}")
    module_path, install_hint = entry
    try:
        import importlib
        module = importlib.import_module(module_path, package=__name__)
    except ImportError:
        raise ImportError(
            f"Dependencies not installed. Install with: pip install {install_hint}"
        ) from None
    return getattr(module, name)
