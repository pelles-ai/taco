---
title: "Server"
description: "Run a TACO-compatible A2A server. Register typed handlers per task type, fail tasks with caller-facing messages, optionally serve the live Monitor UI, and persist tasks."
sidebar_position: 2
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Server

Run a TACO-compatible A2A server. Register typed handlers per task type, fail tasks with caller-facing messages, optionally serve the live Monitor UI, and persist tasks.

## `A2AServer`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/server.py#L374)

Reusable FastAPI application implementing the A2A protocol.

Wraps the official A2A SDK v1 server primitives (``LegacyRequestHandler``
plus ``create_jsonrpc_routes``) while exposing the v0.3 JSON-RPC wire
format unchanged.

#### Constructor

```python
A2AServer(agent_card: 'AgentCard | ConstructionAgentCard', *, task_store: 'TaskStore | None' = None, push_config_store: 'PushNotificationConfigStore | None' = None, cors_origins: 'list[str] | None' = None, enable_admin: 'bool' = False, admin_auth_token: 'str | None' = None, enable_monitor: 'bool' = False, monitor_auth_token: 'str | None' = None, token_verifier: 'TokenVerifier | None' = None, require_task_scope: 'bool' = True) -> 'None'
```

#### Methods

### `register_handler()`

```python
def register_handler(self, task_type: 'str', handler: 'TaskHandler') -> 'None'
```

Register an async handler for a TACO task type.

Handler signature: async def handler(task: Task, input_data: dict) -> Artifact

### `register_streaming_handler()`

```python
def register_streaming_handler(self, task_type: 'str', handler: 'StreamingTaskHandler') -> 'None'
```

Register an async streaming handler for a TACO task type.

Handler signature: async def handler(task: Task, input_data: dict) -> AsyncIterator[Part]

Marks the agent card as streaming-capable. ``message/stream`` requests
for ``task_type`` use this handler even when a regular handler is also
registered; ``message/send`` requests prefer the regular handler.


## `TacoTaskError`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/errors.py#L6)

Fail the current task with a message the caller is allowed to see.

Raise it from a task handler for expected, caller-facing problems::

    if not input_data.get("lineItems"):
        raise TacoTaskError("bom-v1 input has no lineItems")

The task ends ``failed`` with ``str(exc)`` as its status message. Any
other exception also fails the task, but the caller only gets a generic
message with an error id; the details go to the server log under that
id. That keeps connection strings, file paths and stack details out of
responses to other companies' agents.

#### Constructor

```python
TacoTaskError(*args)
```


## `enable_monitor()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/monitor/__init__.py#L59)

```python
enable_monitor(*, server: 'A2AServer | None' = None, client: 'TacoClient | None' = None, registry: 'AgentRegistry | None' = None, agent_name: 'str | None' = None, max_events: 'int' = 2000, auth_token: 'str | None' = None) -> 'None'
```

Enable the Agent Monitor for the given server/client/registry.

Instruments the provided objects so their A2A traffic appears in the
monitor UI, and mounts the monitor routes onto the server's app at
``/monitor``.

The monitor shows every request and response payload. Set
``auth_token`` before exposing the agent's port beyond your machine;
the UI is then opened as ``/monitor/#token=<token>``.

## See also

- [Build a Custom Agent](/docs/getting-started/build-agent)
- [SDK Guide](/docs/sdk)
- [Cookbook: RFI round-trip](/docs/cookbook/rfi-round-trip)

