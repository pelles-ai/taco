<p align="center">
  <img src="assets/caip_logo.png" alt="CAIP Logo" width="300">
</p>

# CAIP — Construction A2A Interoperability Protocol

**An open standard for AI agent communication in the built environment.**

CAIP is a construction-specific ontology layer built on top of the [A2A protocol](https://a2a-protocol.org) (Linux Foundation). It defines a shared vocabulary of task types, typed data schemas, and agent discovery extensions so that AI agents across the construction industry can interoperate — regardless of who built them.

Every CAIP agent is a standard A2A agent. Zero lock-in.

---

## What CAIP Adds

| Layer | What it defines | Example |
|-------|----------------|---------|
| **Task Types** | A typed vocabulary of construction workflows | `takeoff`, `estimate`, `rfi-generation`, `submittal-review`, `schedule-coordination` |
| **Data Schemas** | Typed JSON schemas for construction artifacts | `bom-v1`, `rfi-v1`, `estimate-v1`, `schedule-v1`, `quote-v1` |
| **Agent Discovery** | Construction extensions to A2A Agent Cards | Filter by trade, CSI division, project type, file format, platform integration |
| **Security** | Scope taxonomy, trust tiers, token delegation | `caip:trade:mechanical`, `caip:task:estimate`, `caip:project:PRJ-0042:write` |

## How It Works

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Takeoff     │───▶│  Estimating  │───▶│  Supplier    │───▶│  Bid Package │
│  Agent       │    │  Agent       │    │  Agent       │    │  (complete)  │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └──────────────┘
       │ bom-v1            │ estimate-v1       │ quote-v1
       ▼                   ▼                   ▼
╔══════════════════════════════════════════════════════════════════════════╗
║  CAIP — shared task types, data schemas, agent discovery               ║
╚══════════════════════════════════════════════════════════════════════════╝
       ▲                   ▲                   ▲
       │ schedule-v1       │ rfi-v1            │
┌──────┴───────┐    ┌──────┴───────┐    ┌──────────────┐
│  Schedule    │    │  RFI Agent   │    │  Architect   │
│  Agent       │    │              │    │  Agent       │
└──────────────┘    └──────────────┘    └──────────────┘
```

Different companies. Different AI models. One shared language.

## Sandbox Demo

The repo includes a fully functional demo with 3 LLM-powered agents, an orchestrator dashboard, and a live flow diagram.

<p align="center">
  <img src="assets/demo.gif" alt="CAIP Sandbox Demo" width="800">
</p>

**Run it yourself:**

```bash
# Clone and configure
git clone https://github.com/pelles-ai/caip.git && cd caip
cp examples/.env.example examples/.env
# Edit examples/.env and add your API key (Anthropic or OpenAI)

# Run with Docker (recommended)
make demo-docker

# Or run locally
make demo-install && make demo
```

Then open [http://localhost:8000](http://localhost:8000), click **Discover Agents**, and send tasks to see typed schemas flow between independent agents in real time.

## Repository Structure

```
caip/
├── Makefile                         # demo, demo-docker, demo-stop
├── spec/
│   ├── task-types.md                # Construction task type definitions
│   ├── agent-card-extensions.md     # x-construction Agent Card fields
│   ├── security.md                  # Auth model, scope taxonomy, trust tiers
│   └── schemas/                     # JSON Schema definitions (bom-v1, rfi-v1, estimate-v1, ...)
├── docs/
│   ├── abstract.md                  # Position paper
│   ├── caip-architecture-overview.html
│   ├── caip-auth-flow.html          # Auth & delegation flow diagram
│   └── caip-security-model.html     # Scopes, trust tiers, extension fields
├── sdk/                             # Reference SDK (Python)
│   └── caip/                        # agent_card, schemas, registry, client
└── examples/                        # Sandbox demo
    ├── docker-compose.yml           # 4 services, hot-reload
    ├── run_demo.py                  # Local launcher (all 4 processes)
    ├── common/                      # Shared A2A server, models, LLM provider
    ├── agents/                      # 3 LLM-powered CAIP agents
    │   ├── estimating_agent.py      # :8001 — estimate + value-engineering
    │   ├── supplier_quote_agent.py  # :8002 — material-procurement
    │   └── rfi_generation_agent.py  # :8003 — rfi-generation
    └── orchestrator/                # :8000 — dashboard + agent discovery
        ├── app.py
        └── dashboard.html           # Single-file UI with live flow diagram
```

## Quick Start

```python
from caip import ConstructionAgentCard, ConstructionSkill

# Define your agent
card = ConstructionAgentCard(
    name="My Electrical Estimating Agent",
    trade="electrical",
    csi_divisions=["26"],
    skills=[
        ConstructionSkill(
            id="generate-estimate",
            task_type="estimate",
            input_schema="bom-v1",
            output_schema="estimate-v1",
        )
    ],
)

# Serve as an A2A-compatible endpoint
card.serve(host="0.0.0.0", port=8080)
```

```python
from caip import AgentRegistry

# Discover agents
registry = AgentRegistry(url="https://registry.caip.dev")
agents = registry.find(trade="plumbing", task_type="material-procurement")

# Delegate a task
result = await agents[0].run_task(
    task_type="material-procurement",
    input=bom,
)
# result.schema == "quote-v1"
```

> **Note:** The Python SDK uses snake_case parameter names (e.g., `csi_divisions`, `task_type`) that map to the camelCase JSON fields defined in the spec (`csiDivisions`, `taskType`).

## Principles

1. **Ontology, not protocol.** CAIP builds on A2A using its native extension points. Every CAIP agent is a standard A2A agent.
2. **Agents are opaque.** Agents collaborate without exposing internals — proprietary logic, pricing models, and trade secrets stay private.
3. **Open and composable.** Apache 2.0 licensed. The spec, schemas, and SDK are open source. The registry is a shared resource.
4. **Construction-native.** Task types, schemas, and discovery are designed for how construction actually works — by trade, CSI division, project phase, and platform.

## Status

🚧 **Early stage** — We're defining the core schemas and building the reference SDK. Looking for construction technology companies, trade contractors, GCs, and platform vendors to help shape the standard.

## Get Involved

- **GitHub Discussions**: Share ideas and feedback
- **Issues**: Report problems or suggest improvements
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

*Initiated by [Pelles](https://pelles.ai). Built on the [A2A protocol](https://a2a-protocol.org) (Linux Foundation).*
