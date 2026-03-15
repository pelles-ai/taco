"""TACO — The A2A Construction Open-standard SDK"""

__version__ = "0.1.3"

# A2A protocol models (via types.py which re-exports from a2a-sdk)
# Compatibility helpers
from ._compat import (
    extract_structured_data,
    extract_text,
    get_data_parts,
    get_file_parts,
    get_message_text,
    # Upstream a2a.utils re-exports
    get_text_parts,
    make_artifact,
    make_data_part,
    make_message,
    make_text_part,
    new_agent_parts_message,
    new_agent_text_message,
    new_data_artifact,
    new_text_artifact,
)

# Convenience factories
from .agent_card import ConstructionAgentCard, ConstructionSkill

# TACO data schemas
from .schemas import (
    BOMV1,
    RFIV1,
    BOMAlternate,
    BOMFlaggedItem,
    BOMLineItem,
    BOMMetadata,
    BOMSchema,
    BOMSourceDocument,
    ChangeOrderLineItem,
    ChangeOrderMetadata,
    ChangeOrderSchema,
    ChangeOrderV1,
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
    ScheduleActivity,
    ScheduleMetadata,
    ScheduleMilestone,
    ScheduleSchema,
    ScheduleV1,
)
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
    FilePart,
    FlagSeverity,
    Integration,
    JSONRPCError,
    # Deprecated aliases (old casing)
    JsonRpcError,
    JSONRPCRequest,
    JsonRpcRequest,
    JSONRPCResponse,
    JsonRpcResponse,
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
)

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
    "FilePart",
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
    # Compatibility helpers (TACO)
    "extract_structured_data",
    "extract_text",
    "make_artifact",
    "make_data_part",
    "make_message",
    "make_text_part",
    # Upstream a2a.utils re-exports
    "get_text_parts",
    "get_data_parts",
    "get_file_parts",
    "new_agent_text_message",
    "new_agent_parts_message",
    "get_message_text",
    "new_text_artifact",
    "new_data_artifact",
    # TACO data schemas
    "BOMAlternate",
    "BOMFlaggedItem",
    "BOMLineItem",
    "BOMMetadata",
    "BOMSchema",
    "BOMSourceDocument",
    "BOMV1",
    "ChangeOrderLineItem",
    "ChangeOrderMetadata",
    "ChangeOrderSchema",
    "ChangeOrderV1",
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
    "ScheduleActivity",
    "ScheduleMetadata",
    "ScheduleMilestone",
    "ScheduleSchema",
    "ScheduleV1",
    # Server (lazy — requires taco[server])
    "A2AServer",
    "TaskHandler",
    "StreamingTaskHandler",
    # Agent (lazy — requires taco[all])
    "TacoAgent",
    # Monitor (lazy — requires taco[server])
    "enable_monitor",
    "EventBus",
    "MonitorServer",
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
    "TacoAgent": (".agent", "taco-agent[all]"),
    "enable_monitor": (".monitor", "taco-agent[server]"),
    "EventBus": (".monitor._event_bus", "taco-agent[server]"),
    "MonitorServer": (".monitor._server", "taco-agent[server]"),
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
