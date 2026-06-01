---
title: ADR-0001 — Build on A2A rather than designing a new transport
description: Why TACO is built on the Linux Foundation's A2A protocol instead of a custom construction-specific wire format.
sidebar_position: 1
---

# ADR-0001 — Build on A2A rather than designing a new transport

**Status:** Accepted
**Date:** 2026-02-15

## Context

When TACO was scoped in early 2026, the project needed to settle the most consequential design question: how do construction agents talk to each other on the wire?

There were three realistic options:

1. **Design a custom construction-specific protocol** — gRPC service definitions, a bespoke event envelope, hand-rolled discovery
2. **Adopt an existing agent-to-agent protocol** — A2A (Linux Foundation), MCP (Anthropic), or one of the LLM-orchestration frameworks' internal protocols
3. **Build on top of OpenAPI / REST** — every vendor publishes an OpenAPI spec, codegen the rest

Each option had real proponents. Construction is enough of a beast that "we know what construction needs better than a generic protocol does" is a serious argument.

## Decision

We build TACO on top of [A2A](https://a2a-protocol.org) — the Linux Foundation's agent-to-agent protocol — using its native extension mechanisms. We do not fork A2A, do not modify its wire format, and do not require any A2A change to land TACO features. Construction-specific semantics live in an `x-construction` extension on the Agent Card, in our task type vocabulary, and in our typed JSON schemas.

Every TACO agent is a valid A2A agent. Non-TACO clients ignore the construction extension gracefully.

## Alternatives considered

### A custom construction protocol

Pros: maximum fit to construction semantics, no compromise with generic concerns, total control of versioning.

Cons:
- Forks the agent ecosystem at the start of its life. Construction agents would have been unable to talk to non-construction agents without a translation layer.
- Multiplies the "first 10 lines of code" cost for every construction software vendor.
- Concentrates protocol governance in a single company (us) — exactly the dynamic the construction software space already complains about.
- Reinvents transport, auth, streaming, task lifecycle — all things A2A solved and the community already reviewed.

### MCP

MCP is excellent at what it does — connecting an LLM to tools and data sources. It is the wrong layer for agent-to-agent communication. Several construction teams initially asked "isn't this MCP?" — the answer is *MCP is orthogonal*. A TACO agent often uses MCP internally to reach its own data and tools; agents talk to other agents over A2A. See [`/docs/protocol-stack`](../protocol-stack).

### OpenAPI / REST

Every construction platform publishes a REST API. Could we just standardize a set of OpenAPI patterns?

OpenAPI is great for documenting a single service. It is poor at:
- Discovery — `/.well-known/openapi.yaml` exists but isn't a registry concept
- Bidirectional streaming and long-running tasks — REST is request-response; OpenAPI's streaming extensions are immature
- Cross-service typed handoffs — schemas in OpenAPI aren't easy to share between specs
- Capability negotiation — protocol versioning is per-endpoint, not per-message

A2A solves these out of the box.

## Consequences

### Positive

- TACO inherits A2A's task lifecycle, JSON-RPC dialect, streaming via SSE, and five well-understood auth schemes (`apiKey`, `http`, `oauth2`, `openIdConnect`, `mutualTLS`) without writing any of it.
- Adoption: every TACO agent shows up as a valid agent to any A2A-aware client. That makes the on-ramp for non-construction tooling (orchestration frameworks, agent IDEs, monitoring) much shorter.
- Governance: TACO sits next to other domain extensions on top of A2A. The Linux Foundation owns the transport; we own the construction vocabulary. Neither side has to absorb the other's scope.
- Versioning: A2A's protocol versioning (`A2A-Version` headers, capability negotiation) handles transport churn for us. TACO only versions the construction concepts.

### Negative

- We don't control the transport. When A2A makes a breaking change (e.g. the v0.3 → v1.0 wire cutover), TACO has to track it. See [`sdk/V1_MIGRATION.md`](https://github.com/pelles-ai/taco/blob/main/sdk/V1_MIGRATION.md).
- Some construction-specific optimizations we might want (e.g. attaching a BIM-fragment streaming channel to a task) need to be expressed via A2A extension mechanisms rather than as first-class features.
- Education tax: visitors confused about why we don't "just build TACO" need [the protocol stack page](../protocol-stack) and [the cookbook recipes](../cookbook/) to see the layering payoff.

### Reversibility

The decision is reversible at high cost. If A2A's direction becomes incompatible with TACO over time, we could fork a TACO-specific transport. The SDK already encapsulates transport details behind `TacoClient` / `A2AServer`, so the application surface area would survive. But the *ecosystem* benefit of being one of many A2A dialects would be lost — a serious cost worth not paying lightly.

## References

- [A2A Protocol (Linux Foundation)](https://a2a-protocol.org)
- [Protocol stack — A2A, MCP, and TACO](../protocol-stack)
- [SDK v1 migration plan](https://github.com/pelles-ai/taco/blob/main/sdk/V1_MIGRATION.md)
