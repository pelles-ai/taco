---
sidebar_position: 2
title: Integrate Your Platform
---

# Integrate Your Platform

Already have a construction platform? You don't need to rewrite it. Add an **agent sidecar** — a thin TACO-compatible wrapper — that exposes your platform's capabilities as A2A agent skills.

## What is an Agent Sidecar?

An agent sidecar is a small service that sits alongside your existing platform and:

1. **Publishes an Agent Card** describing your platform's capabilities in TACO terms
2. **Translates incoming A2A requests** into calls to your platform's existing API
3. **Returns results** using standard TACO data schemas

Your platform's internals stay private. The sidecar only exposes what you want to share.

## 1. Define Your Agent Card

Map your platform's capabilities to TACO task types and trades:

```python
from taco import ConstructionAgentCard, ConstructionSkill

card = ConstructionAgentCard(
    name="Acme Estimating Platform",
    url="http://your-platform:9000",
    trade="general",
    csi_divisions=["01", "02", "03", "04", "05"],
    integrations=["procore", "plangrid"],
    skills=[
        ConstructionSkill(
            id="generate-estimate",
            name="Generate Cost Estimate",
            description="Creates detailed cost estimates from BOM data",
            task_type="estimate",
            input_schema="bom-v1",
            output_schema="estimate-v1",
        ),
        ConstructionSkill(
            id="review-rfi",
            name="Review RFI",
            description="Reviews and responds to RFIs using project context",
            task_type="rfi-response",
            input_schema="rfi-v1",
            output_schema="rfi-v1",
        ),
    ],
)
```

## 2. Map Capabilities to TACO Task Types

Review the [Task Types](/docs/task-types) list and identify which ones your platform supports:

| Your Platform Feature | TACO Task Type | Input Schema | Output Schema |
|---|---|---|---|
| Cost estimation | `estimate` | `bom-v1` | `estimate-v1` |
| RFI management | `rfi-generation` / `rfi-response` | — | `rfi-v1` |
| Schedule management | `schedule-coordination` | — | `schedule-v1` |
| Submittal tracking | `submittal-review` | — | — |
| Change orders | `change-order` | — | `change-order-v1` |

## 3. Build the Sidecar Handler

The handler translates A2A requests into calls to your platform's API:

```python
from taco import make_artifact, make_data_part
from taco.server import A2AServer
from taco.types import Artifact, Task

# Your existing platform client
from your_platform import PlatformClient

platform = PlatformClient(api_key="...")


async def handle_estimate(task: Task, input_data: dict) -> Artifact:
    # Call your platform's existing API
    result = await platform.estimate(input_data)

    # Return as TACO-typed artifact
    return make_artifact(
        parts=[make_data_part(result)],
        name="cost-estimate",
        description="Estimate from platform API",
    )
```

## 4. Register with a Registry

Make your agent discoverable by other TACO agents:

```python
from taco import AgentRegistry

registry = AgentRegistry()
await registry.register("http://your-platform:9000")

# Other agents can now find you
agents = registry.find(task_type="estimate")
```

## Architecture

```
┌─────────────────────────┐     ┌──────────────────────┐
│   Your Platform API     │◄────│   TACO Agent Sidecar │
│   (unchanged)           │     │   - Agent Card       │
│   - /api/estimates      │     │   - A2A endpoint     │
│   - /api/rfis           │     │   - Schema mapping   │
│   - /api/schedules      │     │                      │
└─────────────────────────┘     └──────────┬───────────┘
                                           │
                                    A2A Protocol
                                           │
                                ┌──────────┴───────────┐
                                │   Other TACO Agents   │
                                │   (any vendor)        │
                                └───────────────────────┘
```

Your platform remains unchanged. The sidecar handles all TACO/A2A communication.

## Next Steps

- See the full [SDK Reference](/docs/sdk) for server configuration options
- Review [Security](/docs/security) for authentication and trust tiers
- Check [Agent Card Extensions](/docs/agent-card-extensions) for all metadata fields
