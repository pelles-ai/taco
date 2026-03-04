"""Compatibility helpers for constructing A2A SDK types.

These functions simplify Part/Message/Artifact construction, smoothing
the transition from TACO 0.1 (flat Part fields) to 0.2 (A2A SDK
discriminated union types).
"""

from __future__ import annotations

import uuid
from typing import Any

from a2a.types import (
    Artifact,
    DataPart,
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
) -> Message:
    """Create an A2A Message with auto-generated message_id."""
    return Message(
        role=Role(role),
        parts=parts,
        message_id=message_id or str(uuid.uuid4()),
    )


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
