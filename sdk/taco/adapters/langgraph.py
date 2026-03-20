"""LangGraph adapter — wrap a compiled LangGraph StateGraph as a TACO A2A agent.

Usage::

    from langgraph.graph import StateGraph
    from taco.adapters.langgraph import LangGraphAdapter

    graph = builder.compile()
    adapter = LangGraphAdapter(graph)
    server.register_handler("estimate", adapter.as_handler())
    server.register_streaming_handler("estimate", adapter.as_streaming_handler())

    # Or use the convenience method:
    adapter.register_on(server, "estimate", streaming=True)
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from .._compat import make_artifact, make_data_part, make_text_part
from ..types import Artifact, Part, Task

logger = logging.getLogger("taco.adapters.langgraph")


def _check_langgraph_installed() -> None:
    """Raise a helpful ImportError if langgraph is not installed."""
    try:
        import langgraph  # noqa: F401
    except ImportError:
        raise ImportError(
            "langgraph is required for LangGraphAdapter. "
            "Install it with: pip install taco-agent[langgraph]"
        ) from None


class LangGraphAdapter:
    """Bridge between a compiled LangGraph graph and TACO task handlers.

    Parameters
    ----------
    graph:
        A compiled LangGraph ``StateGraph`` (must support ``ainvoke`` and ``astream``).
    input_key:
        State key to inject input data into (default ``"input"``).
    output_key:
        State key to read the result from (default ``"output"``).
    state_factory:
        Custom ``(task, input_data) -> dict`` to build the full graph input state.
        When provided, *input_key* is ignored.
    output_factory:
        Custom ``(final_state) -> Artifact`` to build the output artifact.
        When provided, *output_key* is ignored.
    stream_filter:
        Custom ``(chunk) -> Part | None`` for streaming. When provided,
        ``astream`` is called with ``stream_mode="updates"`` and each chunk
        is passed through this filter. Return ``None`` to skip a chunk.
    artifact_name:
        Name for the output artifact (default ``"langgraph-result"``).
    artifact_description:
        Optional description for the output artifact.
    """

    def __init__(
        self,
        graph: Any,
        *,
        input_key: str = "input",
        output_key: str = "output",
        state_factory: Callable[[Task, dict], dict] | None = None,
        output_factory: Callable[[dict], Artifact] | None = None,
        stream_filter: Callable[[Any], Part | None] | None = None,
        artifact_name: str = "langgraph-result",
        artifact_description: str | None = None,
    ) -> None:
        _check_langgraph_installed()
        self.graph = graph
        self.input_key = input_key
        self.output_key = output_key
        self.state_factory = state_factory
        self.output_factory = output_factory
        self.stream_filter = stream_filter
        self.artifact_name = artifact_name
        self.artifact_description = artifact_description

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_input(self, task: Task, input_data: dict) -> dict:
        """Build the graph input state dict."""
        if self.state_factory is not None:
            return self.state_factory(task, input_data)
        return {self.input_key: input_data}

    def _build_config(self, task: Task) -> dict:
        """Build the LangGraph ``config`` dict, mapping ``context_id`` to ``thread_id``."""
        config: dict[str, Any] = {}
        if task.context_id:
            config["configurable"] = {"thread_id": task.context_id}
        return config

    def _build_artifact(self, final_state: dict) -> Artifact:
        """Build a TACO artifact from the graph's final state."""
        if self.output_factory is not None:
            return self.output_factory(final_state)

        value = final_state.get(self.output_key)
        if value is None:
            logger.warning(
                "Graph output key %r not found in final state; returning empty artifact",
                self.output_key,
            )
            return make_artifact(
                parts=[make_text_part("")],
                name=self.artifact_name,
                description=self.artifact_description,
            )

        if isinstance(value, str):
            parts = [make_text_part(value)]
        elif isinstance(value, dict):
            parts = [make_data_part(value)]
        else:
            parts = [make_text_part(str(value))]

        return make_artifact(
            parts=parts,
            name=self.artifact_name,
            description=self.artifact_description,
        )

    def _check_interrupt(self, result: dict) -> None:
        """Log a warning if the graph result contains an interrupt signal."""
        if "__interrupt__" in result:
            logger.warning(
                "LangGraph graph returned an interrupt: %s. "
                "TACO does not yet support INPUT_REQUIRED; returning partial result.",
                result["__interrupt__"],
            )

    # ------------------------------------------------------------------
    # Handler factories
    # ------------------------------------------------------------------

    def as_handler(self) -> Callable[[Task, dict], Any]:
        """Return a TACO ``TaskHandler`` that invokes the graph synchronously.

        Signature: ``async def handler(task, input_data) -> Artifact``
        """
        adapter = self

        async def handler(task: Task, input_data: dict) -> Artifact:
            graph_input = adapter._build_input(task, input_data)
            config = adapter._build_config(task)
            result = await adapter.graph.ainvoke(graph_input, config=config)
            adapter._check_interrupt(result)
            return adapter._build_artifact(result)

        return handler

    def as_streaming_handler(self) -> Callable[[Task, dict], AsyncIterator[Part]]:
        """Return a TACO ``StreamingTaskHandler`` that streams graph output.

        Signature: ``async def handler(task, input_data) -> AsyncIterator[Part]``
        """
        adapter = self

        async def handler(task: Task, input_data: dict) -> AsyncIterator[Part]:
            graph_input = adapter._build_input(task, input_data)
            config = adapter._build_config(task)

            if adapter.stream_filter is not None:
                async for chunk in adapter.graph.astream(
                    graph_input, config=config, stream_mode="updates"
                ):
                    part = adapter.stream_filter(chunk)
                    if part is not None:
                        yield part
            else:
                async for chunk in adapter.graph.astream(
                    graph_input, config=config, stream_mode="messages", version="v2"
                ):
                    if not isinstance(chunk, tuple) or len(chunk) < 2:
                        continue
                    message_chunk = chunk[0]
                    metadata = chunk[1]
                    if metadata.get("langgraph_node") is None:
                        continue
                    content = getattr(message_chunk, "content", None)
                    if content:
                        yield make_text_part(str(content))

        return handler

    def register_on(
        self,
        server: Any,
        task_type: str,
        *,
        streaming: bool = False,
    ) -> None:
        """Convenience method to register handlers on an ``A2AServer``.

        Parameters
        ----------
        server:
            A ``taco.server.A2AServer`` instance.
        task_type:
            The TACO task type to register for.
        streaming:
            If ``True``, register both regular and streaming handlers.
            If ``False`` (default), register only the regular handler.
        """
        server.register_handler(task_type, self.as_handler())
        if streaming:
            server.register_streaming_handler(task_type, self.as_streaming_handler())
