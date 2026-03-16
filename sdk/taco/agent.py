"""TacoAgent — bidirectional A2A agent that can both receive and send requests.

Composes A2AServer (inbound), AgentRegistry (discovery), and a TacoClient
pool (outbound) into a single convenient object.

Usage::

    from taco import TacoAgent, ConstructionAgentCard, ConstructionSkill

    card = ConstructionAgentCard(
        name="My Agent",
        url="http://localhost:8100",
        trade="electrical",
        skills=[ConstructionSkill(id="analyze", name="Analyze", ...)],
    )
    agent = TacoAgent(card, peers="agents.yaml", enable_monitor=True)
    agent.register_handler("analyze", my_handler)

    # Inside a handler, call a peer agent:
    task = await agent.send_to_peer("data-query", {"query": "SELECT ..."})
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from .agent_card import ConstructionAgentCard
from .server import A2AServer, StreamingTaskHandler, TaskHandler
from .types import AgentCard, Task

if TYPE_CHECKING:
    from .client import TacoClient
    from .registry import AgentRegistry

logger = logging.getLogger("taco.agent")


class TacoAgent:
    """A TACO agent that can both receive and send A2A requests.

    Composes :class:`A2AServer` (inbound), :class:`AgentRegistry` (peer
    discovery), and a :class:`TacoClient` pool (outbound calls) into a
    single object.

    Args:
        agent_card: The construction agent card describing this agent.
        peers: Peer agent URLs for discovery. Accepts either:
            - A file path (str) to a YAML/JSON config with
              ``agents: [{url: "http://..."}]`` format
            - A list of URL strings
            - ``None`` to disable peer communication
        peer_retry_attempts: How many times to retry discovering each peer
            at startup (default 5).
        peer_retry_delay: Seconds between retry attempts (default 2.0).
        cors_origins: CORS origins for the server (default ``["*"]``).
        enable_monitor: Whether to enable the Agent Monitor UI at
            ``/monitor`` on this agent's port.
    """

    def __init__(
        self,
        agent_card: ConstructionAgentCard,
        *,
        peers: list[str] | str | None = None,
        peer_retry_attempts: int = 5,
        peer_retry_delay: float = 2.0,
        cors_origins: list[str] | None = None,
        enable_monitor: bool = False,
    ) -> None:
        self._card = agent_card
        self._server = A2AServer(
            agent_card.to_a2a(),
            cors_origins=cors_origins,
            enable_monitor=enable_monitor,
        )

        # Peer communication (lazy imports to avoid requiring [client] extra)
        self._registry: AgentRegistry | None = None
        self._client_pool: dict[str, TacoClient] = {}
        self._peer_urls: list[str] = []
        self._peer_retry_attempts = peer_retry_attempts
        self._peer_retry_delay = peer_retry_delay
        self._has_monitor = enable_monitor

        if peers is not None:
            from .client import TacoClient as _TacoClient  # noqa: F811
            from .registry import AgentRegistry as _AgentRegistry

            self._client_cls = _TacoClient
            self._peer_urls = self._load_peers(peers)
            self._registry = _AgentRegistry()

            # Instrument registry for the monitor
            if self._has_monitor:
                from .monitor import _instrument_registry, get_event_bus

                _instrument_registry(self._registry, get_event_bus())

            # Attach lifespan for peer discovery and cleanup
            existing_lifespan = self._server.app.router.lifespan_context

            @asynccontextmanager
            async def _lifespan(app: Any) -> AsyncIterator[None]:
                async with existing_lifespan(app):
                    await self._discover_peers()
                    try:
                        yield
                    finally:
                        await self._close_clients()

            self._server.app.router.lifespan_context = _lifespan

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def app(self):
        """The underlying ASGI/FastAPI application (for uvicorn)."""
        return self._server.app

    @property
    def agent_card(self) -> ConstructionAgentCard:
        """The construction agent card for this agent."""
        return self._card

    @property
    def server(self) -> A2AServer:
        """The underlying A2AServer (inbound only)."""
        return self._server

    @property
    def registry(self) -> AgentRegistry | None:
        """The peer agent registry, or ``None`` if peers not configured."""
        return self._registry

    # ------------------------------------------------------------------
    # Delegated handler registration
    # ------------------------------------------------------------------

    def register_handler(self, task_type: str, handler: TaskHandler) -> None:
        """Register an async handler for a TACO task type.

        Delegates to :meth:`A2AServer.register_handler`.
        """
        self._server.register_handler(task_type, handler)

    def register_streaming_handler(
        self,
        task_type: str,
        handler: StreamingTaskHandler,
    ) -> None:
        """Register a streaming handler for a TACO task type.

        Delegates to :meth:`A2AServer.register_streaming_handler`.
        """
        self._server.register_streaming_handler(task_type, handler)

    # ------------------------------------------------------------------
    # Peer communication
    # ------------------------------------------------------------------

    async def send_to_peer(
        self,
        task_type: str,
        input_data: dict[str, Any],
        *,
        context_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Task:
        """Send a message to whichever peer agent handles *task_type*.

        Looks up the peer by skill ID/tag match, gets or creates a pooled
        :class:`TacoClient`, and calls ``send_message()``.

        Returns:
            The resulting :class:`Task` with artifacts.

        Raises:
            ValueError: No peers configured or no peer has the skill.
        """
        if self._registry is None:
            raise ValueError(
                "No peers configured. Pass peers=... to TacoAgent() to enable peer communication."
            )

        card = self._find_peer_by_skill(task_type)
        if card is None:
            raise ValueError(f"No peer agent found for task type: {task_type}")

        client = self._get_or_create_client(card.url)
        return await client.send_message(
            task_type, input_data, context_id=context_id, headers=headers,
        )

    async def stream_from_peer(
        self,
        task_type: str,
        input_data: dict[str, Any],
        *,
        context_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a message from whichever peer agent handles *task_type*.

        Same lookup logic as :meth:`send_to_peer` but returns an SSE
        event iterator.

        Raises:
            ValueError: No peers configured or no peer has the skill.
        """
        if self._registry is None:
            raise ValueError(
                "No peers configured. Pass peers=... to TacoAgent() to enable peer communication."
            )

        card = self._find_peer_by_skill(task_type)
        if card is None:
            raise ValueError(f"No peer agent found for task type: {task_type}")

        client = self._get_or_create_client(card.url)
        async for event in client.stream_message(
            task_type,
            input_data,
            context_id=context_id,
            headers=headers,
        ):
            yield event

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_peers(peers: list[str] | str) -> list[str]:
        """Parse peer URLs from a file path or return the list as-is."""
        if isinstance(peers, list):
            return list(peers)

        # It's a file path — read and parse
        path = peers
        if path.endswith((".yaml", ".yml")):
            try:
                import yaml
            except ImportError:
                raise ImportError(
                    "PyYAML is required to load peers from a YAML file. "
                    "Install with: pip install pyyaml"
                ) from None
            with open(path) as f:
                config = yaml.safe_load(f)
        elif path.endswith(".json"):
            import json

            with open(path) as f:
                config = json.load(f)
        else:
            # Try YAML first, fall back to JSON
            try:
                import yaml

                with open(path) as f:
                    config = yaml.safe_load(f)
            except Exception:
                import json

                with open(path) as f:
                    config = json.load(f)

        agents = config.get("agents", [])
        urls = []
        for entry in agents:
            if isinstance(entry, dict) and "url" in entry:
                urls.append(entry["url"])
            else:
                logger.warning("Skipping malformed peer entry: %s", entry)
        return urls

    def _find_peer_by_skill(self, skill_id: str) -> AgentCard | None:
        """Find the first peer agent with a skill matching *skill_id*.

        Matches on ``skill.id`` or ``skill.tags``.
        """
        if self._registry is None:
            return None
        for card in self._registry.list_agents():
            for skill in card.skills:
                if skill.id == skill_id or skill_id in (skill.tags or []):
                    return card
        return None

    def _get_or_create_client(self, agent_url: str) -> TacoClient:
        """Return a pooled TacoClient, creating and instrumenting if needed."""
        if agent_url not in self._client_pool:
            client = self._client_cls(agent_url=agent_url)
            if self._has_monitor:
                from .monitor import _instrument_client, get_event_bus

                _instrument_client(client, get_event_bus())
            self._client_pool[agent_url] = client
        return self._client_pool[agent_url]

    async def _discover_peers(self) -> None:
        """Discover all configured peer agents with retries.

        Called automatically on app startup when peers are configured.
        """
        if self._registry is None:
            logger.warning("No registry available — skipping peer discovery")
            return
        for url in self._peer_urls:
            for attempt in range(1, self._peer_retry_attempts + 1):
                try:
                    card = await self._registry.register(url)
                    skills = [s.id for s in card.skills]
                    logger.info(
                        "Discovered peer: %s at %s (skills: %s)",
                        card.name,
                        url,
                        skills,
                    )
                    break
                except Exception as e:
                    if attempt < self._peer_retry_attempts:
                        logger.warning(
                            "Peer at %s not ready (attempt %d/%d): %s",
                            url,
                            attempt,
                            self._peer_retry_attempts,
                            e,
                        )
                        await asyncio.sleep(self._peer_retry_delay)
                    else:
                        logger.error(
                            "Failed to discover peer at %s after %d attempts: %s",
                            url,
                            self._peer_retry_attempts,
                            e,
                        )

    async def _close_clients(self) -> None:
        """Close all pooled TacoClients. Called on app shutdown."""
        for url, client in self._client_pool.items():
            try:
                await client.close()
            except Exception:
                logger.warning("Error closing client for %s", url, exc_info=True)
        self._client_pool.clear()
