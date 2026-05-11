"""Compatibility helpers for constructing A2A SDK types.

These functions simplify Part/Message/Artifact construction, smoothing
the transition between TACO releases and A2A SDK versions.

In a2a-sdk v1.0 the upstream ``a2a.utils.message`` / ``a2a.utils.parts``
/ ``a2a.utils.artifact`` modules were removed and replaced with
protobuf-shaped helpers in ``a2a.helpers.proto_helpers``. While TACO is
still on the v0.3 wire format (via ``a2a.compat.v0_3.types``) we keep
Pydantic-shaped versions of the previously re-exported helpers here so
the public ``taco.*`` surface does not change. They will be retired
together with the v0_3 compat shim in a later phase.
"""

from __future__ import annotations

import uuid
from typing import Any

from a2a.compat.v0_3.types import (
    Artifact,
    DataPart,
    FilePart,
    Message,
    Part,
    Role,
    TextPart,
)


def make_text_part(text: str) -> Part:
    """Create a Part containing text."""
    return Part(root=TextPart(text=text))


def make_data_part(data: dict[str, Any]) -> Part:
    """Create a Part containing structured data."""
    return Part(root=DataPart(data=data))


def make_message(
    role: str,
    parts: list[Part],
    *,
    message_id: str | None = None,
    reference_task_ids: list[str] | None = None,
) -> Message:
    """Create an A2A Message with auto-generated message_id.

    ``reference_task_ids`` lists prior tasks this message logically
    follows up on (A2A v1 spec). TACO uses it to thread RFI responses
    back to the originating RFI task, change-order approvals back to
    the proposal task, etc.
    """
    kwargs: dict[str, Any] = {
        "role": Role(role),
        "parts": parts,
        "message_id": message_id or str(uuid.uuid4()),
    }
    if reference_task_ids:
        kwargs["reference_task_ids"] = list(reference_task_ids)
    return Message(**kwargs)


def make_artifact(
    parts: list[Part],
    *,
    name: str | None = None,
    description: str | None = None,
    artifact_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Artifact:
    """Create an A2A Artifact with auto-generated artifact_id."""
    return Artifact(
        artifact_id=artifact_id or str(uuid.uuid4()),
        parts=parts,
        name=name,
        description=description,
        metadata=metadata,
    )


def extract_text(part: Part) -> str | None:
    """Extract text from a Part, returning None if not a TextPart."""
    if isinstance(part.root, TextPart):
        return part.root.text
    return None


def extract_structured_data(part: Part) -> dict[str, Any] | None:
    """Extract structured data from a Part, returning None if not a DataPart."""
    if isinstance(part.root, DataPart):
        return part.root.data
    return None


# ---------------------------------------------------------------------------
# Pydantic-shaped equivalents of the helpers ``a2a.utils`` used to expose.
# Re-implemented locally because v1.0 removed those modules; we still want
# the public ``taco.*`` surface (and existing user code) to keep working.
# ---------------------------------------------------------------------------


def get_text_parts(parts: list[Part]) -> list[str]:
    """Return the text payloads of every ``TextPart`` in ``parts``."""
    return [p.root.text for p in parts if isinstance(p.root, TextPart)]


def get_data_parts(parts: list[Part]) -> list[dict[str, Any]]:
    """Return the data payloads of every ``DataPart`` in ``parts``."""
    return [p.root.data for p in parts if isinstance(p.root, DataPart)]


def get_file_parts(parts: list[Part]) -> list[FilePart]:
    """Return every ``FilePart`` in ``parts``."""
    return [p.root for p in parts if isinstance(p.root, FilePart)]


def get_message_text(message: Message, separator: str = "\n") -> str:
    """Concatenate the text of every ``TextPart`` in ``message.parts``."""
    return separator.join(get_text_parts(message.parts))


def new_agent_text_message(text: str, *, message_id: str | None = None) -> Message:
    """Create an agent-role ``Message`` with a single ``TextPart``."""
    return make_message("agent", [make_text_part(text)], message_id=message_id)


def new_agent_parts_message(
    parts: list[Part],
    *,
    message_id: str | None = None,
) -> Message:
    """Create an agent-role ``Message`` with the given parts."""
    return make_message("agent", parts, message_id=message_id)


def new_text_artifact(
    *,
    name: str,
    text: str,
    description: str | None = None,
) -> Artifact:
    """Create an ``Artifact`` containing a single ``TextPart``."""
    return make_artifact(
        parts=[make_text_part(text)],
        name=name,
        description=description,
    )


def new_data_artifact(
    *,
    name: str,
    data: dict[str, Any],
    description: str | None = None,
) -> Artifact:
    """Create an ``Artifact`` containing a single ``DataPart``."""
    return make_artifact(
        parts=[make_data_part(data)],
        name=name,
        description=description,
    )
