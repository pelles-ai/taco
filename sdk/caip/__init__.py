"""CAIP — Construction A2A Interoperability Protocol SDK"""

__version__ = "0.1.0"

# A2A protocol models
from .models import (
    AgentCard,
    AgentConstructionExt,
    AgentSkill,
    Artifact,
    Availability,
    CaipBaseModel,
    Certification,
    Integration,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    Message,
    Part,
    ProjectType,
    SecurityExt,
    SkillConstructionExt,
    Task,
    TaskState,
    TaskStatus,
    Trade,
)

# CAIP data schemas
from .schemas import (
    BOMSchema,
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
    RFISchema,
    ScheduleSchema,
)

# Convenience factories
from .agent_card import ConstructionAgentCard, ConstructionSkill

# Client stubs
from .registry import AgentRegistry
from .client import CAIPClient

__all__ = [
    # A2A protocol models
    "AgentCard",
    "AgentConstructionExt",
    "AgentSkill",
    "Artifact",
    "Availability",
    "CaipBaseModel",
    "Certification",
    "Integration",
    "JsonRpcError",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "Message",
    "Part",
    "ProjectType",
    "SecurityExt",
    "SkillConstructionExt",
    "Task",
    "TaskState",
    "TaskStatus",
    "Trade",
    # CAIP data schemas
    "BOMSchema",
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
    "RFISchema",
    "ScheduleSchema",
    # Server (lazy — requires caip[server])
    "A2AServer",
    "TaskHandler",
    # Convenience factories
    "ConstructionAgentCard",
    "ConstructionSkill",
    # Client stubs
    "AgentRegistry",
    "CAIPClient",
]


def __getattr__(name: str):
    if name in ("A2AServer", "TaskHandler"):
        try:
            from .server import A2AServer, TaskHandler  # noqa: F811
        except ImportError:
            raise ImportError(
                "Server dependencies not installed. "
                "Install with: pip install caip[server]"
            ) from None
        if name == "A2AServer":
            return A2AServer
        return TaskHandler
    raise AttributeError(f"module 'caip' has no attribute {name!r}")
