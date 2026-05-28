---
title: "Client"
description: "Call another TACO agent over A2A. Async HTTP, JSON-RPC and streaming, push notification config management, and the standard `A2A-Version` headers."
sidebar_position: 3
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Client

Call another TACO agent over A2A. Async HTTP, JSON-RPC and streaming, push notification config management, and the standard `A2A-Version` headers.

## `TacoClient`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/client.py#L51)

Async client for sending tasks to a TACO-compatible agent.

#### Constructor

```python
TacoClient(*, agent_url: 'str', http_client: 'httpx.AsyncClient | None' = None, timeout: 'float' = 120.0) -> 'None'
```

#### Methods

### `cancel_task()`

```python
async def cancel_task(self, task_id: 'str') -> 'Task'
```

Cancel a task by ID.

### `close()`

```python
async def close(self) -> 'None'
```

*No docstring.*

### `create_push_config()`

```python
async def create_push_config(self, task_id: 'str', url: 'str', *, token: 'str | None' = None, authentication: 'dict[str, Any] | None' = None, config_id: 'str | None' = None, headers: 'dict[str, str] | None' = None) -> 'PushNotificationConfig'
```

Subscribe a webhook to receive push events for ``task_id``.

A task can carry multiple push configs in A2A v1 — pass distinct
``config_id`` values to register multiple subscribers (e.g. one
for the project owner's dashboard, another for an audit log).

### `delete_push_config()`

```python
async def delete_push_config(self, task_id: 'str', config_id: 'str', *, headers: 'dict[str, str] | None' = None) -> 'None'
```

Unsubscribe a webhook from ``task_id``. No-op if already gone.

### `discover()`

```python
async def discover(self) -> 'AgentCard'
```

Fetch and cache the agent's AgentCard.

Tries the A2A v0.3+ path ``/.well-known/agent-card.json`` first,
falling back to the legacy ``/.well-known/agent.json`` on 404.
Sends the ``A2A-Version`` header so v1 peers can negotiate.

### `get_push_config()`

```python
async def get_push_config(self, task_id: 'str', config_id: 'str', *, headers: 'dict[str, str] | None' = None) -> 'PushNotificationConfig'
```

Fetch a single push config by its id.

### `get_task()`

```python
async def get_task(self, task_id: 'str') -> 'Task'
```

Retrieve a task by ID.

### `list_push_configs()`

```python
async def list_push_configs(self, task_id: 'str', *, headers: 'dict[str, str] | None' = None) -> 'list[PushNotificationConfig]'
```

Return every push config currently registered for ``task_id``.

### `list_tasks()`

```python
async def list_tasks(self, *, cursor: 'str | None' = None, limit: 'int | None' = None, context_id: 'str | None' = None, headers: 'dict[str, str] | None' = None) -> 'tuple[list[Task], str | None]'
```

List tasks visible to this caller via the v1 ``ListTasks`` RPC.

Returns ``(tasks, next_cursor)``. Pass ``next_cursor`` back as
``cursor`` on a subsequent call to fetch the next page; a
``None`` cursor means there are no more results.

``ListTasks`` was added in A2A v1.0, so this method overrides
the default ``A2A-Version: 0.3`` header with ``1.0`` for the
request — v0.3-only peers will reject it.

### `run_task()`

```python
async def run_task(self, *, task_type: 'str', input_data: 'dict[str, Any]', reference_task_ids: 'list[str] | None' = None, return_immediately: 'bool' = False, headers: 'dict[str, str] | None' = None) -> 'dict[str, Any]'
```

Legacy convenience — send a message and return raw result dict.

### `send_message()`

```python
async def send_message(self, task_type: 'str', input_data: 'dict[str, Any]', *, context_id: 'str | None' = None, reference_task_ids: 'list[str] | None' = None, return_immediately: 'bool' = False, headers: 'dict[str, str] | None' = None) -> 'Task'
```

Send a message to the agent and return the resulting Task.

``reference_task_ids`` (A2A v1) links this message to prior
tasks — e.g. an RFI response references the originating RFI
task, a change-order approval references the proposal task.

When ``return_immediately`` is ``True``, the server returns the
Task as soon as it accepts the message (typically in
``submitted`` / ``working`` state) rather than waiting for the
terminal state. Useful for fire-and-forget workflows where the
caller plans to poll via :meth:`get_task` / :meth:`list_tasks`,
or where progress is observed elsewhere (push notifications,
the Monitor UI, an event bus).

### `stream_message()`

```python
def stream_message(self, task_type: 'str', input_data: 'dict[str, Any]', *, context_id: 'str | None' = None, reference_task_ids: 'list[str] | None' = None, headers: 'dict[str, str] | None' = None) -> 'AsyncIterator[dict[str, Any]]'
```

Send a streaming message and yield SSE event dicts.

Each yielded dict has ``event`` (str) and ``data`` (parsed JSON).
``reference_task_ids`` (A2A v1) links this message to prior tasks.


## `TacoClientError`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/client.py#L37)

Base exception for TACO client errors.

#### Constructor

```python
TacoClientError()
```


## `RpcError`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/client.py#L41)

*Extends:* `TacoClientError`

A JSON-RPC error returned by the remote agent.

#### Constructor

```python
RpcError(code: 'int', message: 'str', data: 'Any' = None) -> 'None'
```


## See also

- [Multi-Agent Coordination](/docs/getting-started/multi-agent)
- [SDK Guide](/docs/sdk)
- [Cookbook: BOM → Quote marketplace](/docs/cookbook/bom-to-quote-marketplace)

