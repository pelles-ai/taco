"""TACO Agent Registry — discover construction agents by trade, skill, and capability."""

from __future__ import annotations

import json
import logging
import os
import tempfile

try:
    import httpx
except ImportError:
    raise ImportError(
        "Client dependencies not installed. Install with: pip install taco-agent[client]"
    ) from None

from .types import AgentCard, get_construction_ext, get_skill_construction_ext

logger = logging.getLogger("a2a")


class AgentRegistry:
    """In-memory agent registry with HTTP-based discovery.

    Optionally persists registered agents to a JSON file when
    ``persistence_path`` is provided.
    """

    def __init__(
        self,
        *,
        timeout: float = 10.0,
        persistence_path: str | None = None,
    ) -> None:
        self._agents: dict[str, AgentCard] = {}
        self._timeout = timeout
        self._persistence_path = persistence_path
        if persistence_path:
            self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._persistence_path or not os.path.exists(self._persistence_path):
            return
        try:
            with open(self._persistence_path) as f:
                data = json.load(f)
            for url, card_data in data.items():
                self._agents[url] = AgentCard.model_validate(card_data)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning(
                "Failed to load registry from %s: %s — starting empty",
                self._persistence_path,
                exc,
            )
            self._agents = {}

    def _save(self) -> None:
        if not self._persistence_path:
            return
        data = {
            url: card.model_dump(by_alias=True, exclude_none=True)
            for url, card in self._agents.items()
        }
        dir_path = os.path.dirname(self._persistence_path) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self._persistence_path)
        except BaseException:
            os.unlink(tmp_path)
            raise

    # ------------------------------------------------------------------

    async def register(self, agent_url: str) -> AgentCard:
        """Discover an agent by URL and store its card.

        Tries the A2A v0.3+ path ``/.well-known/agent-card.json`` first,
        falling back to the legacy ``/.well-known/agent.json`` on 404.
        Sends the ``A2A-Version`` header so v1 peers can negotiate.
        """
        from .client import A2A_PROTOCOL_VERSION

        agent_url = agent_url.rstrip("/")
        headers = {"A2A-Version": A2A_PROTOCOL_VERSION}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{agent_url}/.well-known/agent-card.json",
                headers=headers,
            )
            if resp.status_code == 404:
                resp = await client.get(
                    f"{agent_url}/.well-known/agent.json",
                    headers=headers,
                )
            resp.raise_for_status()
        card = AgentCard.model_validate(resp.json())
        self._agents[agent_url] = card
        self._save()
        return card

    def register_card(self, agent_url: str, card: AgentCard) -> None:
        """Register an agent card directly (useful for testing)."""
        self._agents[agent_url.rstrip("/")] = card
        self._save()

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
            if trade is not None and (xc is None or xc.trade != trade):
                continue
            if csi_division is not None and (xc is None or csi_division not in xc.csi_divisions):
                continue
            if project_type is not None and (xc is None or project_type not in xc.project_types):
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
        result = self._agents.pop(agent_url.rstrip("/"), None) is not None
        if result:
            self._save()
        return result

    async def refresh(self, agent_url: str) -> AgentCard:
        """Re-fetch and update an agent's card."""
        return await self.register(agent_url)
