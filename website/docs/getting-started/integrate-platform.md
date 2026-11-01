---
sidebar_position: 3
title: Integrate Your Platform
description: Wrap your existing construction platform as a TACO agent with a thin sidecar — no rewrites required.
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
            output_schema="rfi-response-v1",
        ),
    ],
)
```

## 2. Map Capabilities to TACO Task Types

Review the [Task Types](/docs/task-types) list and identify which ones your platform supports:

| Your Platform Feature | TACO Task Type | Input Schema | Output Schema |
|---|---|---|---|
| Cost estimation | `estimate` | `bom-v1` | `estimate-v1` |
| RFI management | `rfi-generation` / `rfi-response` | — / `rfi-v1` | `rfi-v1` / `rfi-response-v1` (planned) |
| Schedule management | `schedule-coordination` | `bom-v1`, `estimate-v1` | `schedule-v1` |
| Submittal tracking | `submittal-review` | — | `submittal-review-v1` (planned) |
| Change orders | `change-order-analysis` | `bom-v1`, `schedule-v1` | `change-order-v1` |

## 3. Build the Sidecar Handler

The handler translates A2A requests into calls to your platform's API:

```python
from pydantic import ValidationError
from taco import (
    A2AServer,
    Artifact,
    Task,
    TacoTaskError,
    get_schema_model,
    make_artifact,
    make_data_part,
)

# Your existing platform client
from your_platform import PlatformClient

platform = PlatformClient(api_key="...")


async def handle_estimate(task: Task, input_data: dict) -> Artifact:
    try:
        bom = get_schema_model("bom-v1").model_validate(input_data)
    except ValidationError as exc:
        # A TacoTaskError message reaches the caller; keep internals out of it
        raise TacoTaskError(f"Input is not a valid bom-v1 ({exc.error_count()} problems)") from exc

    # Call your platform's existing API. If it raises, the caller only
    # sees a generic error id; the details stay in your log.
    result = await platform.estimate(bom.model_dump(by_alias=True, exclude_none=True))

    # Check the platform's answer really is an estimate-v1 before it leaves
    estimate = get_schema_model("estimate-v1").model_validate(result)
    return make_artifact(
        parts=[make_data_part(estimate.model_dump(by_alias=True, exclude_none=True))],
        name="cost-estimate",
        description="Estimate from platform API",
    )


server = A2AServer(card)
server.register_handler("estimate", handle_estimate)
```

A handler that raises fails the task. The caller only sees the message of a `TacoTaskError`; for any other exception it gets `Task handler failed for type 'estimate' (error id ...)`, and the details (platform URLs, credentials in connection strings, stack traces) stay in your log under that id.

## 4. Require a token

A sidecar is a door into your platform, so require a token before other companies' agents can reach it. Pass a `token_verifier` that checks tokens against your identity provider, and declare the scheme on the card:

```python
from taco import AuthContext

async def verify(token: str) -> AuthContext | None:
    claims = await platform.introspect_token(token)  # your IdP check
    if not claims:
        return None
    return AuthContext(subject=claims["sub"], scopes=frozenset(claims["scope"].split()))

server = A2AServer(card, token_verifier=verify)  # instead of A2AServer(card)
server.register_handler("estimate", handle_estimate)
```

Tokens without `taco:task:estimate` are refused with HTTP 403 before the handler runs. See [Security](/docs/security#implementing-it-with-the-sdk) for the card declaration and project-scoped checks.

## 5. Get discovered

Other agents discover yours by fetching its Agent Card. With the SDK, an orchestrator registers your sidecar's URL in its own in-process registry and filters by task type, trade or integration:

```python
from taco import AgentRegistry

registry = AgentRegistry()
await registry.register("http://your-platform:9000")

# The orchestrator can now find you
agents = registry.find(task_type="estimate", integration="procore")
```

There is no shared registry service to publish to yet; a hosted registry is on the [roadmap](/docs/roadmap).

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
