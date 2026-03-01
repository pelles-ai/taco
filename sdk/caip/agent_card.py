"""CAIP Agent Card — construction-specific extensions to A2A Agent Cards."""

from __future__ import annotations


class ConstructionSkill:
    """A construction-aware skill entry for an A2A Agent Card."""

    def __init__(
        self,
        *,
        id: str,
        task_type: str,
        input_schema: str | None = None,
        output_schema: str,
    ) -> None:
        self.id = id
        self.task_type = task_type
        self.input_schema = input_schema
        self.output_schema = output_schema


class ConstructionAgentCard:
    """A construction-aware A2A Agent Card with x-construction extensions."""

    def __init__(
        self,
        *,
        name: str,
        trade: str,
        csi_divisions: list[str] | None = None,
        project_types: list[str] | None = None,
        data_formats: dict[str, list[str]] | None = None,
        integrations: list[str] | None = None,
        skills: list[ConstructionSkill] | None = None,
    ) -> None:
        self.name = name
        self.trade = trade
        self.csi_divisions = csi_divisions or []
        self.project_types = project_types or []
        self.data_formats = data_formats or {}
        self.integrations = integrations or []
        self.skills = skills or []

    def serve(self, *, host: str = "0.0.0.0", port: int = 8080) -> None:
        raise NotImplementedError("Agent serving is not yet implemented")
