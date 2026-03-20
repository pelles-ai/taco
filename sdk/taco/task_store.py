"""JSON-file-backed TaskStore for lightweight task persistence.

Implements the A2A SDK ``TaskStore`` protocol using a single JSON file.
Uses atomic writes (``tempfile.mkstemp`` + ``os.replace``) to avoid
data corruption on crash — the same pattern used by
:class:`taco.registry.AgentRegistry`.

.. note::
   Single-process only.  Not suitable for high-throughput or
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

from .types import Task, TaskStore

logger = logging.getLogger("taco.task_store")


class JsonFileTaskStore(TaskStore):
    """Persist A2A tasks to a JSON file.

    Args:
        path: Filesystem path for the JSON file.  Created on first
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

    async def save(self, task: Task, context=None) -> None:  # type: ignore[override]
        """Save or update a task, then flush to disk."""
        async with self._lock:
            self._tasks[task.id] = task
            self._flush()

    async def get(self, task_id: str, context=None) -> Task | None:  # type: ignore[override]
        """Retrieve a task by ID, or ``None`` if not found."""
        async with self._lock:
            return self._tasks.get(task_id)

    async def delete(self, task_id: str, context=None) -> None:  # type: ignore[override]
        """Delete a task by ID (no-op if absent), then flush to disk."""
        async with self._lock:
            if self._tasks.pop(task_id, None) is not None:
                self._flush()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load tasks from disk.  Gracefully handles missing / corrupt files."""
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
                    self._tasks[task_id] = Task.model_validate(task_data)
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
        data = {
            tid: task.model_dump(by_alias=True, exclude_none=True)
            for tid, task in self._tasks.items()
        }
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
