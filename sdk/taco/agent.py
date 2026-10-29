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
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from .agent_card import ConstructionAgentCard
from .server import A2AServer, StreamingTaskHandler, TaskHandler
from .types import AgentCard, Task, TaskStore

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
        task_store: Optional :class:`TaskStore` for task persistence.
            Defaults to ``InMemoryTaskStore`` (state lost on restart).
            Pass a :class:`JsonFileTaskStore` or ``DatabaseTaskStore``
            for durable storage.
        peer_retry_attempts: How many times to try discovering each peer
            in the background after startup (default 5). A peer still
            missing after that is tried again when a request needs it.
        peer_retry_delay: Seconds between retry attempts (default 2.0).
        peer_startup_wait: Seconds startup waits for the first discovery
            round before the agent starts serving (default 2.0). Discovery
            carries on in the background, so agents that list each other
            as peers find each other once both are up.
        cors_origins: CORS origins for the server. ``None`` (the default)
            disables CORS middleware entirely.
        enable_monitor: Whether to enable the Agent Monitor UI at
            ``/monitor`` on this agent's port.
        monitor_auth_token: Token the monitor's API and WebSocket require
            (open the UI as ``/monitor/#token=<token>``). Set it whenever
            the agent's port is reachable by anyone but you: the monitor
            shows every request and response payload.
    """

    def __init__(
        self,
        agent_card: ConstructionAgentCard,
        *,
        task_store: TaskStore | None = None,
        peers: list[str] | str | None = None,
        peer_retry_attempts: int = 5,
        peer_retry_delay: float = 2.0,
        peer_startup_wait: float = 2.0,
        cors_origins: list[str] | None = None,
        enable_monitor: bool = False,
        monitor_auth_token: str | None = None,
    ) -> None:
        self._card = agent_card
        self._server = A2AServer(
            agent_card.to_a2a(),
            task_store=task_store,
            cors_origins=cors_origins,
            enable_monitor=enable_monitor,
            monitor_auth_token=monitor_auth_token,
        )

        # Peer communication (lazy imports to avoid requiring [client] extra)
        self._registry: AgentRegistry | None = None
        self._client_pool: dict[str, TacoClient] = {}
        self._peer_urls: list[str] = []
        self._peer_retry_attempts = peer_retry_attempts
        self._peer_retry_delay = peer_retry_delay
        self._peer_startup_wait = peer_startup_wait
        self._pending_peers: set[str] = set()
        self._discovery_task: asyncio.Task[None] | None = None
        self._has_monitor = enable_monitor

        if peers is not None:
            from .client import TacoClient as _TacoClient  # noqa: F811
            from .registry import AgentRegistry as _AgentRegistry

            self._client_cls = _TacoClient
            self._peer_urls = self._load_peers(peers)
            self._pending_peers = set(self._peer_urls)
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
                    # Discovery runs in the background: if startup waited
                    # for it, two agents that list each other would each
                    # wait for the other to start serving, and neither would.
                    self._discovery_task = asyncio.create_task(self._discover_peers())
                    await asyncio.wait({self._discovery_task}, timeout=self._peer_startup_wait)
                    try:
                        yield
                    finally:
                        self._discovery_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await self._discovery_task
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
        reference_task_ids: list[str] | None = None,
        return_immediately: bool = False,
        headers: dict[str, str] | None = None,
    ) -> Task:
        """Send a message to whichever peer agent handles *task_type*.

        Looks up the peer by skill ID/tag match, gets or creates a pooled
        :class:`TacoClient`, and calls ``send_message()``. When
        ``return_immediately`` is ``True``, the peer returns the Task as
        soon as it accepts the message rather than waiting for the
        terminal state — useful for long-running estimates and
        schedules where the caller plans to poll or watch via the
        Monitor UI.

        ``reference_task_ids`` (A2A v1) links this outbound call to prior
        tasks — natural fit for RFI → response or proposal → approval
        construction workflows.

        Returns:
            The resulting :class:`Task` with artifacts (or just the
            accepted task object when ``return_immediately`` is True).

        Raises:
            ValueError: No peers configured or no peer has the skill.
        """
        peer_url = await self._peer_url_for(task_type)
        client = self._get_or_create_client(peer_url)
        return await client.send_message(
            task_type,
            input_data,
            context_id=context_id,
            reference_task_ids=reference_task_ids,
            return_immediately=return_immediately,
            headers=headers,
        )

    async def stream_from_peer(
        self,
        task_type: str,
        input_data: dict[str, Any],
        *,
        context_id: str | None = None,
        reference_task_ids: list[str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a message from whichever peer agent handles *task_type*.

        Same lookup logic as :meth:`send_to_peer` but returns an SSE
        event iterator. ``reference_task_ids`` is forwarded onto the
        outbound stream request.

        Raises:
            ValueError: No peers configured or no peer has the skill.
        """
        peer_url = await self._peer_url_for(task_type)
        client = self._get_or_create_client(peer_url)
        async for event in client.stream_message(
            task_type,
            input_data,
            context_id=context_id,
            reference_task_ids=reference_task_ids,
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

    async def _peer_url_for(self, task_type: str) -> str:
        """Return the URL of a peer that handles *task_type*.

        Peers that have not been discovered yet are tried once more first.
        Requests go to the URL the peer was discovered at, never to the
        ``url`` its card declares (which may be empty, unreachable from
        here, or any host the peer chooses).

        Raises:
            ValueError: No peers configured or no peer has the skill.
        """
        if self._registry is None:
            raise ValueError(
                "No peers configured. Pass peers=... to TacoAgent() to enable peer communication."
            )
        found = self._find_peer_by_skill(task_type)
        if found is None and self._pending_peers:
            await self._discover_pending_once()
            found = self._find_peer_by_skill(task_type)
        if found is None:
            raise ValueError(f"No peer agent found for task type: {task_type}")
        return found[0]

    def _find_peer_by_skill(self, task_type: str) -> tuple[str, AgentCard] | None:
        """Find the first peer with a skill for *task_type*.

        Matches the skill's x-construction ``taskType``, its ``id`` or its
        ``tags``. Returns ``(url, card)`` with the URL the peer was found at.
        """
        if self._registry is None:
            return None
        for url, card in self._registry.entries():
            for skill in card.skills:
                xc = skill.x_construction
                if (
                    (xc is not None and xc.task_type == task_type)
                    or skill.id == task_type
                    or task_type in (skill.tags or [])
                ):
                    return url, card
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
        """Discover all configured peers concurrently, retrying each.

        Started in the background on app startup when peers are configured.
        A peer still missing after its retries stays pending and is tried
        again by :meth:`_peer_url_for` when a request needs it.
        """
        if self._registry is None:
            logger.warning("No registry available — skipping peer discovery")
            return
        pending = sorted(self._pending_peers)
        await asyncio.gather(*(self._discover_with_retries(url) for url in pending))

    async def _discover_with_retries(self, url: str) -> None:
        for attempt in range(1, self._peer_retry_attempts + 1):
            try:
                await self._discover_one(url)
                return
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

    async def _discover_one(self, url: str) -> None:
        assert self._registry is not None
        card = await self._registry.register(url)
        self._pending_peers.discard(url)
        logger.info(
            "Discovered peer: %s at %s (skills: %s)",
            card.name,
            url,
            [s.id for s in card.skills],
        )

    async def _discover_pending_once(self) -> None:
        """Try each still-undiscovered peer once, concurrently."""
        results = await asyncio.gather(
            *(self._discover_one(url) for url in sorted(self._pending_peers)),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Peer still not reachable: %s", result)

    async def _close_clients(self) -> None:
        """Close all pooled TacoClients. Called on app shutdown."""
        for url, client in self._client_pool.items():
            try:
                await client.close()
            except Exception:
                logger.warning("Error closing client for %s", url, exc_info=True)
        self._client_pool.clear()
