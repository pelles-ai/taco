"""CAIP Agent Card — convenience factories for construction-specific A2A Agent Cards."""

from __future__ import annotations

from .models import (
    AgentCard,
    AgentConstructionExt,
    AgentSkill,
    SkillConstructionExt,
    Trade,
)


class ConstructionSkill:
    """Factory for building an AgentSkill with x-construction pre-populated.

    Example::

        skill = ConstructionSkill(
            id="generate-estimate",
            name="Generate Cost Estimate",
            description="Produces an estimate-v1 from a BOM",
            task_type="estimate",
            input_schema="bom-v1",
            output_schema="estimate-v1",
        )
        agent_skill = skill.to_a2a()
    """

    def __init__(
        self,
        *,
        id: str,
        name: str = "",
        description: str = "",
        task_type: str,
        input_schema: str | None = None,
        output_schema: str,
    ) -> None:
        self.id = id
        self.name = name or id
        self.description = description or f"CAIP skill: {id}"
        self.task_type = task_type
        self.input_schema = input_schema
        self.output_schema = output_schema

    def to_a2a(self) -> AgentSkill:
        """Convert to a standard A2A AgentSkill with x-construction extension."""
        return AgentSkill(
            id=self.id,
            name=self.name,
            description=self.description,
            x_construction=SkillConstructionExt(
                task_type=self.task_type,
                input_schema=self.input_schema,
                output_schema=self.output_schema,
            ),
        )


class ConstructionAgentCard:
    """Factory for building an AgentCard with x-construction pre-populated.

    Example::

        card = ConstructionAgentCard(
            name="My Estimating Agent",
            description="Estimates mechanical work",
            url="http://localhost:8001",
            trade="mechanical",
            csi_divisions=["22", "23"],
            skills=[skill],
        )
        agent_card = card.to_a2a()
        card.serve(host="0.0.0.0", port=8001)
    """

    def __init__(
        self,
        *,
        name: str,
        description: str = "",
        url: str = "",
        trade: Trade,
        csi_divisions: list[str],
        project_types: list[str] | None = None,
        data_formats: dict[str, list[str]] | None = None,
        integrations: list[str] | None = None,
        skills: list[ConstructionSkill] | None = None,
    ) -> None:
        self.name = name
        self.description = description or f"CAIP agent: {name}"
        self.url = url
        self.trade = trade
        self.csi_divisions = csi_divisions
        self.project_types = project_types or []
        self.data_formats = data_formats or {}
        self.integrations = integrations or []
        self.skills = skills or []

    def to_a2a(self) -> AgentCard:
        """Convert to a standard A2A AgentCard with x-construction extension."""
        return AgentCard(
            name=self.name,
            description=self.description,
            url=self.url,
            skills=[s.to_a2a() for s in self.skills],
            x_construction=AgentConstructionExt(
                trade=self.trade,
                csi_divisions=self.csi_divisions,
                project_types=self.project_types,
                data_formats=self.data_formats,
                integrations=self.integrations,
            ),
        )

    def serve(self, *, host: str = "0.0.0.0", port: int = 8080) -> None:
        """Start an A2A-compliant server for this agent.

        Requires the ``server`` extra: ``pip install caip[server]``
        """
        try:
            import uvicorn

            from .server import A2AServer
        except ImportError:
            raise ImportError(
                "Server dependencies not installed. "
                "Install with: pip install caip[server]"
            ) from None

        card = self.to_a2a()
        if not card.url:
            card.url = f"http://{host}:{port}"
        server = A2AServer(card)
        uvicorn.run(server.app, host=host, port=port)
