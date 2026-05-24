---
sidebar_position: 3
title: TACO vs. Alternatives
description: How TACO compares with proprietary platform APIs, raw A2A, and homegrown integrations for construction agent interoperability.
---

# TACO vs. Alternatives

A practical comparison of how TACO stacks up against the realistic alternatives. None of these are strawmen — each one is a path real teams take.

## TACO vs. proprietary platform APIs

The dominant approach today is point-to-point integration with each platform's REST API: Procore, Autodesk Construction Cloud, Bluebeam, PlanGrid, and so on.

| | Proprietary platform APIs | TACO |
|---|---------------------------|------|
| **Integration cost** | One per platform, per direction. Custom mapping each time. | One integration per *agent type*, reusable across every TACO-compatible platform. |
| **Schema discovery** | Read the docs, hope they're current. | Agent advertises its `taskType`, `inputSchema`, `outputSchema` in its Agent Card. |
| **Agent discovery** | Out of scope — you find vendors manually. | Filter the registry by trade, CSI division, project type. |
| **Auth model** | Each vendor's OAuth, each vendor's scopes. | A2A's five standard schemes; TACO scope taxonomy on top. |
| **Versioning** | Vendor-managed, sometimes silent. | Schema names are explicit (`bom-v1`), versions are visible. |
| **Lock-in** | High — your code knows about vendor X. | None — every TACO agent is a valid A2A agent. |
| **Cost** | License + integration engineer time. | Apache 2.0, build on top. |
| **Best for** | Single-platform shops that have already standardized. | Multi-platform projects, multi-vendor ecosystems, any future-proof agent strategy. |

The realistic answer is **both**: a TACO agent on the inside that exposes typed capabilities, and platform integrations on the outside via vendor APIs (or MCP servers) that the agent uses internally.

## TACO vs. raw A2A

A2A is the transport. You can build everything on raw A2A without TACO — and for non-construction agents, you should.

| | Raw A2A | TACO on A2A |
|---|---------|-------------|
| **Agent discovery** | By name/URL | By trade, CSI division, task type, platform |
| **Task semantics** | Freeform strings | 18 named task types |
| **Data interchange** | Unstructured artifacts | 6 typed schemas with cross-references |
| **Security scopes** | Generic OAuth | Construction-scoped (`taco:trade:mechanical`, `taco:project:PRJ-0042:write`) |
| **Registry** | Not defined by the spec | Trade-aware registry with trust tiers |
| **Lock-in** | None | None — every TACO agent is a valid A2A agent |
| **Best for** | Non-construction agent ecosystems | Construction-specific workflows |

You cannot lose by adopting TACO. Non-TACO clients ignore the `x-construction` extension gracefully — the agent still answers raw A2A traffic.

## TACO vs. building it yourself

A common path is to define your own internal schemas and your own internal agent discovery, scoped to one organization.

| | Homegrown | TACO |
|---|-----------|------|
| **Time to first agent** | Weeks to define schemas, run a working group, write the SDK | Two minutes ([Quick Start](/docs/getting-started/quick-start)) |
| **Schema review** | Your team | Community + spec working group |
| **Cross-org interop** | Requires you to publish + market your spec | Already public, already aligned with A2A |
| **Maintenance** | Yours forever | Shared |
| **Best for** | Truly novel domains | Construction |

Construction is not novel. Trades, CSI divisions, RFIs, BOMs, change orders, schedules — these exist and have meanings. The shared dictionary is the value.

## TACO vs. MCP-only agents

A growing pattern is to wrap construction tools as [MCP](/docs/protocol-stack) servers and call them from a generic agent runtime.

| | MCP-only | TACO + MCP |
|---|----------|------------|
| **What it standardizes** | How an LLM reaches tools | How agents discover and talk to each other |
| **Agent discovery** | Out of scope | Built in |
| **Cross-agent typing** | None — tool calls are LLM-driven | Typed schemas the LLM does not need to invent |
| **Best for** | Single-agent workflows | Multi-agent construction workflows |

These are not competitors. The recommended pattern is **A2A between agents, MCP from each agent to its tools, TACO as the vocabulary**. See [A2A, MCP, and TACO](/docs/protocol-stack) for the full picture.

## When TACO is not the right answer

- **You are not in the construction or built-environment space.** Use raw A2A.
- **You have exactly one platform and no plans for multi-vendor interop.** Use the vendor's SDK.
- **You are building an internal-only workflow with no agent-to-agent communication.** You can skip the protocol layer entirely.

For everyone else: TACO is the cheapest way to make your software agent-compatible without committing to any specific vendor or model.
