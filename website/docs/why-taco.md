---
sidebar_position: 0
title: Why TACO?
description: TACO is the superintendent's vocabulary, machine-readable. The shared language that lets construction agents discover, trust, and exchange typed data.
---

# Why TACO?

## The Superintendent Analogy

Think of a construction superintendent. Every day, they coordinate across dozens of trades, tools, and companies — translating between electrical engineers and plumbers, reconciling schedules with budgets, making sure the right material shows up at the right time.

**TACO is the superintendent's vocabulary, machine-readable.**

It gives every AI agent on a construction project — estimators, schedulers, RFI generators, supplier bots — a shared language so they can find each other, understand each other's capabilities, and exchange typed data without custom integrations.

## Where TACO Fits

| Layer | Protocol | What it does |
|-------|----------|-------------|
| **Communication** | [A2A Protocol](https://a2a-protocol.org) | Agent-to-agent messaging, task lifecycle, streaming |
| **Tool Access** | [MCP](https://modelcontextprotocol.io) | Connects AI models to external tools and data sources |
| **Construction Intelligence** | **TACO** | Task types, data schemas, and discovery for the built environment |

A2A handles _how_ agents talk. MCP connects agents to _tools_. TACO defines _what construction agents know_ — the domain vocabulary that makes interoperability meaningful.

## TACO vs. Raw A2A

A2A is domain-agnostic by design. TACO fills the gap:

| Capability | Raw A2A | TACO on A2A |
|-----------|---------|-------------|
| Agent discovery | By name/URL | By **trade**, CSI division, task type, platform |
| Task semantics | Freeform strings | **Typed task types** (takeoff, estimate, rfi-generation, ...) |
| Data interchange | Unstructured artifacts | **Typed schemas** (bom-v1, rfi-v1, estimate-v1, schedule-v1, ...) |
| Security scopes | Generic OAuth | **Construction-scoped** (taco:trade:mechanical, taco:project:PRJ-0042:write) |
| Registry | Not defined | **Trade-aware registry** with trust tiers |

Every TACO agent is a valid A2A agent. Zero lock-in — you can always drop back to raw A2A.

## TACO vs. Proprietary Integrations

| | Proprietary | TACO |
|---|------------|------|
| **Standard** | Vendor-specific API | Open standard (Apache 2.0) |
| **Interop** | Only within one platform | Cross-vendor, cross-platform |
| **Community** | Closed roadmap | Community-driven, public spec |
| **Cost** | License fees, integration costs | Free and open source |
| **Lock-in** | High | None — built on A2A + open schemas |

## Who Benefits

### Agent Builders
Build once, work everywhere. Define your agent's trade, task types, and schemas — any TACO-compatible system can discover and use it.

### Platform Vendors
Add TACO support to your existing platform via an [agent sidecar](/docs/getting-started/integrate-platform). Your users get interoperability without rebuilding.

### General Contractors & Owners
Get a unified view across all agents and platforms on your project. Discover agents by trade, enforce project-scoped security, and let tools coordinate automatically.

### The Ecosystem
TACO turns construction AI from a collection of isolated tools into a connected ecosystem. The more agents that speak TACO, the more valuable every agent becomes.

## Get Started

- [Core Concepts](/docs/core-concepts) — understand Agent Cards, Tasks, Messages, Parts, and Artifacts
- [Quick Start](/docs/getting-started/quick-start) — run a TACO agent in under 2 minutes
- [Build a custom agent](/docs/getting-started/build-agent) — define trades, schemas, and handlers
- [Agent-to-agent communication](/docs/getting-started/multi-agent) — connect agents with peer discovery
- [CLI Reference](/docs/cli) — interact with agents from the terminal
