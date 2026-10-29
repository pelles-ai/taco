# TACO Examples

## Standalone Examples

Quick-start examples you can run immediately with zero configuration (no LLM key needed):

| Example | What it shows |
|---|---|
| [`quick_start.py`](quick_start.py) | Minimal single-file agent with the monitor UI |
| [`peer_communication.py`](peer_communication.py) | Two agents talking to each other via `TacoAgent` with peer discovery |

```bash
# Install the TACO SDK from this checkout (run from examples/)
pip install -e "../sdk[all]"
# ...or the published package: pip install "taco-agent[all]"

# Minimal agent
python quick_start.py
# Open http://localhost:8080/.well-known/agent-card.json and http://localhost:8080/monitor

# Two agents communicating
python peer_communication.py data          # Terminal 1
python peer_communication.py orchestrator  # Terminal 2
# Open http://localhost:9000/monitor to see inter-agent traffic
```

Each file's docstring has a `curl` command that sends it a task.

---

## Sandbox Demo

A working demonstration of the Construction A2A Interoperability Protocol. Three LLM-powered agents from "different companies" exchange typed construction data over A2A, coordinated by an orchestrator with a web dashboard.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  GC Orchestrator + Dashboard  (http://localhost:8000)        │
│  Discovers agents, sends tasks, shows typed results          │
└───────┬──────────────────┬──────────────────┬────────────────┘
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ ACME          │  │ BuildSupply   │  │ PlanCheck     │
│ Estimating    │  │ Quote Agent   │  │ RFI Agent     │
│ Agent         │  │               │  │               │
│ :8001         │  │ :8002         │  │ :8003         │
│               │  │               │  │               │
│ bom-v1 →      │  │ bom-v1 →      │  │ bom-v1 →      │
│ estimate-v1   │  │ quote-v1      │  │ rfi-v1        │
│ + VE analysis │  │               │  │               │
└───────────────┘  └───────────────┘  └───────────────┘
```

Each agent is a standard A2A endpoint:
- `GET /.well-known/agent-card.json` — Agent Card with `x-construction` extensions (the legacy `/.well-known/agent.json` path is served too)
- `POST /` — JSON-RPC 2.0 (`message/send`, `tasks/get`, `tasks/cancel`). The demo agents do not stream, so `message/stream` is refused.

Agent output is validated against the SDK's Pydantic models (`EstimateV1`, `QuoteV1`, `RFIV1`) before it is returned. With Anthropic, the same models also constrain the LLM's response through structured outputs.

## Quick Start

### 1. Set up environment

```bash
cd examples
cp .env.example .env
# Edit .env with your API key
```

### 2. Install dependencies

```bash
pip install -e "../sdk[all]"       # the TACO SDK from this checkout
pip install -r requirements.txt    # demo dependencies (FastAPI, LLM SDKs, ...)
```

Or run `make demo-install` from the repository root, which does the same.

### 3. Run locally

```bash
python run_demo.py
```

All four services listen on `127.0.0.1` only. Set `AGENT_BIND_HOST` / `ORCHESTRATOR_HOST` (for example to `0.0.0.0`) if you need them reachable from other machines. If any service exits, `run_demo.py` reports it and stops the others.

### 4. Open the dashboard

Navigate to **http://localhost:8000**

1. Click **"Discover Agents"** — three agents appear with their trade, CSI divisions, and skills
2. Click **"Send Task"** on any agent skill — the BOM is sent via JSON-RPC, the LLM processes it, and typed results appear
3. Click **"Run Full Pipeline"** — sends the BOM to all three agents in parallel and shows combined results
4. Check the **message log** at the bottom to see the raw A2A JSON-RPC exchanges

## Docker Compose

```bash
cd examples
cp .env.example .env
# Edit .env with your API key
docker compose up --build
```

(`make demo-docker` from the repository root does the same.) The build context is the repository root; its `.dockerignore` keeps `.git`, `examples/.env` and local caches out of the image. Ports are published on `127.0.0.1` only.

## The Orchestrator Only Talks to Configured Agents

The orchestrator contacts only the agent URLs listed in `AGENT_URLS` (default: the three demo agents on `localhost`). Requests from the dashboard or API that name any other URL are rejected with HTTP 400, and the **Register Agent** box only accepts URLs from that list. To add your own agent, put it in `AGENT_URLS` and restart:

```bash
AGENT_URLS=http://localhost:8001,http://localhost:8002,http://localhost:8003,http://localhost:8080 python run_demo.py
```

The orchestrator API sends no CORS headers (the dashboard is served from the same origin) and only accepts `POST` requests with `Content-Type: application/json`.

## Demo: Dynamic Skill Registration

This showcases how the A2A ecosystem adapts when agents add new capabilities:

1. Start the demo and click "Discover Agents"
2. Click **"+ Add VE Skill to Estimator"** in the header
3. Click **"Discover Agents"** again — the Estimating Agent now shows a second skill marked **NEW**
4. Click "Send Task" on the new "Value Engineering Analysis" skill

You can also add skills via curl:

```bash
curl -X POST http://localhost:8001/admin/skills \
  -H "Content-Type: application/json" \
  -d '{
    "id": "value-engineering",
    "name": "Value Engineering Analysis",
    "description": "Identifies cost reduction opportunities",
    "x-construction": {
      "taskType": "value-engineering",
      "inputSchema": "bom-v1",
      "outputSchema": "ve-suggestions-v1"
    }
  }'
```

The demo agents leave these admin endpoints unauthenticated; that is one reason they listen on `127.0.0.1` only.

## Demo: Full Pipeline

Click **"Run Full Pipeline"** in the dashboard header to send the sample BOM to all three agents in parallel. The orchestrator calls `POST /api/run-pipeline`, which dispatches estimate, quote, and RFI tasks concurrently and returns combined results. Each step's status comes from the returned task's state, so a task that failed inside the agent shows as failed.

You can also call it directly (an empty object uses the sample BOM; pass `{"inputData": {...}}` to send your own):

```bash
curl -X POST http://localhost:8000/api/run-pipeline \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Demo: Agent-to-Agent Communication

The estimating agent can fetch real supplier pricing from the supplier quote agent before generating its estimate. Set the `SUPPLIER_AGENT_URL` environment variable:

```bash
export SUPPLIER_AGENT_URL=http://localhost:8002
```

When set, the estimating agent uses the TACO SDK client to send a `material-procurement` task to the supplier agent, checks that the task completed, and validates the returned quote against `quote-v1`. The quote is then passed to the LLM as clearly delimited data in the user message (never as part of its instructions). The artifact metadata includes `supplierDataUsed: true/false` to show whether supplier data was used; if the supplier call fails, the reason is logged and the estimate is made without it.

With Docker Compose, uncomment the `SUPPLIER_AGENT_URL=http://supplier-agent:8002` line under `estimating-agent` in `docker-compose.yml`.

## Demo: Agent Monitors

Every agent includes a live tracing UI at `/monitor`. After starting the demo, open any agent's monitor to see real-time A2A traffic:

- **Estimating Agent:** http://localhost:8001/monitor
- **Supplier Agent:** http://localhost:8002/monitor
- **RFI Agent:** http://localhost:8003/monitor

The monitor traces:
- **Incoming requests** — JSON-RPC calls received by the agent
- **Handler execution** — Task processing timing and results
- **Outgoing calls** — Peer agent calls (e.g., estimating → supplier)
- **Discovery** — Agent registration events

Events stream live via WebSocket and are stored in a ring buffer (max 2000).

To enable the monitor in your own agent, add `enable_monitor=True`:

```python
server = A2AServer(card, enable_monitor=True)
```

## Verification

Test agent discovery directly:

```bash
curl http://localhost:8001/.well-known/agent-card.json | python -m json.tool
```

Test a task via JSON-RPC (every A2A message needs a `messageId`):

```bash
curl -X POST http://localhost:8001/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "messageId": "msg-test-1",
        "parts": [{"kind": "data", "data": {
          "projectId": "test", "trade": "mechanical", "csiDivision": "23",
          "lineItems": [{"id": "LI-001", "description": "Exhaust fan, centrifugal inline, 2000 CFM", "quantity": 6, "unit": "EA"}],
          "metadata": {"generatedBy": "test", "generatedAt": "2026-01-01T00:00:00Z"}
        }}]
      },
      "metadata": {"taskType": "estimate"}
    }
  }'
```

## File Structure

```
examples/
├── README.md
├── quick_start.py               # Minimal single-file agent
├── peer_communication.py        # Two agents communicating
├── .env.example
├── requirements.txt             # Demo dependencies (install the SDK from ../sdk first)
├── Dockerfile
├── docker-compose.yml
├── run_demo.py
├── common/
│   ├── a2a_models.py          # Re-exports A2A types and helpers from the TACO SDK
│   ├── a2a_server.py          # Re-exports the SDK's A2AServer
│   ├── llm_provider.py        # Anthropic/OpenAI wrapper returning schema-validated JSON
│   ├── schemas.py             # Re-exports the SDK's bom/rfi/estimate/quote Pydantic models
│   └── sample_data.py         # Sample mechanical HVAC BOM
├── agents/
│   ├── estimating_agent.py    # Port 8001 — estimate + value-engineering
│   ├── supplier_quote_agent.py # Port 8002 — material-procurement
│   └── rfi_generation_agent.py # Port 8003 — rfi-generation
└── orchestrator/
    ├── app.py                 # Orchestrator backend
    └── dashboard.html         # Web UI
```

## Configuration

Set these in `.env` or the environment:

| Variable | Used by | Default |
|----------|---------|---------|
| `LLM_PROVIDER` | agents | `anthropic` (or `openai`) |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | agents | model `claude-opus-5` |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | agents | model `gpt-4o` |
| `SUPPLIER_AGENT_URL` | estimating agent | unset (no agent-to-agent pricing) |
| `AGENT_URLS` | orchestrator | the three demo agents on `localhost` |
| `ORCHESTRATOR_HOST` | `run_demo.py`, `python -m orchestrator.app` | `127.0.0.1` |
| `ORCHESTRATOR_PORT` | `python -m orchestrator.app` | `8000` |
| `AGENT_BIND_HOST` | `run_demo.py`, `python -m agents.<name>` | `127.0.0.1` |

With Anthropic, requests use structured outputs and, on models that support it (including the default), the server-side refusal fallback (`fallbacks: "default"`). LLM errors are logged by the agent; callers only see a short, generic error message.
