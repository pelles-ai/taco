"""JSON-file-backed TaskStore for lightweight task persistence.

Implements the A2A SDK ``TaskStore`` interface using a single JSON file.
Uses atomic writes (``tempfile.mkstemp`` + ``os.replace``) to avoid
data corruption on crash — the same pattern used by
:class:`taco.registry.AgentRegistry`.

Like the a2a-sdk's ``InMemoryTaskStore``, tasks are kept per owner (the
authenticated caller, see :mod:`taco.auth`), so one caller can never read,
list or delete another caller's tasks, and ``list()`` honours the
``ListTasks`` filters and pagination.

The on-disk format stores each task in the v0.3 Pydantic representation,
grouped by owner::

    {"version": 2, "owners": {"<owner>": {"<task id>": {...task...}}}}

Files written by earlier versions (a flat ``{task id: task}`` object) are
read as belonging to the unauthenticated owner.

.. note::
   Single-process only. Not suitable for high-throughput or
   multi-process deployments — use ``DatabaseTaskStore`` from the
   A2A SDK for those scenarios.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import tempfile
from typing import TYPE_CHECKING, Any

from a2a.compat.v0_3 import conversions
from a2a.compat.v0_3.types import Task as TaskCompat
from a2a.server.owner_resolver import OwnerResolver, resolve_user_scope
from a2a.types.a2a_pb2 import ListTasksRequest, ListTasksResponse, Task
from a2a.utils.constants import DEFAULT_LIST_TASKS_PAGE_SIZE
from a2a.utils.errors import InvalidParamsError
from a2a.utils.task import decode_page_token, encode_page_token

from .types import TaskStore

if TYPE_CHECKING:
    from a2a.server.context import ServerCallContext

logger = logging.getLogger("taco.task_store")

_FORMAT_VERSION = 2


def _owner_of(resolver: OwnerResolver, context: ServerCallContext | None) -> str:
    if context is None:
        # Application code calling the store directly (no request): use the
        # same owner as unauthenticated requests.
        from a2a.server.context import ServerCallContext

        context = ServerCallContext()
    return resolver(context)


def _copy(task: Task) -> Task:
    copied = Task()
    copied.CopyFrom(task)
    return copied


class JsonFileTaskStore(TaskStore):
    """Persist A2A tasks to a JSON file.

    Args:
        path: Filesystem path for the JSON file. Created on first
            write if it does not already exist.
        owner_resolver: Maps a request's call context to the task owner.
            Defaults to the a2a-sdk's ``resolve_user_scope`` (the
            authenticated user's name).
    """

    def __init__(self, path: str, owner_resolver: OwnerResolver = resolve_user_scope) -> None:
        self._path = path
        self._owner_resolver = owner_resolver
        self._tasks: dict[str, dict[str, Task]] = {}
        self._lock = asyncio.Lock()
        self._load()

    # ------------------------------------------------------------------
    # TaskStore interface
    # ------------------------------------------------------------------

    async def save(  # type: ignore[override]
        self,
        task: Task | TaskCompat,
        context: ServerCallContext | None = None,
    ) -> None:
        """Save or update a task for the request's owner, then flush to disk.

        Accepts either the protobuf ``Task`` the v1 SDK passes through
        the runtime, or a Pydantic ``Task`` for ergonomic use from
        application code; the latter is converted internally.
        """
        pb_task = _copy(task) if isinstance(task, Task) else conversions.to_core_task(task)
        owner = _owner_of(self._owner_resolver, context)
        async with self._lock:
            self._tasks.setdefault(owner, {})[pb_task.id] = pb_task
            await self._flush()

    async def get(  # type: ignore[override]
        self,
        task_id: str,
        context: ServerCallContext | None = None,
    ) -> Task | None:
        """Retrieve one of the owner's tasks by ID, or ``None`` if not found."""
        owner = _owner_of(self._owner_resolver, context)
        async with self._lock:
            task = self._tasks.get(owner, {}).get(task_id)
            return _copy(task) if task is not None else None

    async def delete(  # type: ignore[override]
        self,
        task_id: str,
        context: ServerCallContext | None = None,
    ) -> None:
        """Delete one of the owner's tasks (no-op if absent), then flush to disk."""
        owner = _owner_of(self._owner_resolver, context)
        async with self._lock:
            owner_tasks = self._tasks.get(owner, {})
            if owner_tasks.pop(task_id, None) is not None:
                if not owner_tasks:
                    self._tasks.pop(owner, None)
                await self._flush()

    async def list(  # type: ignore[override]
        self,
        params: ListTasksRequest | None = None,
        context: ServerCallContext | None = None,
    ) -> ListTasksResponse:
        """List the owner's tasks, applying the ``ListTasks`` filters and paging.

        Mirrors the a2a-sdk ``InMemoryTaskStore``: filters by context id,
        status and status timestamp, orders newest first, and pages with
        ``page_size`` / ``page_token``.
        """
        params = params if params is not None else ListTasksRequest()
        owner = _owner_of(self._owner_resolver, context)
        async with self._lock:
            tasks = [_copy(t) for t in self._tasks.get(owner, {}).values()]

        if params.context_id:
            tasks = [t for t in tasks if t.context_id == params.context_id]
        if params.status:
            tasks = [t for t in tasks if t.status.state == params.status]
        if params.HasField("status_timestamp_after"):
            after = params.status_timestamp_after.ToJsonString()
            tasks = [
                t
                for t in tasks
                if t.HasField("status")
                and t.status.HasField("timestamp")
                and t.status.timestamp.ToJsonString() >= after
            ]

        def sort_key(t: Task) -> tuple[bool, str, str]:
            has_ts = t.HasField("status") and t.status.HasField("timestamp")
            return (has_ts, t.status.timestamp.ToJsonString() if has_ts else "", t.id)

        tasks.sort(key=sort_key, reverse=True)

        total_size = len(tasks)
        start = 0
        if params.page_token:
            start_id = decode_page_token(params.page_token)
            for i, t in enumerate(tasks):
                if t.id == start_id:
                    start = i
                    break
            else:
                raise InvalidParamsError(f"Invalid page token: {params.page_token}")
        page_size = params.page_size or DEFAULT_LIST_TASKS_PAGE_SIZE
        end = start + page_size
        next_token = encode_page_token(tasks[end].id) if end < total_size else None
        return ListTasksResponse(
            tasks=tasks[start:end],
            next_page_token=next_token,
            total_size=total_size,
            page_size=page_size,
        )

    # ------------------------------------------------------------------
    # Internal helpers — bridge protobuf runtime to Pydantic on disk
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load tasks from disk. Gracefully handles missing / corrupt files."""
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path) as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Failed to load task store from %s: %s — starting empty",
                self._path,
                exc,
            )
            return
        if not isinstance(raw, dict):
            logger.warning("Task store at %s is not a JSON object — starting empty", self._path)
            return

        if raw.get("version") == _FORMAT_VERSION and isinstance(raw.get("owners"), dict):
            by_owner: dict[str, Any] = raw["owners"]
        else:
            # Version 1: a flat {task id: task} map with no owners.
            by_owner = {_owner_of(self._owner_resolver, None): raw}

        for owner, tasks in by_owner.items():
            if not isinstance(tasks, dict):
                continue
            for task_id, task_data in tasks.items():
                try:
                    compat = TaskCompat.model_validate(task_data)
                    self._tasks.setdefault(owner, {})[task_id] = conversions.to_core_task(compat)
                except Exception as exc:
                    logger.warning(
                        "Skipping corrupt task entry %s in %s: %s",
                        task_id,
                        self._path,
                        exc,
                    )

    async def _flush(self) -> None:
        """Serialise every task and write the file without blocking the event loop."""
        owners: dict[str, dict[str, Any]] = {}
        for owner, tasks in self._tasks.items():
            for tid, task in tasks.items():
                try:
                    compat = conversions.to_compat_task(task)
                    owners.setdefault(owner, {})[tid] = compat.model_dump(
                        mode="json", by_alias=True, exclude_none=True
                    )
                except Exception as exc:
                    logger.warning("Skipping un-serialisable task %s: %s", tid, exc)
        data = {"version": _FORMAT_VERSION, "owners": owners}
        await asyncio.to_thread(self._write, data)

    def _write(self, data: dict[str, Any]) -> None:
        """Atomically replace the JSON file."""
        dir_path = os.path.dirname(self._path) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self._path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise
