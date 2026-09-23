---
title: ADR-0005 — In-memory registry first, hosted registry second
description: Why the v0.3 registry is an in-process Python class with optional JSON persistence, not a hosted service.
sidebar_position: 5
---

# ADR-0005 — In-memory registry first, hosted registry second

**Status:** Accepted (with hosted registry on the roadmap)
**Date:** 2026-03-18

## Context

Agent discovery is one of the four pillars of TACO. The question is *where the registry lives*.

The obvious answer for a "real protocol" is a hosted, public registry — like npm, PyPI, or Docker Hub for agents. Sign up, publish your Agent Card, and become discoverable globally. This is what most spectators expected when we described agent discovery.

But TACO's earliest users aren't building agents for the open internet. They're building agents that talk to other agents inside a single project, often within a single VPC, often with credentials too sensitive to publish anywhere. The hosted-registry model would force them to either:

1. Run their own private registry instance (operational burden we'd be handing them), or
2. Publish private project data to a shared service (security disaster they'd refuse)

Either choice slows down the first 100 deployments.

## Decision

The reference SDK ships an **in-process Python `AgentRegistry` class** with optional JSON-file persistence (`persistence_path`). Discovery is a Python call (`registry.find(trade="mechanical", task_type="estimate")`). The registry is part of the orchestrator agent's process, not a separate service.

A hosted public registry is on the [roadmap](/docs/roadmap) as a follow-on, scoped to be:
- Opt-in (private projects never publish to it)
- Federated (each org can run their own registry instance; the hosted one is a default, not a gatekeeper)
- Bound to the trust tier model from day one (publishing requires at minimum tier-1 verification)

## Alternatives considered

### Hosted-first

Pros: matches what people expect from "registry," accelerates cross-org discovery, gives TACO a network effect.

Cons:
- Operational complexity TACO doesn't have the capacity to run safely in v0.3.
- Confidentiality concerns block the largest potential adopters (GCs, owners) from publishing.
- Centralization risk — if the hosted registry is the only registry, TACO becomes dependent on whoever runs it.

### File-format-only

Some discovery protocols (Docker Hub via image refs, RFC 8615 well-known URLs) work by URL convention alone — no registry service needed. We could have said "to discover an agent, know its URL."

Cons: doesn't help with the actual question construction users ask: "which agent on this project handles mechanical estimating?" The URL-convention approach answers "where is this agent?" not "what agents exist for this need?"

### gRPC service definition for the registry

A "registry server" with a defined gRPC API that anyone can implement. Closer to where we'll end up, but premature in v0.3 — the in-process abstraction is enough to validate the API surface (`find`, `register`, persistence, filters) before extracting it into a separate service.

## Consequences

### Positive

- Zero operational overhead. A registry is a Python import; persistence is one config option. No hosted service to keep up.
- Privacy by default. No data leaves the orchestrator process unless the operator opts in.
- The `AgentRegistry` API is the same shape it'll be when extracted into a service. Code written today (`registry.find(...)`) keeps working when a hosted backend lands.
- Multi-tenant projects can run their own registry instance per project / per environment without coordination.

### Negative

- No cross-org discovery out of the box. If two orgs want their agents to find each other, they manually share URLs or run their own bridging service.
- Each orchestrator has to bootstrap its own registry from URLs (`registry.register("http://...")`). For large projects this is operational toil — we'd want a hosted registry to push agents to.
- The "where do I publish my agent so others can find me?" question has no answer today beyond "your readme." That's a real adoption friction we accept for v0.3.
- The trust tier model (defined in [security](/docs/security)) has nowhere to live without a registry to enforce it. Until the hosted registry ships, trust tiers are advisory.

### Reversibility

Mostly forward-compatible. The hosted registry will be a separate codebase that exposes the same logical surface as `AgentRegistry`. The in-process registry will keep working for private deployments and small projects. A hybrid mode (in-process registry that mirrors a hosted upstream) is the natural shape; nothing in v0.3 precludes it.

## References

- [`AgentRegistry`](/docs/sdk-reference/registry)
- [Roadmap](/docs/roadmap) — hosted registry work
- [Security model](/docs/security) — trust tier model awaiting a registry to enforce it
