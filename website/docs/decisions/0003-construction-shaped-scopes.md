---
title: ADR-0003 — Construction-shaped OAuth scope taxonomy
description: Why TACO defines its own OAuth scope shape (`taco:trade:mechanical`, `taco:project:PRJ-0042:write`) rather than reusing generic scope conventions.
sidebar_position: 3
---

# ADR-0003 — Construction-shaped OAuth scope taxonomy

**Status:** Accepted
**Date:** 2026-03-03

## Context

Multi-agent construction workflows have a real authorization problem. A GC orchestrator calls a mechanical estimator, which calls a supplier — three companies, three trust boundaries, three different things each agent should be allowed to do.

Generic OAuth tells us *how* to express scopes (`scope=read write admin` separated by spaces) but says nothing about *what* the scopes mean. Construction software has historically solved this with platform-specific scope strings (`procore:project:read`, `acc:rfi:write`), which makes cross-vendor delegation impossible — each platform's tokens don't translate.

The question: define a construction-meaningful scope vocabulary, or punt to "use whatever scopes your auth server emits"?

## Decision

TACO defines a typed scope taxonomy: `taco:{dimension}:{value}[:{action}]`. The dimensions are stable (`trade`, `task`, `csi`, `project`, `registry`), the values are construction-domain identifiers (`mechanical`, `estimate`, `23`, `PRJ-0042`), and the optional action narrows write access (`read`, `write`, `admin`; defaults to `write` if omitted).

Examples:
- `taco:trade:mechanical` — access to mechanical-trade workflows
- `taco:task:estimate` — permission to submit estimate tasks
- `taco:csi:23` — access scoped to a CSI division
- `taco:project:PRJ-0042:write` — write access on a specific project

Scopes compose additively. An agent that holds `taco:trade:mechanical` and `taco:task:estimate` can submit estimate tasks against mechanical-trade agents. `taco:project:PRJ-0042` alone is meaningless without a task or trade scope.

For delegation across hops, TACO mandates [RFC 8693 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693): every hop narrows the token before calling downstream. No agent ever forwards a token wider than it needs.

## Alternatives considered

### "Use whatever scopes your auth server emits"

Pros: zero spec surface area, every vendor keeps what they have.

Cons:
- Cross-vendor delegation is impossible. A GC orchestrator that holds a Procore token can't narrow it for a non-Procore supplier agent.
- Registry filtering by scope becomes nonsensical (every agent's scopes mean different things).
- The whole point of TACO — that any TACO-compatible agent can be substituted for any other — collapses when scopes are vendor-specific.

### Coarse scopes (`taco:read`, `taco:write`)

Pros: simple, easy to issue, hard to get wrong.

Cons: lose all the structure we'd build the rest of the protocol around. Project-scoped delegation (the most-asked-for feature in early conversations) becomes impossible. Trust boundaries collapse to per-agent rather than per-project.

### Resource-server-specific scopes (`procore:projects/PRJ-0042:read`)

This is what the construction software space does today. The pattern works *within* a vendor and falls apart *across* vendors. Adopting it would lock us into the same fragmentation we're trying to solve.

## Consequences

### Positive

- Token Exchange becomes meaningful. A GC token holding `taco:trade:mechanical taco:project:PRJ-0042:write` can be narrowed to `taco:task:estimate taco:project:PRJ-0042:write` before calling the estimator, then to `taco:task:material-procurement taco:project:PRJ-0042:write` before calling the supplier. Each hop holds only what it needs.
- The registry can filter agents by scope coverage (`find me agents that accept tokens with taco:trade:electrical`).
- Auditing becomes possible. A project-scoped token narrowed at every hop produces an audit trail where each agent's exact authority is recorded.
- Trust tiers become composable. Combining `taco:registry:read` with project scopes lets owners enforce "only cert-attested agents can read this project's artifacts."

### Negative

- Auth servers have to be configured to issue TACO-shaped scopes. We provide a taxonomy spec, not a token issuer. Operators need to configure their IdP (Auth0, Okta, Keycloak, in-house) to emit these scopes — non-trivial.
- The taxonomy is opinionated. Edge cases ("what scope does a value-engineering agent need?") have to be decided in a spec working group, which means RFCs and slower iteration than per-vendor extension.
- Scope-string parsing has to be implemented per language. We provide it for Python; other-language SDKs need to mirror it.

### Reversibility

Hard to reverse without breaking deployed agents. The scope vocabulary is mentioned in deployment guides, embedded in token issuance pipelines, and shows up in audit logs. Migration would require coordinated changes across the ecosystem. We treat the taxonomy as a quasi-permanent commitment.

## References

- [Security model](/docs/security)
- [RFC 8693 — OAuth 2.0 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693)
- [`SecurityExt`](/docs/sdk-reference/agent-cards) — the agent card declaration
