---
sidebar_position: 2
title: Agent-to-Agent Communication
---

# Agent-to-Agent Communication

So far you've built a single agent that accepts tasks from external clients. In real construction workflows, agents need to talk to each other — an orchestrator calls a data agent, an estimating agent fetches supplier quotes, a scheduler checks RFI status.

This guide shows you how to connect agents using `TacoAgent`, which handles peer discovery, client pooling, and inter-agent messaging automatically.

## What you'll build

Two agents that communicate over A2A:

```
┌──────────────────┐         ┌──────────────────┐
│  Orchestrator    │  A2A    │  Data Agent      │
│  :9000           │────────▶│  :9001           │
│                  │         │                  │
│  Asks questions  │         │  Returns answers │
└──────────────────┘         └──────────────────┘
```

The orchestrator receives a question from a user, forwards it to the data agent via A2A, and returns a combined result.

## Prerequisites

```bash
pip install taco-agent[all]
```

## Step 1: Build the data agent

The data agent is a standard `A2AServer` — same pattern as [Build a Custom Agent](/docs/getting-started/build-agent):

```python
# data_agent.py
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
    name="Data Agent",
    description="Provides sample construction data.",
    url="http://localhost:9001",
    trade="electrical",
    csi_divisions=["26"],
    skills=[
        ConstructionSkill(
            id="data-query",
            task_type="data-query",
            output_schema="query-result-v1",
        ),
    ],
)

server = A2AServer(card.to_a2a(), enable_monitor=True)
# Optional: server = A2AServer(card.to_a2a(), task_store=JsonFileTaskStore("tasks.json"), enable_monitor=True)


async def handle_query(task: Task, input_data: dict) -> Artifact:
    question = input_data.get("question", "")
    # In a real agent, this would query a database or call an LLM
    return make_artifact(
        parts=[make_data_part({
            "question": question,
            "answer": f"You asked: '{question}'. Here are 42 items.",
            "count": 42,
        })],
        name="query-result",
    )


server.register_handler("data-query", handle_query)

if __name__ == "__main__":
    print("Data Agent:  http://localhost:9001")
    print("Monitor:     http://localhost:9001/monitor")
    uvicorn.run(server.app, host="0.0.0.0", port=9001)
```

## Step 2: Build the orchestrator with `TacoAgent`

Here's where it gets interesting. Instead of `A2AServer`, use `TacoAgent` — it combines a server (inbound), a client pool (outbound), and a registry (peer discovery) into a single object.

```python
# orchestrator.py
import uvicorn
from taco import (
    Artifact,
    ConstructionAgentCard,
    ConstructionSkill,
    TacoAgent,
    Task,
    make_artifact,
    make_data_part,
    extract_structured_data,
)

card = ConstructionAgentCard(
    name="Orchestrator Agent",
    description="Plans queries and calls data agents.",
    url="http://localhost:9000",
    trade="multi-trade",
    csi_divisions=[],
    skills=[
        ConstructionSkill(
            id="analyze",
            task_type="analyze",
            output_schema="analysis-v1",
        ),
    ],
)

# TacoAgent discovers peers at startup
agent = TacoAgent(
    card,
    peers=["http://localhost:9001"],
    enable_monitor=True,
    # task_store=JsonFileTaskStore("orchestrator-tasks.json"),  # optional persistence
)


async def handle_analyze(task: Task, input_data: dict) -> Artifact:
    question = input_data.get("question", "No question provided")

    # Call the data agent via A2A — TacoAgent handles connection pooling
    peer_task = await agent.send_to_peer(
        "data-query",
        {"question": question},
    )

    # Extract structured data from the response
    peer_data = extract_structured_data(peer_task.artifacts[0].parts[0])

    return make_artifact(
        parts=[make_data_part({
            "answer": f"Analysis complete. Data agent said: {peer_data.get('answer')}",
            "data_source": peer_data,
        })],
        name="analysis-result",
    )


agent.register_handler("analyze", handle_analyze)

if __name__ == "__main__":
    print("Orchestrator: http://localhost:9000")
    print("Monitor:      http://localhost:9000/monitor")
    uvicorn.run(agent.app, host="0.0.0.0", port=9000)
```

### Key differences from `A2AServer`

| | `A2AServer` | `TacoAgent` |
|---|---|---|
| **Role** | Receives tasks only | Receives and sends tasks |
| **Peers** | None | Auto-discovers peers at startup |
| **Client pool** | Manual | Built-in, with connection reuse |
| **Calling other agents** | Use `TacoClient` directly | `agent.send_to_peer(task_type, data)` |

## Step 3: Run both agents

In **Terminal 1** — start the data agent:

```bash
python data_agent.py
```

In **Terminal 2** — start the orchestrator:

```bash
python orchestrator.py
```

The orchestrator will automatically discover the data agent's capabilities at startup.

## Step 4: Test the flow

Send a question to the orchestrator:

```bash
curl -X POST http://localhost:9000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "data", "data": {"question": "How many items?"}}]
      },
      "metadata": {"taskType": "analyze"}
    }
  }'
```

The orchestrator forwards the question to the data agent and returns a combined result.

## Step 5: Trace the communication

Open both monitor UIs to see the full request flow:

- **Orchestrator:** [http://localhost:9000/monitor](http://localhost:9000/monitor) — shows the incoming request and the outgoing call to the data agent
- **Data Agent:** [http://localhost:9001/monitor](http://localhost:9001/monitor) — shows the request received from the orchestrator

Events are tagged with labels like `RECEIVED`, `CALLING`, `GOT REPLY`, and `COMPLETED` for clear traceability across agents.

## Peer discovery options

`TacoAgent` accepts peers in several formats:

```python
# List of URLs
agent = TacoAgent(card, peers=["http://agent1:8001", "http://agent2:8002"])

# YAML config file
agent = TacoAgent(card, peers="agents.yaml")
```

**agents.yaml:**

```yaml
agents:
  - url: http://localhost:8001
  - url: http://localhost:8002
```

At startup, `TacoAgent` fetches each peer's Agent Card, registers it in its internal registry, and routes `send_to_peer()` calls to the right agent based on task type.

## Forwarding HTTP headers

When proxying requests between agents, you may need to forward authentication headers:

```python
peer_task = await agent.send_to_peer(
    "data-query",
    {"question": question},
    headers={"Authorization": f"Bearer {token}"},
)
```

The `headers` parameter passes custom HTTP headers to the downstream agent, which is useful for token-based authentication chains.

## Next steps

- [Integrate your platform](/docs/getting-started/integrate-platform) — wrap an existing system as a TACO agent
- [SDK Reference](/docs/sdk) — full API reference for `TacoAgent`, `TacoClient`, and `AgentRegistry`
- [Security](/docs/security) — authentication, trust tiers, and scope taxonomy
- [Examples](/docs/examples) — sandbox demo with 3 LLM-powered agents and an orchestrator dashboard
