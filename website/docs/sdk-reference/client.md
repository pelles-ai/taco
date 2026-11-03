---
title: "Client"
description: "Call another TACO agent over A2A. Async HTTP, JSON-RPC and streaming, push notification config management, and the standard `A2A-Version` headers."
sidebar_position: 4
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Client

Call another TACO agent over A2A. Async HTTP, JSON-RPC and streaming, push notification config management, and the standard `A2A-Version` headers.

## `TacoClient`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/client.py#L262)

Async client for sending tasks to a TACO-compatible agent.

``headers`` are sent on every request (for example an
``Authorization`` header for an agent that requires a token);
per-call ``headers`` arguments are merged on top of them.

``protocol`` picks the A2A wire version (ADR-0010):

- ``"0.3"`` (the default) sends ``message/send``, ``tasks/get`` and the
  other v0.3 methods, as every TACO release has.
- ``"1.0"`` sends the v1 methods (``SendMessage``, ``GetTask``, ...) with
  ``A2A-Version: 1.0``.
- ``"auto"`` reads the agent card (fetched once, on the first call, and
  cached) and uses ``"1.0"`` when the card lists an A2A v1 JSON-RPC
  interface at the agent's endpoint, as TACO agents from 0.7 do, and
  ``"0.3"`` otherwise or when the card cannot be read.

Every method returns the same ``taco.types`` models, and
:meth:`stream_message` yields the same event dicts, whichever version is
on the wire. An agent that does not answer the version used raises
:class:`ProtocolVersionError`.

#### Constructor

```python
TacoClient(*, agent_url: 'str', http_client: 'httpx.AsyncClient | None' = None, timeout: 'float' = 120.0, headers: 'dict[str, str] | None' = None, protocol: 'str' = '0.3') -> 'None'
```

#### Methods

### `cancel_task()`

```python
async def cancel_task(self, task_id: 'str', *, headers: 'dict[str, str] | None' = None) -> 'Task'
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
async def get_task(self, task_id: 'str', *, headers: 'dict[str, str] | None' = None) -> 'Task'
```

Retrieve a task by ID.

### `list_push_configs()`

```python
async def list_push_configs(self, task_id: 'str', *, headers: 'dict[str, str] | None' = None) -> 'list[PushNotificationConfig]'
```

Return every push config currently registered for ``task_id``.

### `list_tasks()`

```python
async def list_tasks(self, *, cursor: 'str | None' = None, limit: 'int | None' = None, context_id: 'str | None' = None, include_artifacts: 'bool' = False, headers: 'dict[str, str] | None' = None) -> 'tuple[list[Task], str | None]'
```

List tasks visible to this caller via the v1 ``ListTasks`` RPC.

Returns ``(tasks, next_cursor)``. Pass ``next_cursor`` back as
``cursor`` on a subsequent call to fetch the next page; a
``None`` cursor means there are no more results. ``ListTasks``
leaves artifacts out unless ``include_artifacts`` is ``True``.

``ListTasks`` was added in A2A v1.0, so this method always speaks
v1, whatever ``protocol`` is: v0.3-only peers reject it with
:class:`ProtocolVersionError`.

### `run_task()`

```python
async def run_task(self, *, task_type: 'str', input_data: 'dict[str, Any]', reference_task_ids: 'list[str] | None' = None, return_immediately: 'bool' = False, headers: 'dict[str, str] | None' = None) -> 'dict[str, Any]'
```

Legacy convenience — send a message and return raw result dict.

The dict is in the v0.3 shape in either protocol: a v1 result is
converted, so callers see ``"state": "completed"`` either way.

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
``data`` is the JSON-RPC response for one event, its ``result`` in
the v0.3 shape (``"kind": "status-update"``, ``"state": "working"``)
in either protocol.

### `wire_protocol()`

```python
async def wire_protocol(self) -> 'str'
```

The A2A version this client speaks to the agent: ``"1.0"`` or ``"0.3"``.

With ``protocol="auto"`` the first call reads the agent card (see
:meth:`discover`). An agent without a readable card (an HTTP error
status, or a body that is not a valid card) is spoken to in
``"0.3"``, which every TACO agent answers, and its card is not asked
for again. A connection error propagates, and the card is fetched
again on the next call.


## `TacoClientError`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/client.py#L127)

Base exception for TACO client errors.

#### Constructor

```python
TacoClientError(*args)
```


## `RpcError`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/client.py#L131)

*Extends:* `TacoClientError`

A JSON-RPC error returned by the remote agent.

#### Constructor

```python
RpcError(code: 'int', message: 'str', data: 'Any' = None) -> 'None'
```


## `ProtocolVersionError`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/client.py#L141)

*Extends:* `RpcError`

The agent does not answer the A2A version or method the client used.

Raised for JSON-RPC ``-32601`` (method not found) and ``-32009`` (A2A
v1's version not supported). :attr:`protocol` is the version the client
spoke and :attr:`method` the method it sent. With ``protocol="auto"`` it
means the agent's card lists a version the agent does not serve.

#### Constructor

```python
ProtocolVersionError(code: 'int', message: 'str', data: 'Any' = None, *, protocol: 'str', method: 'str') -> 'None'
```


## `MessageReplyError`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/client.py#L167)

*Extends:* `TacoClientError`

The agent answered with a ``Message`` where a ``Task`` was expected.

TACO agents always return a Task, but other A2A agents may reply to
``message/send`` with a plain Message. The reply is on :attr:`reply`.

#### Constructor

```python
MessageReplyError(reply: 'Message') -> 'None'
```


## See also

- [Multi-Agent Coordination](/docs/getting-started/multi-agent)
- [SDK Guide](/docs/sdk)
- [Cookbook: BOM → Quote marketplace](/docs/cookbook/bom-to-quote-marketplace)

