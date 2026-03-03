---
sidebar_position: 1
title: Introduction
---

# TACO — The A2A Construction Open-standard

Every construction tool should be agent-compatible. TACO gives them a shared language.

## The Problem

Construction projects succeed or fail based on communication. A superintendent coordinates across dozens of trades, tools, and companies every day — sharing status, resolving conflicts, pushing decisions forward. The software these teams use should be able to do the same.

Today, most construction software operates in silos. Platforms don't share data, formats don't align, and when AI agents enter the picture — generating takeoffs, drafting RFIs, coordinating schedules — they're being built in isolation too. Different APIs, different schemas, no shared vocabulary.

Every tool in the construction ecosystem needs to become agent-compatible. Whether it's a fully autonomous AI agent or an existing platform with an agent sidecar, every piece of software should be able to communicate its status, share generated content, and coordinate work across the project — just like the people operating it need to do to succeed.

## Why Now

The [A2A protocol](https://a2a-protocol.org) (Linux Foundation) provides a universal standard for agent-to-agent communication: Agent Cards for discovery, JSON-RPC for messaging, task lifecycle management, and streaming. It solves the transport layer.

But A2A is domain-agnostic. It doesn't know what a takeoff is, what a BOM looks like, or how to find an agent that handles mechanical estimating for healthcare projects. Construction needs a shared vocabulary on top of A2A — one that makes it easy for any tool, whether natively agentic or wrapped with a sidecar, to participate in the ecosystem.

## What TACO Adds

TACO is a construction-specific ontology layer built on A2A. It defines:

| Layer | What it defines | Example |
|-------|----------------|---------|
| **Task Types** | A typed vocabulary of construction workflows | `takeoff`, `estimate`, `rfi-generation`, `submittal-review` |
| **Data Schemas** | Typed JSON schemas for construction artifacts | `bom-v1`, `rfi-v1`, `estimate-v1`, `schedule-v1`, `quote-v1` |
| **Agent Discovery** | Construction extensions to A2A Agent Cards | Filter by trade, CSI division, project type, platform integration |
| **Security** | Scope taxonomy, trust tiers, token delegation | `taco:trade:mechanical`, `taco:task:estimate`, `taco:project:PRJ-0042:write` |

Every TACO agent is a standard A2A agent. Zero lock-in.

## What TACO Does Not Do

- **Replace A2A.** TACO uses A2A's native extension points. It does not fork or modify the protocol.
- **Dictate implementation.** Agents are opaque. TACO defines what goes in and what comes out — not how agents work internally.
- **Replace existing platforms.** TACO integrates with Procore, ACC, Bluebeam, and others. It connects the ecosystem; it doesn't replace it.
- **Require AI.** Any software that speaks A2A and follows TACO schemas can participate — fully agentic systems, existing platforms with agent sidecars, human-in-the-loop tools, and legacy system adapters. The goal is to make all construction software agent-compatible.

## Quick Example

```python
from taco import ConstructionAgentCard, ConstructionSkill

# Define an agent that performs mechanical takeoffs
card = ConstructionAgentCard(
    name="My Mechanical Takeoff Agent",
    trade="mechanical",
    csi_divisions=["22", "23"],
    skills=[
        ConstructionSkill(
            id="generate-bom",
            task_type="takeoff",
            output_schema="bom-v1",
        )
    ],
)

# Serve as an A2A-compatible endpoint
card.serve(host="0.0.0.0", port=8080)
```

## Status

TACO is early stage. We're defining the core schemas and building the reference SDK. We're looking for construction technology companies, trade contractors, GCs, and platform vendors to help shape the standard.

- [GitHub Repository](https://github.com/pelles-ai/taco)
- [Contributing Guide](https://github.com/pelles-ai/taco/blob/main/CONTRIBUTING.md)
