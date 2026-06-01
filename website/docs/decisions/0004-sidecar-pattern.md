---
title: ADR-0004 — Sidecar pattern for platform integration
description: Why TACO recommends a separate-process sidecar for wrapping existing construction platforms rather than asking platforms to add native A2A endpoints.
sidebar_position: 4
---

# ADR-0004 — Sidecar pattern for platform integration

**Status:** Accepted
**Date:** 2026-03-10

## Context

Most of the construction software market is mature platforms with established APIs — Procore, ACC, Bluebeam, Trimble, Smartsheet, PlanGrid (now Autodesk), and dozens of trade-specific tools. For TACO to matter beyond greenfield agents, these platforms need to participate in the ecosystem.

Two paths exist:

1. **Native integration.** Convince each platform vendor to add A2A endpoints to their own server (`/.well-known/agent-card.json`, JSON-RPC at `/`, etc.).
2. **Sidecar.** Run a small separate process that translates A2A requests into the platform's existing API calls and shapes responses into TACO artifacts.

The decision shapes adoption velocity, not just architecture.

## Decision

The recommended pattern for integrating an existing construction platform is the **sidecar**: a small, separately-deployed process — usually a Python app using `taco-agent` — that exposes the platform's capabilities as TACO agent skills by calling the platform's existing REST/SOAP/GraphQL API internally.

The sidecar advertises itself in the registry with the platform identifier (`integrations: ["procore"]`); downstream agents discover it the same way they discover a native TACO agent. The platform itself stays untouched.

Native A2A endpoints on the platform side are welcomed when vendors want them, but the sidecar is the path-of-least-resistance default.

## Alternatives considered

### Native integration only

Pros: clean architecture, no extra process, no translation layer.

Cons:
- Adoption requires every platform vendor to ship A2A support. The market doesn't move at that pace; we'd be talking to vendor product teams for years before getting a single integration.
- Even cooperative vendors prioritize their own roadmap over external protocols. Asking for A2A endpoints is a feature request that lands behind everything they're already shipping.
- Some platforms (Procore, ACC) have plugin/SDK ecosystems; a sidecar fits naturally there. Others (older trade tools) only expose CSV exports — but a sidecar can wrap *any* surface.

### Reverse proxy / API gateway

Pros: even less invasive than a sidecar, just rewrites HTTP requests.

Cons:
- Translating between A2A's JSON-RPC + task lifecycle and arbitrary REST is not "rewrite the URL." It needs business logic per skill.
- Auth translation (TACO scopes → platform-specific tokens) is genuinely complex; a reverse proxy isn't the right tool.
- Long-running tasks (a 30-minute submittal review) need state-keeping the proxy doesn't have.

### Platform-side plugin

Pros: zero deployment overhead for the integrator, runs in the platform's own runtime.

Cons:
- Each platform's plugin model is different and limiting. Not all of them allow arbitrary HTTP servers, async operations, or the runtime dependencies (`taco-agent`, `httpx`) we'd need.
- The plugin runs inside the platform's permission model and can't easily federate auth.

## Consequences

### Positive

- A single team can add TACO support for any platform in days, not the months a vendor-side feature request takes.
- The sidecar repository is small and focused. Anyone can read it end-to-end in a sitting.
- Operational isolation: the sidecar fails independently of the platform. A bug in the sidecar can't crash Procore.
- Auth flexibility: the sidecar holds platform credentials (service accounts, app installation tokens) and translates TACO scopes into platform-specific authority. Owners can rotate the sidecar's credentials without touching their TACO tokens.
- A vendor-native A2A path can land later without breaking sidecars — agents calling either one see the same Agent Card shape.

### Negative

- Two processes to operate (the platform itself + the sidecar). Some teams hate this.
- An extra HTTP hop per call. Latency overhead is small (the sidecar is local to the platform) but real.
- The sidecar holds long-lived platform credentials. Operational security has to take this seriously — secret rotation, network isolation, audit logging.
- A buggy sidecar can produce typed-but-wrong TACO artifacts. The platform doesn't know its data is being reshaped.
- We have to write and maintain the sidecar pattern docs; vendors don't.

### Reversibility

Fully reversible. The sidecar pattern is a *recommendation*, not a requirement. If a vendor ships native A2A endpoints, the registry treats them identically. Operators can swap their sidecar deployment for a native endpoint with zero change to the calling agents.

## References

- [Integrate Your Platform guide](/docs/getting-started/integrate-platform)
- [For Platform Vendors landing](/for/platform-vendor)
