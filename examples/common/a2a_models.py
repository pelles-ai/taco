"""A2A protocol models — re-exported from the TACO SDK.

Example agents import from here for convenience. The canonical
definitions live in ``taco.types``.
"""

from taco.types import (  # noqa: F401
    AgentCapabilities,
    AgentCard,
    AgentConstructionExt,
    AgentSkill,
    Artifact,
    DataPart,
    JSONRPCRequest,
    JSONRPCResponse,
    Message,
    Part,
    Role,
    SkillConstructionExt,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)
from taco._compat import (  # noqa: F401
    extract_structured_data,
    extract_text,
    make_artifact,
    make_data_part,
    make_message,
    make_text_part,
)
