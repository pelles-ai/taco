---
sidebar_position: 8
title: Examples
description: Standalone examples and a full sandbox demo with LLM-powered construction agents you can run locally.
---

# Examples

The TACO repository includes standalone examples you can run immediately and a full sandbox demo with LLM-powered agents.

## Standalone Examples

No API keys or configuration needed — run these right away:

| Example | What it shows | Guide |
|---|---|---|
| [`quick_start.py`](https://github.com/pelles-ai/taco/blob/main/examples/quick_start.py) | Minimal single-file agent with monitor UI | [Quick Start](/docs/getting-started/quick-start) |
| [`peer_communication.py`](https://github.com/pelles-ai/taco/blob/main/examples/peer_communication.py) | Two agents talking via `TacoAgent` with peer discovery | [Agent-to-Agent Communication](/docs/getting-started/multi-agent) |

```bash
# Minimal agent — runs on http://localhost:8080
pip install taco-agent[all]
python examples/quick_start.py

# Two agents communicating
python examples/peer_communication.py data          # Terminal 1
python examples/peer_communication.py orchestrator  # Terminal 2
```

## Sandbox Demo

Three LLM-powered agents from "different companies" exchange typed construction data over A2A, coordinated by an orchestrator with a web dashboard.

### Agents

| Agent | Port | Trade | Task Type | Schemas |
|---|---|---|---|---|
| **Estimating Agent** | 8001 | multi-trade | `estimate` | `bom-v1` → `estimate-v1` |
| **Supplier Quote Agent** | 8002 | mechanical | `material-procurement` | `bom-v1` → `quote-v1` |
| **RFI Generation Agent** | 8003 | mechanical | `rfi-generation` | `bom-v1` → `rfi-v1` |

Sources:
- [`agents/estimating_agent.py`](https://github.com/pelles-ai/taco/blob/main/examples/agents/estimating_agent.py)
- [`agents/supplier_quote_agent.py`](https://github.com/pelles-ai/taco/blob/main/examples/agents/supplier_quote_agent.py)
- [`agents/rfi_generation_agent.py`](https://github.com/pelles-ai/taco/blob/main/examples/agents/rfi_generation_agent.py)

### Running the demo

```bash
cd examples
cp .env.example .env
# Edit .env with your API key (Anthropic or OpenAI)

# Run locally
python run_demo.py

# Or with Docker Compose
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000) for the orchestrator dashboard:

1. Click **"Discover Agents"** — three agents appear with their trade, CSI divisions, and skills
2. Click **"Send Task"** on any agent skill — the BOM is sent via JSON-RPC, the LLM processes it, and typed results appear
3. Click **"Run Full Pipeline"** — sends the BOM to all three agents in parallel

### Agent Monitors

Every agent includes a live tracing UI at `/monitor`. After starting the demo:

- **Estimating Agent:** [http://localhost:8001/monitor](http://localhost:8001/monitor)
- **Supplier Agent:** [http://localhost:8002/monitor](http://localhost:8002/monitor)
- **RFI Agent:** [http://localhost:8003/monitor](http://localhost:8003/monitor)

The monitor shows incoming requests, handler execution, outgoing peer calls, and discovery events — all streaming in real time via WebSocket.

To enable the monitor in your own agent:

```python
server = A2AServer(card.to_a2a(), enable_monitor=True)
# Monitor UI at http://localhost:<port>/monitor
```

## Building Your Own

Ready to build a custom agent? Follow the getting started guides:

1. [Quick Start](/docs/getting-started/quick-start) — run a minimal agent in under 2 minutes
2. [Build a Custom Agent](/docs/getting-started/build-agent) — define trades, schemas, and handlers
3. [Agent-to-Agent Communication](/docs/getting-started/multi-agent) — connect agents with peer discovery
4. [Integrate Your Platform](/docs/getting-started/integrate-platform) — wrap an existing system as a TACO agent
