---
sidebar_position: 0
title: Quick Start
description: Run a TACO agent in under two minutes with `pip install "taco-agent[all]"`. No API keys, no configuration.
---

# Quick Start

Get a TACO agent running in under 2 minutes. No API keys, no configuration.

:::tip Nothing installed yet?
The [playground](/playground) runs the same SDK in your browser: define an agent card, serve it and send it a task, with nothing to install.
:::

## Prerequisites

- Python 3.10+
- pip

## Install

```bash
pip install "taco-agent[all]"
```

The quotes stop shells such as zsh from treating the brackets as a pattern. The `all` extra brings the server, the client and `uvicorn`.

## Run your first agent

Create a file called `my_agent.py`:

```python
from taco import (
    A2AServer,
    Artifact,
    ConstructionAgentCard,
    ConstructionSkill,
    Task,
    make_artifact,
    make_data_part,
)

# Define your agent
card = ConstructionAgentCard(
    name="My First TACO Agent",
    description="A minimal agent that echoes back input data.",
    url="http://localhost:8080",
    trade="multi-trade",
    csi_divisions=[],
    skills=[
        ConstructionSkill(
            id="echo",
            task_type="echo",
            output_schema="echo-v1",
        ),
    ],
)

# Create the server, with a live tracing UI at /monitor
server = A2AServer(card.to_a2a(), enable_monitor=True)


# Handle incoming tasks
async def handle_echo(task: Task, input_data: dict) -> Artifact:
    return make_artifact(
        parts=[make_data_part({"received": input_data, "message": "Hello from TACO!"})],
        name="echo-result",
    )


server.register_handler("echo", handle_echo)

if __name__ == "__main__":
    import uvicorn

    # 127.0.0.1: only this machine can reach the agent and its monitor.
    uvicorn.run(server.app, host="127.0.0.1", port=8080)
```

Start it:

```bash
python my_agent.py
```

## Verify it works

Your agent exposes these endpoints out of the box:

**Agent Card** — the machine-readable description of your agent's capabilities:

```bash
curl http://localhost:8080/.well-known/agent-card.json | python -m json.tool
```

The server also answers on the legacy path `/.well-known/agent.json`, for older A2A clients.

**Monitor UI** — a live tracing dashboard that shows all A2A traffic:

Open [http://localhost:8080/monitor](http://localhost:8080/monitor) in your browser.

:::warning The monitor shows every payload
Anyone who can reach the port can read every request and response in the monitor. That is fine on `127.0.0.1`. Before you bind to `0.0.0.0`, run in a container or deploy, give the monitor a token and open it as `/monitor/#token=<token>`:

```python
import os

server = A2AServer(
    card.to_a2a(),
    enable_monitor=True,
    monitor_auth_token=os.environ["TACO_MONITOR_TOKEN"],
)
```

Or leave `enable_monitor` off outside development.
:::

**Send a task** via JSON-RPC:

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
        "messageId": "msg-1",
        "parts": [{"kind": "data", "data": {"hello": "world"}}]
      },
      "metadata": {"taskType": "echo"}
    }
  }'
```

Every A2A message needs a `messageId`; without one the agent answers with JSON-RPC error `-32600` (Invalid Request). Use a fresh id for each message you send.

You should see a task in the `completed` state whose artifact holds your echoed data and a `"Hello from TACO!"` message. The monitor UI will show the request in real time.

:::tip Or use the CLI
`taco send http://localhost:8080 echo` builds the JSON-RPC request for you, and `echo '{"hello": "world"}' | taco send http://localhost:8080 echo` sends input data. See the [CLI Reference](/docs/cli).
:::

## What just happened?

In ~30 lines of code, you created a fully A2A-compatible agent that:

1. **Advertises its capabilities** via a standard Agent Card at `/.well-known/agent-card.json`
2. **Accepts tasks** over JSON-RPC (`message/send`, `message/stream`)
3. **Returns typed artifacts** with structured data
4. **Traces all traffic** through a live monitor UI

Any other TACO or A2A agent can discover and communicate with your agent using this standard interface.

## Next steps

- [Build a custom agent](/docs/getting-started/build-agent) — define your own task types, schemas, and handlers
- [Agent-to-agent communication](/docs/getting-started/multi-agent) — connect multiple agents with peer discovery
- [Integrate your platform](/docs/getting-started/integrate-platform) — wrap an existing system as a TACO agent
