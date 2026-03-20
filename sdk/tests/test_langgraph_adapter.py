"""Tests for taco.adapters.langgraph — LangGraphAdapter."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from taco._compat import make_text_part
from taco.types import (
    Artifact,
    DataPart,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)


@pytest.fixture(autouse=True)
def _patch_langgraph_check():
    """Disable the langgraph import check for all tests."""
    with patch("taco.adapters.langgraph._check_langgraph_installed"):
        yield


@pytest.fixture()
def mock_graph():
    """A mock LangGraph compiled graph with ainvoke and astream."""
    graph = MagicMock()
    graph.ainvoke = AsyncMock(return_value={"output": "result text"})

    async def _astream(*args: Any, **kwargs: Any) -> AsyncIterator:
        msg = MagicMock()
        msg.content = "streamed token"
        metadata = {"langgraph_node": "agent"}
        yield (msg, metadata)

    graph.astream = MagicMock(side_effect=_astream)
    return graph


@pytest.fixture()
def sample_task():
    """A minimal TACO Task for handler testing."""
    return Task(
        id="task-1",
        context_id="ctx-1",
        status=TaskStatus(state=TaskState.working),
    )


def _get_adapter(**kwargs):
    """Import and construct a LangGraphAdapter (import check already patched)."""
    from taco.adapters.langgraph import LangGraphAdapter

    return LangGraphAdapter(**kwargs)


# ======================================================================
# TestLangGraphAdapterInit
# ======================================================================


class TestLangGraphAdapterInit:
    def test_defaults(self, mock_graph):
        adapter = _get_adapter(graph=mock_graph)
        assert adapter.graph is mock_graph
        assert adapter.input_key == "input"
        assert adapter.output_key == "output"
        assert adapter.state_factory is None
        assert adapter.output_factory is None
        assert adapter.stream_filter is None
        assert adapter.artifact_name == "langgraph-result"
        assert adapter.artifact_description is None

    def test_custom_params(self, mock_graph):
        factory = lambda task, data: {"custom": data}  # noqa: E731
        out_factory = lambda state: MagicMock(spec=Artifact)  # noqa: E731
        filt = lambda chunk: None  # noqa: E731

        adapter = _get_adapter(
            graph=mock_graph,
            input_key="query",
            output_key="answer",
            state_factory=factory,
            output_factory=out_factory,
            stream_filter=filt,
            artifact_name="custom-result",
            artifact_description="A custom artifact",
        )
        assert adapter.input_key == "query"
        assert adapter.output_key == "answer"
        assert adapter.state_factory is factory
        assert adapter.output_factory is out_factory
        assert adapter.stream_filter is filt
        assert adapter.artifact_name == "custom-result"
        assert adapter.artifact_description == "A custom artifact"

    def test_import_check_called(self, mock_graph):
        """Verify _check_langgraph_installed is called during construction."""
        with patch("taco.adapters.langgraph._check_langgraph_installed") as mock_check:
            _get_adapter(graph=mock_graph)
            mock_check.assert_called_once()


# ======================================================================
# TestInputMapping
# ======================================================================


class TestInputMapping:
    def test_default_key(self, mock_graph, sample_task):
        adapter = _get_adapter(graph=mock_graph)
        result = adapter._build_input(sample_task, {"foo": "bar"})
        assert result == {"input": {"foo": "bar"}}

    def test_custom_key(self, mock_graph, sample_task):
        adapter = _get_adapter(graph=mock_graph, input_key="query")
        result = adapter._build_input(sample_task, {"q": "test"})
        assert result == {"query": {"q": "test"}}

    def test_state_factory(self, mock_graph, sample_task):
        def factory(task, data):
            return {"task_id": task.id, "data": data}

        adapter = _get_adapter(graph=mock_graph, state_factory=factory)
        result = adapter._build_input(sample_task, {"x": 1})
        assert result == {"task_id": "task-1", "data": {"x": 1}}

    def test_empty_input(self, mock_graph, sample_task):
        adapter = _get_adapter(graph=mock_graph)
        result = adapter._build_input(sample_task, {})
        assert result == {"input": {}}


# ======================================================================
# TestOutputMapping
# ======================================================================


class TestOutputMapping:
    def test_string_output(self, mock_graph):
        adapter = _get_adapter(graph=mock_graph)
        artifact = adapter._build_artifact({"output": "hello world"})
        assert isinstance(artifact, Artifact)
        assert len(artifact.parts) == 1
        assert isinstance(artifact.parts[0].root, TextPart)
        assert artifact.parts[0].root.text == "hello world"
        assert artifact.name == "langgraph-result"

    def test_dict_output(self, mock_graph):
        adapter = _get_adapter(graph=mock_graph)
        artifact = adapter._build_artifact({"output": {"key": "val"}})
        assert isinstance(artifact.parts[0].root, DataPart)
        assert artifact.parts[0].root.data == {"key": "val"}

    def test_missing_key(self, mock_graph):
        adapter = _get_adapter(graph=mock_graph)
        artifact = adapter._build_artifact({"other_key": "value"})
        assert isinstance(artifact.parts[0].root, TextPart)
        assert artifact.parts[0].root.text == ""

    def test_non_str_non_dict_output(self, mock_graph):
        adapter = _get_adapter(graph=mock_graph)
        artifact = adapter._build_artifact({"output": 42})
        assert isinstance(artifact.parts[0].root, TextPart)
        assert artifact.parts[0].root.text == "42"

    def test_custom_output_key(self, mock_graph):
        adapter = _get_adapter(graph=mock_graph, output_key="answer")
        artifact = adapter._build_artifact({"answer": "the answer"})
        assert artifact.parts[0].root.text == "the answer"

    def test_custom_output_factory(self, mock_graph):
        from taco._compat import make_artifact, make_data_part

        def factory(state):
            return make_artifact(
                parts=[make_data_part({"custom": state.get("x", "none")})],
                name="factory-result",
            )

        adapter = _get_adapter(graph=mock_graph, output_factory=factory)
        artifact = adapter._build_artifact({"x": "value"})
        assert artifact.name == "factory-result"
        assert artifact.parts[0].root.data == {"custom": "value"}

    def test_artifact_name_and_description(self, mock_graph):
        adapter = _get_adapter(
            graph=mock_graph,
            artifact_name="my-artifact",
            artifact_description="A test artifact",
        )
        artifact = adapter._build_artifact({"output": "test"})
        assert artifact.name == "my-artifact"
        assert artifact.description == "A test artifact"


# ======================================================================
# TestConfigMapping
# ======================================================================


class TestConfigMapping:
    def test_context_id_maps_to_thread_id(self, mock_graph, sample_task):
        adapter = _get_adapter(graph=mock_graph)
        config = adapter._build_config(sample_task)
        assert config == {"configurable": {"thread_id": "ctx-1"}}

    def test_empty_context_id(self, mock_graph):
        task = Task(
            id="task-2",
            context_id="",
            status=TaskStatus(state=TaskState.working),
        )
        adapter = _get_adapter(graph=mock_graph)
        config = adapter._build_config(task)
        assert config == {}


# ======================================================================
# TestAsHandler
# ======================================================================


class TestAsHandler:
    async def test_invokes_graph(self, mock_graph, sample_task):
        adapter = _get_adapter(graph=mock_graph)
        handler = adapter.as_handler()

        artifact = await handler(sample_task, {"data": "value"})

        mock_graph.ainvoke.assert_awaited_once_with(
            {"input": {"data": "value"}},
            config={"configurable": {"thread_id": "ctx-1"}},
        )
        assert isinstance(artifact, Artifact)
        assert artifact.parts[0].root.text == "result text"

    async def test_passes_config(self, mock_graph, sample_task):
        adapter = _get_adapter(graph=mock_graph)
        handler = adapter.as_handler()
        await handler(sample_task, {})

        call_kwargs = mock_graph.ainvoke.call_args
        assert call_kwargs.kwargs["config"]["configurable"]["thread_id"] == "ctx-1"

    async def test_interrupt_warning(self, mock_graph, sample_task, caplog):
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "output": "partial",
                "__interrupt__": {"reason": "need input"},
            }
        )
        adapter = _get_adapter(graph=mock_graph)
        handler = adapter.as_handler()

        with caplog.at_level(logging.WARNING, logger="taco.adapters.langgraph"):
            artifact = await handler(sample_task, {})

        assert "interrupt" in caplog.text.lower()
        assert artifact.parts[0].root.text == "partial"

    async def test_dict_result(self, mock_graph, sample_task):
        mock_graph.ainvoke = AsyncMock(return_value={"output": {"estimate": 1000}})
        adapter = _get_adapter(graph=mock_graph)
        handler = adapter.as_handler()
        artifact = await handler(sample_task, {})
        assert artifact.parts[0].root.data == {"estimate": 1000}

    async def test_state_factory_used(self, mock_graph, sample_task):
        def factory(task, data):
            return {"messages": [data], "task_ref": task.id}

        adapter = _get_adapter(graph=mock_graph, state_factory=factory)
        handler = adapter.as_handler()
        await handler(sample_task, {"msg": "hi"})

        call_args = mock_graph.ainvoke.call_args
        assert call_args.args[0] == {
            "messages": [{"msg": "hi"}],
            "task_ref": "task-1",
        }


# ======================================================================
# TestAsStreamingHandler
# ======================================================================


class TestAsStreamingHandler:
    async def test_streams_message_chunks(self, mock_graph, sample_task):
        adapter = _get_adapter(graph=mock_graph)
        handler = adapter.as_streaming_handler()

        parts = []
        async for part in handler(sample_task, {"data": "value"}):
            parts.append(part)

        assert len(parts) == 1
        assert parts[0].root.text == "streamed token"

    async def test_skips_empty_content(self, mock_graph, sample_task):
        async def _astream(*args, **kwargs):
            msg = MagicMock()
            msg.content = ""
            yield (msg, {"langgraph_node": "agent"})
            msg2 = MagicMock()
            msg2.content = "real content"
            yield (msg2, {"langgraph_node": "agent"})

        mock_graph.astream = MagicMock(side_effect=_astream)
        adapter = _get_adapter(graph=mock_graph)
        handler = adapter.as_streaming_handler()

        parts = []
        async for part in handler(sample_task, {}):
            parts.append(part)

        assert len(parts) == 1
        assert parts[0].root.text == "real content"

    async def test_skips_non_message_chunks(self, mock_graph, sample_task):
        async def _astream(*args, **kwargs):
            yield "not a tuple"
            msg = MagicMock()
            msg.content = "good"
            yield (msg, {"langgraph_node": "agent"})

        mock_graph.astream = MagicMock(side_effect=_astream)
        adapter = _get_adapter(graph=mock_graph)
        handler = adapter.as_streaming_handler()

        parts = []
        async for part in handler(sample_task, {}):
            parts.append(part)

        assert len(parts) == 1
        assert parts[0].root.text == "good"

    async def test_skips_chunks_without_node(self, mock_graph, sample_task):
        async def _astream(*args, **kwargs):
            msg = MagicMock()
            msg.content = "skip me"
            yield (msg, {})
            msg2 = MagicMock()
            msg2.content = "keep me"
            yield (msg2, {"langgraph_node": "agent"})

        mock_graph.astream = MagicMock(side_effect=_astream)
        adapter = _get_adapter(graph=mock_graph)
        handler = adapter.as_streaming_handler()

        parts = []
        async for part in handler(sample_task, {}):
            parts.append(part)

        assert len(parts) == 1
        assert parts[0].root.text == "keep me"

    async def test_custom_stream_filter(self, mock_graph, sample_task):
        async def _astream(*args, **kwargs):
            yield {"node": "agent", "data": "chunk1"}
            yield {"node": "tool", "data": "chunk2"}

        mock_graph.astream = MagicMock(side_effect=_astream)

        def my_filter(chunk):
            if chunk.get("node") == "agent":
                return make_text_part(chunk["data"])
            return None

        adapter = _get_adapter(graph=mock_graph, stream_filter=my_filter)
        handler = adapter.as_streaming_handler()

        parts = []
        async for part in handler(sample_task, {}):
            parts.append(part)

        assert len(parts) == 1
        assert parts[0].root.text == "chunk1"
        # Verify stream_mode="updates" was used
        call_kwargs = mock_graph.astream.call_args
        assert call_kwargs.kwargs.get("stream_mode") == "updates"

    async def test_stream_passes_config(self, mock_graph, sample_task):
        adapter = _get_adapter(graph=mock_graph)
        handler = adapter.as_streaming_handler()

        async for _ in handler(sample_task, {}):
            pass

        call_kwargs = mock_graph.astream.call_args
        assert call_kwargs.kwargs["config"]["configurable"]["thread_id"] == "ctx-1"


# ======================================================================
# TestRegisterOn
# ======================================================================


class TestRegisterOn:
    def test_registers_handler_only(self, mock_graph):
        server = MagicMock()
        adapter = _get_adapter(graph=mock_graph)
        adapter.register_on(server, "estimate")

        server.register_handler.assert_called_once()
        assert server.register_handler.call_args.args[0] == "estimate"
        server.register_streaming_handler.assert_not_called()

    def test_registers_both_handlers(self, mock_graph):
        server = MagicMock()
        adapter = _get_adapter(graph=mock_graph)
        adapter.register_on(server, "estimate", streaming=True)

        server.register_handler.assert_called_once()
        assert server.register_handler.call_args.args[0] == "estimate"
        server.register_streaming_handler.assert_called_once()
        assert server.register_streaming_handler.call_args.args[0] == "estimate"


# ======================================================================
# TestCheckLangGraphInstalled
# ======================================================================


class TestCheckLangGraphInstalled:
    def test_constructor_raises_when_langgraph_missing(self):
        """Creating an adapter raises ImportError when langgraph is not installed."""
        from taco.adapters import langgraph as lg_mod

        # Replace the autouse-mocked function with the real implementation
        def _real_check() -> None:
            try:
                import langgraph  # noqa: F401
            except ImportError:
                raise ImportError(
                    "langgraph is required for LangGraphAdapter. "
                    "Install it with: pip install taco-agent[langgraph]"
                ) from None

        with (
            patch.object(lg_mod, "_check_langgraph_installed", _real_check),
            patch.dict("sys.modules", {"langgraph": None}),
            pytest.raises(ImportError, match="taco-agent\\[langgraph\\]"),
        ):
            lg_mod.LangGraphAdapter(graph=MagicMock())
