---
title: "Registry"
description: "In-memory discovery layer with optional JSON persistence. Find agents by trade, task type, CSI division, or trust tier."
sidebar_position: 5
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Registry

In-memory discovery layer with optional JSON persistence. Find agents by trade, task type, CSI division, or trust tier.

## `AgentRegistry`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/registry.py#L22)

In-memory agent registry with HTTP-based discovery.

Optionally persists registered agents to a JSON file when
``persistence_path`` is provided.

#### Constructor

```python
AgentRegistry(*, timeout: 'float' = 10.0, persistence_path: 'str | None' = None) -> 'None'
```

#### Methods

### `find()`

```python
def find(self, *, trade: 'str | None' = None, task_type: 'str | None' = None, csi_division: 'str | None' = None, project_type: 'str | None' = None) -> 'list[AgentCard]'
```

Find agents matching the given filters (all optional, AND logic).

### `list_agents()`

```python
def list_agents(self) -> 'list[AgentCard]'
```

Return all registered agent cards.

### `refresh()`

```python
async def refresh(self, agent_url: 'str') -> 'AgentCard'
```

Re-fetch and update an agent's card.

### `register()`

```python
async def register(self, agent_url: 'str') -> 'AgentCard'
```

Discover an agent by URL and store its card.

Tries the A2A v0.3+ path ``/.well-known/agent-card.json`` first,
falling back to the legacy ``/.well-known/agent.json`` on 404.
Sends the ``A2A-Version`` header so v1 peers can negotiate.

### `register_card()`

```python
def register_card(self, agent_url: 'str', card: 'AgentCard') -> 'None'
```

Register an agent card directly (useful for testing).

### `remove()`

```python
def remove(self, agent_url: 'str') -> 'bool'
```

Remove an agent by URL. Returns True if it was present.


## See also

- [Multi-Agent Coordination](/docs/getting-started/multi-agent)
- [ADR-0005: In-memory registry first](/docs/decisions/in-memory-registry-first)
- [Cookbook: Schedule-aware procurement](/docs/cookbook/schedule-aware-procurement)

