---
title: "Agent (server + client pool)"
description: "`TacoAgent` bundles `A2AServer` with a pool of `TacoClient`s, for agents that both receive and call other agents."
sidebar_position: 5
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Agent (server + client pool)

`TacoAgent` bundles `A2AServer` with a pool of `TacoClient`s, for agents that both receive and call other agents.

## `TacoAgent`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/agent.py#L44)

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
    peer_retry_attempts: How many times to try discovering each peer
        in the background after startup (default 5). A peer still
        missing after that is tried again when a request needs it.
    peer_retry_delay: Seconds between retry attempts (default 2.0).
    peer_startup_wait: Seconds startup waits for the first discovery
        round before the agent starts serving (default 2.0). Discovery
        carries on in the background, so agents that list each other
        as peers find each other once both are up.
    cors_origins: CORS origins for the server. ``None`` (the default)
        disables CORS middleware entirely.
    enable_monitor: Whether to enable the Agent Monitor UI at
        ``/monitor`` on this agent's port.
    monitor_auth_token: Token the monitor's API and WebSocket require
        (open the UI as ``/monitor/#token=<token>``). Set it whenever
        the agent's port is reachable by anyone but you: the monitor
        shows every request and response payload.
    token_verifier: Require a bearer token on inbound task requests
        (see :mod:`taco.auth`); forwarded to :class:`A2AServer`.
        Outbound peer calls take their own credentials through
        ``headers=`` — never forward the caller's token.
    require_task_scope: With ``token_verifier``, require the
        ``taco:task:<taskType>`` scope (default ``True``).
    require_project_scope: With ``token_verifier``, require the token
        to cover the request data's ``projectId``. Defaults to the
        card's ``x-construction.security.projectScoped``.

#### Constructor

```python
TacoAgent(agent_card: 'ConstructionAgentCard', *, task_store: 'TaskStore | None' = None, peers: 'list[str] | str | None' = None, peer_retry_attempts: 'int' = 5, peer_retry_delay: 'float' = 2.0, peer_startup_wait: 'float' = 2.0, cors_origins: 'list[str] | None' = None, enable_monitor: 'bool' = False, monitor_auth_token: 'str | None' = None, token_verifier: 'TokenVerifier | None' = None, require_task_scope: 'bool' = True, require_project_scope: 'bool | None' = None) -> 'None'
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


## See also

- [Multi-Agent Coordination](/docs/getting-started/multi-agent)
- [SDK Guide](/docs/sdk)
- [Cookbook: GC → Estimator → Supplier chain](/docs/cookbook/gc-estimator-supplier-chain)

