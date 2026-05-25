---
title: "Agent (server + client pool)"
description: "`TacoAgent` bundles `A2AServer` with a pool of `TacoClient`s, for agents that both receive and call other agents."
sidebar_position: 4
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Agent (server + client pool)

`TacoAgent` bundles `A2AServer` with a pool of `TacoClient`s, for agents that both receive and call other agents.

## `TacoAgent`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/agent.py#L42)

A TACO agent that can both receive and send A2A requests.

Composes :class:`A2AServer` (inbound), :class:`AgentRegistry` (peer
discovery), and a :class:`TacoClient` pool (outbound calls) into a
single object.

Args:
    agent_card: The construction agent card describing this agent.
    peers: Peer agent URLs for discovery. Accepts either:
        - A file path (str) to a YAML/JSON config with
          ``agents: [{url: "http://..."}]`` format
        - A list of URL strings
        - ``None`` to disable peer communication
    task_store: Optional :class:`TaskStore` for task persistence.
        Defaults to ``InMemoryTaskStore`` (state lost on restart).
        Pass a :class:`JsonFileTaskStore` or ``DatabaseTaskStore``
        for durable storage.
    peer_retry_attempts: How many times to retry discovering each peer
        at startup (default 5).
    peer_retry_delay: Seconds between retry attempts (default 2.0).
    cors_origins: CORS origins for the server. ``None`` (the default)
        disables CORS middleware entirely.
    enable_monitor: Whether to enable the Agent Monitor UI at
        ``/monitor`` on this agent's port.

#### Constructor

```python
TacoAgent(agent_card: 'ConstructionAgentCard', *, task_store: 'TaskStore | None' = None, peers: 'list[str] | str | None' = None, peer_retry_attempts: 'int' = 5, peer_retry_delay: 'float' = 2.0, cors_origins: 'list[str] | None' = None, enable_monitor: 'bool' = False) -> 'None'
```

#### Methods

### `register_handler()`

```python
def register_handler(self, task_type: 'str', handler: 'TaskHandler') -> 'None'
```

Register an async handler for a TACO task type.

Delegates to :meth:`A2AServer.register_handler`.

### `register_streaming_handler()`

```python
def register_streaming_handler(self, task_type: 'str', handler: 'StreamingTaskHandler') -> 'None'
```

Register a streaming handler for a TACO task type.

Delegates to :meth:`A2AServer.register_streaming_handler`.

### `send_to_peer()`

```python
async def send_to_peer(self, task_type: 'str', input_data: 'dict[str, Any]', *, context_id: 'str | None' = None, reference_task_ids: 'list[str] | None' = None, return_immediately: 'bool' = False, headers: 'dict[str, str] | None' = None) -> 'Task'
```

Send a message to whichever peer agent handles *task_type*.

Looks up the peer by skill ID/tag match, gets or creates a pooled
:class:`TacoClient`, and calls ``send_message()``. When
``return_immediately`` is ``True``, the peer returns the Task as
soon as it accepts the message rather than waiting for the
terminal state — useful for long-running estimates and
schedules where the caller plans to poll or watch via the
Monitor UI.

``reference_task_ids`` (A2A v1) links this outbound call to prior
tasks — natural fit for RFI → response or proposal → approval
construction workflows.

Returns:
    The resulting :class:`Task` with artifacts (or just the
    accepted task object when ``return_immediately`` is True).

Raises:
    ValueError: No peers configured or no peer has the skill.

### `stream_from_peer()`

```python
def stream_from_peer(self, task_type: 'str', input_data: 'dict[str, Any]', *, context_id: 'str | None' = None, reference_task_ids: 'list[str] | None' = None, headers: 'dict[str, str] | None' = None) -> 'AsyncIterator[dict[str, Any]]'
```

Stream a message from whichever peer agent handles *task_type*.

Same lookup logic as :meth:`send_to_peer` but returns an SSE
event iterator. ``reference_task_ids`` is forwarded onto the
outbound stream request.

Raises:
    ValueError: No peers configured or no peer has the skill.


