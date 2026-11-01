"""Tests for taco.task_store — JSON-file-backed TaskStore."""

from __future__ import annotations

import json
import os

import pytest
from a2a.compat.v0_3 import conversions

from taco.task_store import JsonFileTaskStore
from taco.types import Task, TaskState, TaskStatus


def _make_task(task_id: str = "task-1", state: TaskState = TaskState.completed) -> Task:
    return Task(
        id=task_id,
        context_id="ctx-1",
        status=TaskStatus(state=state),
    )


def _as_compat(pb_task) -> Task | None:
    """Convert a protobuf task back to v0_3 Pydantic for inspection."""
    return conversions.to_compat_task(pb_task) if pb_task is not None else None


@pytest.fixture()
def store_path(tmp_path) -> str:
    return str(tmp_path / "tasks.json")


class TestSaveAndGet:
    async def test_save_and_retrieve(self, store_path: str):
        store = JsonFileTaskStore(store_path)
        task = _make_task("t1")
        await store.save(task)

        result = _as_compat(await store.get("t1"))
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

        result = _as_compat(await store.get("t1"))
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

    async def test_invalid_task_schema_skipped(self, store_path: str):
        """Valid JSON with invalid task data should be skipped, not crash."""
        valid_task = _make_task("t-good").model_dump(by_alias=True, exclude_none=True)
        data = {
            "t-good": valid_task,
            "t-bad": {"not": "a valid task"},
        }
        with open(store_path, "w") as f:
            json.dump(data, f)

        store = JsonFileTaskStore(store_path)
        assert await store.get("t-good") is not None
        assert await store.get("t-bad") is None


def _ctx(user: str | None):
    """A call context for an authenticated user (or anonymous when None)."""
    from a2a.server.context import ServerCallContext
    from a2a.server.routes.common import StarletteUser
    from starlette.authentication import SimpleUser

    if user is None:
        return ServerCallContext()
    return ServerCallContext(user=StarletteUser(SimpleUser(user)))


class TestOwnerScoping:
    async def test_owners_cannot_see_each_others_tasks(self, store_path: str):
        store = JsonFileTaskStore(store_path)
        await store.save(_make_task("alice-task"), _ctx("alice"))
        await store.save(_make_task("bob-task"), _ctx("bob"))

        assert await store.get("alice-task", _ctx("alice")) is not None
        assert await store.get("alice-task", _ctx("bob")) is None
        assert await store.get("alice-task", _ctx(None)) is None
        listed = await store.list(None, _ctx("bob"))
        assert [t.id for t in listed.tasks] == ["bob-task"]

        await store.delete("alice-task", _ctx("bob"))  # not bob's: no-op
        assert await store.get("alice-task", _ctx("alice")) is not None

    async def test_owners_survive_a_reload(self, store_path: str):
        store = JsonFileTaskStore(store_path)
        await store.save(_make_task("alice-task"), _ctx("alice"))

        reloaded = JsonFileTaskStore(store_path)
        assert await reloaded.get("alice-task", _ctx("alice")) is not None
        assert await reloaded.get("alice-task", _ctx("bob")) is None

        with open(store_path) as f:
            on_disk = json.load(f)
        assert on_disk["version"] == 2
        assert "alice-task" in on_disk["owners"]["alice"]

    async def test_legacy_flat_file_belongs_to_anonymous_owner(self, store_path: str):
        legacy = {"old-task": _make_task("old-task").model_dump(by_alias=True, exclude_none=True)}
        with open(store_path, "w") as f:
            json.dump(legacy, f)

        store = JsonFileTaskStore(store_path)
        assert await store.get("old-task") is not None
        assert await store.get("old-task", _ctx(None)) is not None
        assert await store.get("old-task", _ctx("alice")) is None


class TestListFiltersAndPaging:
    async def test_context_filter(self, store_path: str):
        from a2a.types.a2a_pb2 import ListTasksRequest

        store = JsonFileTaskStore(store_path)
        for tid, ctx in (("a1", "ctx-a"), ("a2", "ctx-a"), ("b1", "ctx-b")):
            await store.save(
                Task(id=tid, context_id=ctx, status=TaskStatus(state=TaskState.completed))
            )

        result = await store.list(ListTasksRequest(context_id="ctx-b"))
        assert [t.id for t in result.tasks] == ["b1"]
        assert result.total_size == 1

    async def test_status_filter(self, store_path: str):
        from a2a.types.a2a_pb2 import ListTasksRequest
        from a2a.types.a2a_pb2 import TaskState as PbTaskState

        store = JsonFileTaskStore(store_path)
        await store.save(_make_task("done", TaskState.completed))
        await store.save(_make_task("busy", TaskState.working))

        result = await store.list(ListTasksRequest(status=PbTaskState.TASK_STATE_WORKING))
        assert [t.id for t in result.tasks] == ["busy"]

    async def test_pagination(self, store_path: str):
        from a2a.types.a2a_pb2 import ListTasksRequest
        from a2a.utils.errors import InvalidParamsError

        store = JsonFileTaskStore(store_path)
        for i in range(5):
            await store.save(_make_task(f"t{i}"))

        seen: list[str] = []
        token = ""
        while True:
            page = await store.list(ListTasksRequest(page_size=2, page_token=token))
            assert len(page.tasks) <= 2
            seen.extend(t.id for t in page.tasks)
            if not page.next_page_token:
                break
            token = page.next_page_token
        assert sorted(seen) == [f"t{i}" for i in range(5)]
        assert len(seen) == 5

        with pytest.raises(InvalidParamsError):
            await store.list(ListTasksRequest(page_token="bm90LWEtdGFzaw"))

    async def test_returned_tasks_are_copies(self, store_path: str):
        store = JsonFileTaskStore(store_path)
        await store.save(_make_task("t1"))
        fetched = await store.get("t1")
        fetched.context_id = "mutated"
        again = await store.get("t1")
        assert again.context_id == "ctx-1"
