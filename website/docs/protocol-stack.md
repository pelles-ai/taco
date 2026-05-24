---
sidebar_position: 1
title: A2A, MCP, and TACO
description: How the three protocols relate — A2A for agent-to-agent transport, MCP for agent-to-tool access, TACO for construction-specific vocabulary.
---

# A2A, MCP, and TACO

Three protocols come up constantly in conversations about agent ecosystems: **A2A**, **MCP**, and **TACO**. They are not competitors. They solve different problems and stack together.

This page explains each one in plain language first, then in technical detail, then shows how they fit on a real construction workflow.

:::tip TL;DR
- **A2A** moves messages **between agents**.
- **MCP** lets a single agent reach **tools and data**.
- **TACO** is the **construction vocabulary** the messages are written in.

You can use any of them alone. They become more powerful together.
:::

## The jobsite analogy

If you have never worked with these protocols before, here is a five-second mental model.

| Protocol | Like | Job |
|---------|------|-----|
| **A2A** | The two-way radio on the jobsite | Lets any worker reach any other worker, regardless of trade |
| **MCP** | The toolbox each worker carries | Lets a worker pick up specific tools — a tape measure, a calculator, a database |
| **TACO** | The trade vocabulary and standard forms | What everyone means by "takeoff," what a BOM looks like, how an RFI is written |

The radio (A2A) and the toolbox (MCP) work whether you are talking about plumbing or sandwich-making. TACO is the part that makes the conversation *about construction*.

## A2A — Agent to Agent

**[A2A](https://a2a-protocol.org)** is the Linux Foundation protocol for agent-to-agent communication.

It defines:

- **Agent Cards** — a `/.well-known/agent-card.json` document each agent serves to advertise its name, capabilities, and how to reach it.
- **JSON-RPC messaging** — `message/send` and `message/stream` for sending tasks.
- **Task lifecycle** — `submitted` → `working` → `completed` / `failed` / `canceled`.
- **Streaming** — Server-Sent Events for incremental responses.
- **Authentication** — five scheme types: `apiKey`, `http`, `oauth2`, `openIdConnect`, `mutualTLS`.

A2A is **domain-agnostic** on purpose. It does not know what a "takeoff" is. It just knows how to deliver a structured message from one agent to another and track its lifecycle.

## MCP — Model Context Protocol

**[MCP](https://modelcontextprotocol.io)** is Anthropic's open standard for connecting an AI model (usually inside an agent) to external tools and data sources.

It defines:

- **Servers** — small processes that expose **tools** (functions an LLM can call), **resources** (data the LLM can read), and **prompts** (templates the LLM can use).
- **Clients** — typically agents or IDEs that connect to MCP servers and let an LLM use what they expose.

MCP is **vertical**: it connects a single agent down to its capabilities. It is not how two agents talk to each other.

A construction agent might use MCP to:
- Read drawings from a BIM server
- Query a project database
- Call an estimating engine
- Search a supplier catalog

## TACO — The construction layer

TACO sits **on top of A2A**. It does not change how the messages travel. It defines what the messages *mean*.

It adds four things:

1. **Task types** — a vocabulary of construction workflows: `takeoff`, `estimate`, `rfi-generation`, `schedule-coordination`, and 14 more. See [Task Types](/docs/task-types).
2. **Data schemas** — typed JSON schemas for the artifacts agents exchange: `bom-v1`, `rfi-v1`, `estimate-v1`, `schedule-v1`, `quote-v1`, `change-order-v1`. See [Data Schemas](/docs/schemas/).
3. **Agent discovery** — Agent Card extensions that let you find agents by trade, CSI division, project type, and platform integration. See [Agent Card Extensions](/docs/agent-card-extensions).
4. **Security scopes** — a construction-shaped OAuth scope taxonomy. See [Security](/docs/security).

Every TACO agent is a **valid A2A agent**. Non-TACO clients ignore the `x-construction` extension gracefully — no lock-in.

## Putting it together

A real workflow uses all three.

```
   ┌──────────────────────────┐                ┌──────────────────────────┐
   │   GC Orchestrator Agent  │  ───  A2A  ──▶ │   Supplier Quoter Agent  │
   │   (speaks TACO)          │                │   (speaks TACO)          │
   └────────────┬─────────────┘                └────────────┬─────────────┘
                │  MCP                                       │  MCP
                ▼                                            ▼
   ┌──────────────────────────┐                ┌──────────────────────────┐
   │ Procore · AutoCAD · DB   │                │ ERP · pricing API ·       │
   │                          │                │ catalog                   │
   └──────────────────────────┘                └──────────────────────────┘
```

1. The orchestrator sends a `material-procurement` task to the supplier quoter **over A2A**.
2. The message body uses **TACO's** `bom-v1` schema, so the supplier knows exactly what is being asked.
3. The supplier quoter uses **MCP** to query its pricing API and catalog.
4. It returns a `quote-v1` artifact — again typed by TACO.
5. The orchestrator parses the typed quote and continues the workflow.

Swap the supplier for any other TACO-compatible quoter and the workflow still runs. That is the point.

## What if I do not use MCP?

You do not need MCP to build a TACO agent. Your agent can use any internal mechanism — a Python library, a direct database call, a custom REST client — to do its work. TACO only cares about what the agent **advertises** and what **goes in and comes out**.

MCP is a popular and clean way to connect an LLM-driven agent to tools, but it is one option among many.

## What if I do not use TACO?

Then you have a plain A2A agent. Other generic A2A clients can talk to it, but they will not know it handles `takeoff` or returns `bom-v1`. Discovery, schema validation, and trade-based filtering all become manual.

TACO is the layer that turns *agents that can talk* into *a construction ecosystem*.

## Where to go next

- [Why TACO?](/docs/why-taco) — the longer-form argument for why the construction industry needs this layer
- [Core Concepts](/docs/core-concepts) — Agent Cards, Skills, Tasks, Messages, Parts, Artifacts
- [Quick Start](/docs/getting-started/quick-start) — run a TACO agent in under 2 minutes
