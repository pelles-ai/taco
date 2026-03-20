"""Tests for taco.task_store — JSON-file-backed TaskStore."""

from __future__ import annotations

import json
import os

import pytest

from taco.task_store import JsonFileTaskStore
from taco.types import Task, TaskState, TaskStatus


def _make_task(task_id: str = "task-1", state: TaskState = TaskState.completed) -> Task:
    return Task(
        id=task_id,
        context_id="ctx-1",
        status=TaskStatus(state=state),
    )


@pytest.fixture()
def store_path(tmp_path) -> str:
    return str(tmp_path / "tasks.json")


class TestSaveAndGet:
    async def test_save_and_retrieve(self, store_path: str):
        store = JsonFileTaskStore(store_path)
        task = _make_task("t1")
        await store.save(task)

        result = await store.get("t1")
        assert result is not None
        assert result.id == "t1"
        assert result.status.state == TaskState.completed

    async def test_get_nonexistent_returns_none(self, store_path: str):
        store = JsonFileTaskStore(store_path)
        result = await store.get("does-not-exist")
        assert result is None

    async def test_save_overwrites(self, store_path: str):
        store = JsonFileTaskStore(store_path)
        task1 = _make_task("t1", state=TaskState.working)
        await store.save(task1)

        task2 = _make_task("t1", state=TaskState.completed)
        await store.save(task2)

        result = await store.get("t1")
        assert result is not None
        assert result.status.state == TaskState.completed


class TestDelete:
    async def test_delete_existing(self, store_path: str):
        store = JsonFileTaskStore(store_path)
        await store.save(_make_task("t1"))
        await store.delete("t1")
        assert await store.get("t1") is None

    async def test_delete_nonexistent_is_noop(self, store_path: str):
        store = JsonFileTaskStore(store_path)
        await store.delete("nope")  # should not raise


class TestPersistence:
    async def test_round_trip_across_instances(self, store_path: str):
        store1 = JsonFileTaskStore(store_path)
        await store1.save(_make_task("t1"))
        await store1.save(_make_task("t2"))

        store2 = JsonFileTaskStore(store_path)
        assert (await store2.get("t1")) is not None
        assert (await store2.get("t2")) is not None

    async def test_delete_persists(self, store_path: str):
        store1 = JsonFileTaskStore(store_path)
        await store1.save(_make_task("t1"))
        await store1.delete("t1")

        store2 = JsonFileTaskStore(store_path)
        assert await store2.get("t1") is None

    async def test_file_created_on_first_save(self, store_path: str):
        assert not os.path.exists(store_path)
        store = JsonFileTaskStore(store_path)
        await store.save(_make_task("t1"))
        assert os.path.exists(store_path)


class TestEdgeCases:
    def test_missing_file_loads_empty(self, store_path: str):
        store = JsonFileTaskStore(store_path)
        assert store._tasks == {}

    def test_corrupt_json_loads_empty(self, store_path: str):
        with open(store_path, "w") as f:
            f.write("not valid json {{{")
        store = JsonFileTaskStore(store_path)
        assert store._tasks == {}

    def test_non_dict_json_loads_empty(self, store_path: str):
        with open(store_path, "w") as f:
            json.dump(["a", "list"], f)
        store = JsonFileTaskStore(store_path)
        assert store._tasks == {}

    async def test_multiple_tasks_persist(self, store_path: str):
        store = JsonFileTaskStore(store_path)
        for i in range(5):
            await store.save(_make_task(f"t{i}"))

        store2 = JsonFileTaskStore(store_path)
        for i in range(5):
            assert (await store2.get(f"t{i}")) is not None

    def test_invalid_task_schema_skipped(self, store_path: str):
        """Valid JSON with invalid task data should be skipped, not crash."""
        valid_task = _make_task("t-good").model_dump(by_alias=True, exclude_none=True)
        data = {
            "t-good": valid_task,
            "t-bad": {"not": "a valid task"},
        }
        with open(store_path, "w") as f:
            json.dump(data, f)

        store = JsonFileTaskStore(store_path)
        assert "t-good" in store._tasks
        assert "t-bad" not in store._tasks
