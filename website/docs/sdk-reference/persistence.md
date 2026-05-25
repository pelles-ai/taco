---
title: "Persistence"
description: "`TaskStore` interface and the bundled `JsonFileTaskStore` for single-process agents that need on-disk task persistence."
sidebar_position: 8
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


