"""JSON-file-backed TaskStore for lightweight task persistence.

Implements the A2A SDK ``TaskStore`` interface using a single JSON file.
Uses atomic writes (``tempfile.mkstemp`` + ``os.replace``) to avoid
data corruption on crash — the same pattern used by
:class:`taco.registry.AgentRegistry`.

The on-disk format is the v0.3 Pydantic representation of a Task, so the
file stays human-readable and is forward-compatible: at runtime we accept
and return the v1 protobuf ``Task`` shape that the SDK passes through.

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
from typing import TYPE_CHECKING

from a2a.compat.v0_3 import conversions
from a2a.compat.v0_3.types import Task as TaskCompat
from a2a.types.a2a_pb2 import ListTasksRequest, ListTasksResponse, Task

from .types import TaskStore

if TYPE_CHECKING:
    from a2a.server.context import ServerCallContext

logger = logging.getLogger("taco.task_store")


class JsonFileTaskStore(TaskStore):
    """Persist A2A tasks to a JSON file.

    Args:
        path: Filesystem path for the JSON file. Created on first
            write if it does not already exist.
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._tasks: dict[str, Task] = {}
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
        """Save or update a task, then flush to disk.

        Accepts either the protobuf ``Task`` the v1 SDK passes through
        the runtime, or a Pydantic ``Task`` for ergonomic use from
        application code; the latter is converted internally.
        """
        pb_task = task if isinstance(task, Task) else conversions.to_core_task(task)
        async with self._lock:
            self._tasks[pb_task.id] = pb_task
            self._flush()

    async def get(  # type: ignore[override]
        self,
        task_id: str,
        context: ServerCallContext | None = None,
    ) -> Task | None:
        """Retrieve a task by ID, or ``None`` if not found."""
        async with self._lock:
            return self._tasks.get(task_id)

    async def delete(  # type: ignore[override]
        self,
        task_id: str,
        context: ServerCallContext | None = None,
    ) -> None:
        """Delete a task by ID (no-op if absent), then flush to disk."""
        async with self._lock:
            if self._tasks.pop(task_id, None) is not None:
                self._flush()

    async def list(  # type: ignore[override]
        self,
        params: ListTasksRequest | None = None,
        context: ServerCallContext | None = None,
    ) -> ListTasksResponse:
        """Return all stored tasks. Pagination/filtering is not implemented."""
        async with self._lock:
            return ListTasksResponse(tasks=list(self._tasks.values()))

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
            if not isinstance(raw, dict):
                logger.warning(
                    "Task store at %s is not a JSON object — starting empty",
                    self._path,
                )
                return
            for task_id, task_data in raw.items():
                try:
                    compat = TaskCompat.model_validate(task_data)
                    self._tasks[task_id] = conversions.to_core_task(compat)
                except Exception as exc:
                    logger.warning(
                        "Skipping corrupt task entry %s in %s: %s",
                        task_id,
                        self._path,
                        exc,
                    )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Failed to load task store from %s: %s — starting empty",
                self._path,
                exc,
            )
            self._tasks = {}

    def _flush(self) -> None:
        """Atomically write current tasks to the JSON file."""
        data = {}
        for tid, task in self._tasks.items():
            try:
                compat = conversions.to_compat_task(task)
                data[tid] = compat.model_dump(by_alias=True, exclude_none=True)
            except Exception as exc:
                logger.warning("Skipping un-serialisable task %s: %s", tid, exc)
        dir_path = os.path.dirname(self._path) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self._path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise
