---
title: "Server"
description: "Run a TACO-compatible A2A server. Register typed handlers per task type, optionally serve the live Monitor UI, and persist tasks."
sidebar_position: 2
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Server

Run a TACO-compatible A2A server. Register typed handlers per task type, optionally serve the live Monitor UI, and persist tasks.

## `A2AServer`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/server.py#L297)

Reusable FastAPI application implementing the A2A protocol.

Wraps the official A2A SDK v1 server primitives (``LegacyRequestHandler``
plus ``create_jsonrpc_routes``) while exposing the v0.3 JSON-RPC wire
format unchanged.

#### Constructor

```python
A2AServer(agent_card: 'AgentCard', *, task_store: 'TaskStore | None' = None, push_config_store: 'PushNotificationConfigStore | None' = None, cors_origins: 'list[str] | None' = None, enable_admin: 'bool' = False, admin_auth_token: 'str | None' = None, enable_monitor: 'bool' = False) -> 'None'
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


