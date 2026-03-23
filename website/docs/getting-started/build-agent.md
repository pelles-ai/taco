---
sidebar_position: 1
title: Build a Custom Agent
---

# Build a Custom Agent

In the [Quick Start](/docs/getting-started/quick-start) you ran a minimal echo agent. Now let's build something real — a construction agent with a specific trade, typed schemas, and a live monitor.

## What you'll build

A mechanical takeoff agent that:
- Advertises itself as a **mechanical** agent covering **plumbing and HVAC** (CSI divisions 22, 23)
- Accepts `takeoff` tasks with BOM input
- Returns structured `bom-v1` data
- Includes a live tracing UI at `/monitor`

## Prerequisites

```bash
pip install taco-agent[all]
```

## Step 1: Define your Agent Card

Every TACO agent has an **Agent Card** — a machine-readable declaration of who you are, what trade you serve, and what you can do.

```python
from taco import ConstructionAgentCard, ConstructionSkill

card = ConstructionAgentCard(
    name="My Mechanical Takeoff Agent",
    url="http://localhost:8080",
    trade="mechanical",
    csi_divisions=["22", "23"],  # Plumbing & HVAC
    skills=[
        ConstructionSkill(
            id="generate-bom",
            name="Generate Bill of Materials",
            description="Generates a BOM from project drawings",
            task_type="takeoff",
            input_schema="bom-v1",
            output_schema="bom-v1",
        )
    ],
)
```

Key fields:

| Field | Purpose | Example |
|-------|---------|---------|
| `trade` | Your construction trade | `mechanical`, `electrical`, `structural` |
| `csi_divisions` | CSI MasterFormat divisions you cover | `["22", "23"]` (Plumbing, HVAC) |
| `skills` | What your agent can do | Each has a `task_type` and optional input/output schemas |

See [Agent Card Extensions](/docs/agent-card-extensions) for all available fields including `integrations`, `project_types`, and `file_formats`.

## Step 2: Write a handler

The handler is your agent's core logic. It receives a `Task` object and parsed input data, and returns an `Artifact` with the result.

```python
from taco import Artifact, Task, make_artifact, make_data_part


async def handle_takeoff(task: Task, input_data: dict) -> Artifact:
    # Your takeoff logic here — call an LLM, query a database,
    # run a calculation, etc.
    bom_result = {
        "projectId": input_data.get("projectId", "unknown"),
        "trade": "mechanical",
        "lineItems": [
            {"description": "Copper pipe 1/2in", "quantity": 120, "unit": "LF"},
            {"description": "90° elbow 1/2in", "quantity": 24, "unit": "EA"},
        ],
    }

    return make_artifact(
        parts=[make_data_part(bom_result)],
        name="bom",
        description="Generated bill of materials",
    )
```

The server handles task lifecycle automatically — status transitions (`working` → `completed`), error handling, and event streaming.

## Step 3: Create the server and run

```python
import uvicorn
from taco import A2AServer

server = A2AServer(card.to_a2a(), enable_monitor=True)
server.register_handler("takeoff", handle_takeoff)

if __name__ == "__main__":
    uvicorn.run(server.app, host="0.0.0.0", port=8080)
```

`enable_monitor=True` mounts a live tracing UI at `/monitor` — no extra servers or ports needed.

:::tip Persist tasks across restarts
By default, tasks are stored in memory and lost on restart. For durable storage:

```python
from taco import JsonFileTaskStore

server = A2AServer(card.to_a2a(), task_store=JsonFileTaskStore("tasks.json"), enable_monitor=True)
```

See [Task persistence](/docs/sdk#task-persistence) in the SDK Reference.
:::

:::tip Discovery-only mode
If you only need to expose your Agent Card for discovery (no task handlers), use the shorthand:

```python
card.serve(host="0.0.0.0", port=8080)
```
:::

## Step 4: Test it

```bash
python my_agent.py
```

**Check the Agent Card:**

```bash
curl http://localhost:8080/.well-known/agent.json | python -m json.tool
```

You'll see your trade, CSI divisions, and skills in the response.

**Open the monitor:**

Navigate to [http://localhost:8080/monitor](http://localhost:8080/monitor) to see a live dashboard of all A2A traffic.

**Send a task:**

```bash
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "data", "data": {"projectId": "PRJ-001", "trade": "mechanical"}}]
      },
      "metadata": {"taskType": "takeoff"}
    }
  }'
```

Watch the request flow through in the monitor UI in real time.

## Streaming responses

For long-running tasks, you can stream partial results using SSE:

```python
from collections.abc import AsyncIterator
from taco import Part, make_text_part, make_data_part


async def stream_takeoff(task: Task, input_data: dict) -> AsyncIterator[Part]:
    yield make_text_part("Analyzing drawings...")
    # ... do work ...
    yield make_text_part("Identifying materials...")
    # ... do work ...
    yield make_data_part(final_bom_result)


server.register_streaming_handler("takeoff", stream_takeoff)
```

Clients receive updates in real time via `message/stream`.

## Full example

Here's everything in one file:

```python
import uvicorn
from taco import (
    A2AServer,
    Artifact,
    ConstructionAgentCard,
    ConstructionSkill,
    Task,
    make_artifact,
    make_data_part,
)

card = ConstructionAgentCard(
    name="My Mechanical Takeoff Agent",
    url="http://localhost:8080",
    trade="mechanical",
    csi_divisions=["22", "23"],
    skills=[
        ConstructionSkill(
            id="generate-bom",
            name="Generate Bill of Materials",
            description="Generates a BOM from project drawings",
            task_type="takeoff",
            input_schema="bom-v1",
            output_schema="bom-v1",
        )
    ],
)

server = A2AServer(card.to_a2a(), enable_monitor=True)


async def handle_takeoff(task: Task, input_data: dict) -> Artifact:
    bom_result = {
        "projectId": input_data.get("projectId", "unknown"),
        "trade": "mechanical",
        "lineItems": [
            {"description": "Copper pipe 1/2in", "quantity": 120, "unit": "LF"},
            {"description": "90° elbow 1/2in", "quantity": 24, "unit": "EA"},
        ],
    }
    return make_artifact(
        parts=[make_data_part(bom_result)],
        name="bom",
        description="Generated bill of materials",
    )


server.register_handler("takeoff", handle_takeoff)

if __name__ == "__main__":
    print("Agent:   http://localhost:8080/.well-known/agent.json")
    print("Monitor: http://localhost:8080/monitor")
    uvicorn.run(server.app, host="0.0.0.0", port=8080)
```

## Next steps

- [Agent-to-agent communication](/docs/getting-started/multi-agent) — connect multiple agents with peer discovery
- [Integrate your platform](/docs/getting-started/integrate-platform) — wrap an existing system as a TACO agent
- Browse the full list of [Task Types](/docs/task-types) your agent can support
- Learn about [Data Schemas](/docs/schemas/) for typed input and output
