"""TACO Agent Registry — discover construction agents by trade, skill, and capability."""

from __future__ import annotations

try:
    import httpx
except ImportError:
    raise ImportError(
        "Client dependencies not installed. Install with: pip install taco[client]"
    ) from None

from .types import AgentCard, get_construction_ext, get_skill_construction_ext


class AgentRegistry:
    """In-memory agent registry with HTTP-based discovery."""

    def __init__(self, *, timeout: float = 10.0) -> None:
        self._agents: dict[str, AgentCard] = {}
        self._timeout = timeout

    async def register(self, agent_url: str) -> AgentCard:
        """Discover an agent by URL and store its card."""
        agent_url = agent_url.rstrip("/")
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{agent_url}/.well-known/agent.json")
            resp.raise_for_status()
        card = AgentCard.model_validate(resp.json())
        self._agents[agent_url] = card
        return card

    def register_card(self, agent_url: str, card: AgentCard) -> None:
        """Register an agent card directly (useful for testing)."""
        self._agents[agent_url.rstrip("/")] = card

    def find(
        self,
        *,
        trade: str | None = None,
        task_type: str | None = None,
        csi_division: str | None = None,
        project_type: str | None = None,
    ) -> list[AgentCard]:
        """Find agents matching the given filters (all optional, AND logic)."""
        results: list[AgentCard] = []
        for card in self._agents.values():
            xc = get_construction_ext(card)
            if trade is not None:
                if xc is None or xc.trade != trade:
                    continue
            if csi_division is not None:
                if xc is None or csi_division not in xc.csi_divisions:
                    continue
            if project_type is not None:
                if xc is None or project_type not in xc.project_types:
                    continue
            if task_type is not None:
                has_task = any(
                    (sxc := get_skill_construction_ext(s)) is not None
                    and sxc.task_type == task_type
                    for s in card.skills
                )
                if not has_task:
                    continue
            results.append(card)
        return results

    def list_agents(self) -> list[AgentCard]:
        """Return all registered agent cards."""
        return list(self._agents.values())

    def remove(self, agent_url: str) -> bool:
        """Remove an agent by URL. Returns True if it was present."""
        return self._agents.pop(agent_url.rstrip("/"), None) is not None

    async def refresh(self, agent_url: str) -> AgentCard:
        """Re-fetch and update an agent's card."""
        return await self.register(agent_url)
