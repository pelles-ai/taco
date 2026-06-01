"""
Browser-only stub of the TACO SDK for the in-browser sandbox.

Mirrors the public API surface of `taco-agent` (ConstructionAgentCard,
ConstructionSkill, make_artifact, make_data_part, TacoClient.send_message),
but runs entirely client-side under Pyodide. No network calls — `send_message`
returns canned, schema-shaped responses keyed by task type.

Use this to feel the SDK ergonomics. For real agent-to-agent traffic, install
`taco-agent` from PyPI.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


VERSION = "0.3.11-browser"


# --------------------------------------------------------------------- models


@dataclass
class ConstructionSkill:
    id: str
    task_type: str
    input_schema: str | None = None
    output_schema: str | None = None
    name: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {"id": self.id, "taskType": self.task_type}
        if self.input_schema:
            d["inputSchema"] = self.input_schema
        if self.output_schema:
            d["outputSchema"] = self.output_schema
        if self.name:
            d["name"] = self.name
        if self.description:
            d["description"] = self.description
        return d


@dataclass
class ConstructionAgentCard:
    name: str
    trade: str
    csi_divisions: list[str] = field(default_factory=list)
    skills: list[ConstructionSkill] = field(default_factory=list)
    description: str | None = None
    url: str | None = None
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "url": self.url or "http://localhost:8080",
            "description": self.description or "",
            "skills": [s.to_dict() for s in self.skills],
            "x-construction": {
                "trade": self.trade,
                "csiDivisions": list(self.csi_divisions),
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class Part:
    kind: str
    text: str | None = None
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"kind": self.kind}
        if self.text is not None:
            d["text"] = self.text
        if self.data is not None:
            d["data"] = self.data
        return d


@dataclass
class Artifact:
    artifact_id: str
    parts: list[Part]
    name: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifactId": self.artifact_id,
            "parts": [p.to_dict() for p in self.parts],
            **({"name": self.name} if self.name else {}),
            **({"description": self.description} if self.description else {}),
        }


@dataclass
class Task:
    task_id: str
    task_type: str
    state: str
    artifacts: list[Artifact] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.task_id,
            "status": {"state": self.state},
            "metadata": {"taskType": self.task_type},
            "artifacts": [a.to_dict() for a in self.artifacts],
        }


# ------------------------------------------------------------------- helpers


def make_text_part(text: str) -> Part:
    return Part(kind="text", text=text)


def make_data_part(data: dict[str, Any]) -> Part:
    return Part(kind="data", data=data)


def make_artifact(
    parts: list[Part], name: str | None = None, description: str | None = None
) -> Artifact:
    return Artifact(
        artifact_id=str(uuid.uuid4()),
        parts=list(parts),
        name=name,
        description=description,
    )


def extract_structured_data(part: Part) -> Any:
    return part.data


# ---------------------------------------------------------------- mock client


_MOCK_RESPONSES = {
    "echo": lambda payload: {"received": payload, "message": "Hello from TACO!"},
    "takeoff": lambda payload: {
        "projectId": payload.get("projectId", "PRJ-001"),
        "trade": payload.get("trade", "mechanical"),
        "lineItems": [
            {"description": "Copper pipe 1/2in", "quantity": 120, "unit": "LF"},
            {"description": "90 deg elbow 1/2in", "quantity": 24, "unit": "EA"},
            {"description": "Ball valve 1/2in", "quantity": 8, "unit": "EA"},
        ],
        "schema": "bom-v1",
    },
    "estimate": lambda payload: {
        "projectId": payload.get("projectId", "PRJ-001"),
        "currency": "USD",
        "lineItems": [
            {"description": "Material", "subtotal": 28400},
            {"description": "Labor (120 hrs @ $145)", "subtotal": 17400},
            {"description": "Equipment", "subtotal": 3200},
        ],
        "overheadAndProfit": 7400,
        "total": 56400,
        "schema": "estimate-v1",
    },
    "material-procurement": lambda payload: {
        "supplier": "PipeWorks Supply",
        "currency": "USD",
        "items": [
            {"sku": "CU-12", "unitPrice": 8.40, "qty": 120, "leadDays": 2},
            {"sku": "EL-90-12", "unitPrice": 2.10, "qty": 24, "leadDays": 2},
        ],
        "validUntil": "2026-06-15",
        "schema": "quote-v1",
    },
    "rfi-generation": lambda payload: {
        "rfiId": "RFI-0042",
        "subject": "Conflicting pipe routing at column line C/4",
        "priority": "high",
        "drawingReferences": ["P-201", "P-202"],
        "schema": "rfi-v1",
    },
}


class TacoClient:
    """Browser-only mock — returns canned shaped responses, no network."""

    def __init__(self, agent_url: str):
        self.agent_url = agent_url

    def send_message(self, task_type: str, payload: dict[str, Any]) -> Task:
        responder = _MOCK_RESPONSES.get(task_type)
        if responder is None:
            return Task(
                task_id=str(uuid.uuid4()),
                task_type=task_type,
                state="failed",
                artifacts=[
                    make_artifact(
                        [make_text_part(f"No mock for task_type={task_type!r}")]
                    )
                ],
            )
        return Task(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            state="completed",
            artifacts=[
                make_artifact(
                    [make_data_part(responder(payload))],
                    name=f"{task_type}-result",
                )
            ],
        )


__all__ = [
    "VERSION",
    "ConstructionAgentCard",
    "ConstructionSkill",
    "Part",
    "Artifact",
    "Task",
    "TacoClient",
    "make_text_part",
    "make_data_part",
    "make_artifact",
    "extract_structured_data",
]
