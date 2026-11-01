---
title: "Persistence"
description: "`TaskStore` interface and the bundled `JsonFileTaskStore` for single-process agents that need on-disk task persistence."
sidebar_position: 9
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Persistence

`TaskStore` interface and the bundled `JsonFileTaskStore` for single-process agents that need on-disk task persistence.

## `TaskStore`

*Extends:* `ABC`

Agent Task Store interface.

Defines the methods for persisting and retrieving `Task` objects.

#### Constructor

```python
TaskStore()
```

#### Methods

### `delete()`

```python
async def delete(self, task_id: str, context: a2a.server.context.ServerCallContext) -> None
```

Deletes a task from the store by ID.

### `get()`

```python
async def get(self, task_id: str, context: a2a.server.context.ServerCallContext) -> a2a_pb2.Task | None
```

Retrieves a task from the store by ID.

### `list()`

```python
async def list(self, params: a2a_pb2.ListTasksRequest, context: a2a.server.context.ServerCallContext) -> a2a_pb2.ListTasksResponse
```

Retrieves a list of tasks from the store.

### `save()`

```python
async def save(self, task: a2a_pb2.Task, context: a2a.server.context.ServerCallContext) -> None
```

Saves or updates a task in the store.


## `JsonFileTaskStore`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/task_store.py#L71)

*Extends:* `TaskStore`

Persist A2A tasks to a JSON file.

Args:
    path: Filesystem path for the JSON file. Created on first
        write if it does not already exist.
    owner_resolver: Maps a request's call context to the task owner.
        Defaults to the a2a-sdk's ``resolve_user_scope`` (the
        authenticated user's name).

#### Constructor

```python
JsonFileTaskStore(path: 'str', owner_resolver: 'OwnerResolver' = <function resolve_user_scope>) -> 'None'
```

#### Methods

### `delete()`

```python
async def delete(self, task_id: 'str', context: 'ServerCallContext | None' = None) -> 'None'
```

Delete one of the owner's tasks (no-op if absent), then flush to disk.

### `get()`

```python
async def get(self, task_id: 'str', context: 'ServerCallContext | None' = None) -> 'Task | None'
```

Retrieve one of the owner's tasks by ID, or ``None`` if not found.

### `list()`

```python
async def list(self, params: 'ListTasksRequest | None' = None, context: 'ServerCallContext | None' = None) -> 'ListTasksResponse'
```

List the owner's tasks, applying the ``ListTasks`` filters and paging.

Mirrors the a2a-sdk ``InMemoryTaskStore``: filters by context id,
status and status timestamp, orders newest first, and pages with
``page_size`` / ``page_token``.

### `save()`

```python
async def save(self, task: 'Task | TaskCompat', context: 'ServerCallContext | None' = None) -> 'None'
```

Save or update a task for the request's owner, then flush to disk.

Accepts either the protobuf ``Task`` the v1 SDK passes through
the runtime, or a Pydantic ``Task`` for ergonomic use from
application code; the latter is converted internally.


## See also

- [Build a Custom Agent](/docs/getting-started/build-agent)
- [ADR-0005: In-memory registry first](/docs/decisions/in-memory-registry-first)
- [SDK Guide](/docs/sdk)

