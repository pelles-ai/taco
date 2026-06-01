---
title: "SPEC-004 — Security & Authentication"
description: Normative requirements for TACO authentication, the construction-shaped scope taxonomy, Token Exchange between agents, and trust tiers.
sidebar_position: 4
---

# SPEC-004 — Security & Authentication

**Status:** Stable
**Version:** 1.0
**Date:** 2026-05-25

## 1. Introduction

This specification defines TACO's security model: authentication schemes, the construction-shaped OAuth scope taxonomy, Token Exchange behavior between agents, and trust tiers.

The key words **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 2. Authentication

TACO inherits A2A's authentication model. An agent **MAY** require authentication on its endpoints. When it does, the agent's Agent Card **SHALL** advertise the authentication requirements in `securitySchemes` and `security[]` per the A2A specification.

### 2.1 Supported scheme types

A TACO agent's `securitySchemes` **MAY** use any A2A-supported scheme type:

- `apiKey`
- `http` (typically with `bearer` for JWT)
- `oauth2`
- `openIdConnect`
- `mutualTLS`

The agent **SHALL** correctly implement validation for whichever scheme(s) it advertises. Advertising a scheme without enforcing it is non-conformant.

### 2.2 Consistency

If `security[]` is present, every named scheme referenced in `security[]` **SHALL** have a matching definition in `securitySchemes`. Mismatched declarations are non-conformant (the conformance runner — see [SPEC-005](./SPEC-005-conformance) — checks this).

### 2.3 The well-known path

Per [SPEC-001 §2.2](./SPEC-001-agent-cards), the `/.well-known/agent-card.json` path **SHALL** be reachable without authentication. Discovery is public; usage is what gets gated.

## 3. The construction scope taxonomy

TACO defines a typed OAuth scope vocabulary for multi-organizational construction workflows. When an agent advertises OAuth-based authentication, the scopes referenced **SHOULD** follow this taxonomy.

### 3.1 Format

A TACO scope **SHALL** match the format:

```
taco:{dimension}:{value}[:{action}]
```

- `dimension` is one of: `trade`, `task`, `csi`, `project`, `registry`
- `value` is a construction-domain identifier
- `action` (optional) is one of: `read`, `write`, `admin`. When omitted, the default action **SHALL** be `write`.

### 3.2 Defined dimensions

| Dimension | Value | Example | Meaning |
|----------|-------|---------|---------|
| `trade` | trade identifier from [SPEC-001 §5.1](./SPEC-001-agent-cards) | `taco:trade:mechanical` | Access to mechanical-trade workflows |
| `task` | task type from [SPEC-002](./SPEC-002-task-types) | `taco:task:estimate` | Permission to submit estimate tasks |
| `csi` | 2-digit MasterFormat division | `taco:csi:23` | Access scoped to a CSI division |
| `project` | project identifier (deployment-defined) | `taco:project:PRJ-0042:write` | Write access to a specific project |
| `registry` | predefined value: `read` or `publish` | `taco:registry:read` | Discover agents in the registry |

### 3.3 Scope combination rules

- **Scopes are additive.** A token bearing both `taco:trade:mechanical` and `taco:task:estimate` is permitted to submit estimate tasks against mechanical-trade agents.
- **Project scopes require a task or trade scope.** A token bearing only `taco:project:PRJ-0042:write` (no `taco:task:*` or `taco:trade:*`) **SHALL NOT** be considered sufficient to perform work — project scope is qualified by task or trade scope.
- **Action narrows authority.** `:read` permits read-only operations; `:write` permits state-changing operations; `:admin` permits configuration mutations.

### 3.4 Validation

Agents that accept OAuth tokens **SHALL** validate that the token's scopes are sufficient for the requested operation per the agent's published authorization model. Agents **SHALL NOT** accept tokens whose project scope mismatches the project ID in the payload (see §5).

## 4. Token Exchange between agents

When an agent calls a downstream agent in a multi-hop workflow, the calling agent **SHOULD** perform [RFC 8693 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693) to narrow the token before the downstream call.

### 4.1 No token passthrough

A calling agent **SHALL NOT** forward its received token verbatim to a downstream agent when the downstream agent has a different scope of authority. Token passthrough across trust boundaries is non-conformant.

### 4.2 Narrowing

The exchanged token issued for the downstream call **SHALL** contain only the scopes that the downstream agent legitimately requires. Examples:

- GC orchestrator receives `taco:trade:mechanical taco:project:PRJ-0042:write`
- Before calling the estimator, narrows to `taco:task:estimate taco:project:PRJ-0042:write`
- Before calling the supplier, narrows to `taco:task:material-procurement taco:project:PRJ-0042:write`

Each downstream agent thus holds only the authority required for its own task, on the specific project.

### 4.3 Audit

Implementations **SHOULD** preserve the chain of token exchanges in an audit log: the original token identifier, the exchanged token identifier, the downstream agent URL, and the timestamp. This audit trail is the defense-in-depth complement to scope narrowing.

## 5. Project-scope binding

Agents handling project-scoped tasks **SHALL** validate that the project scope in the bearer token matches the project identifier in the request payload:

```
token.scope contains "taco:project:PRJ-0042:write"
payload.projectId === "PRJ-0042"
→ permitted

token.scope contains "taco:project:PRJ-0099:write"
payload.projectId === "PRJ-0042"
→ rejected (cross-project assertion)
```

Cross-project requests **SHALL** be rejected with an authentication error (HTTP 403 or equivalent JSON-RPC error) rather than silently processed.

## 6. mTLS, PKCE, Device Code

For deployments using non-OAuth-bearer authentication, TACO agents **MAY** advertise additional capabilities on `x-construction.security`:

| Field | Type | Meaning |
|------|------|------|
| `mtlsSupported` | boolean | Agent supports mutual TLS client cert authentication |
| `pkceRequired` | boolean | OAuth Authorization Code flow requires PKCE ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)) |
| `deviceCodeSupported` | boolean | OAuth Device Authorization Grant ([RFC 8628](https://datatracker.ietf.org/doc/html/rfc8628)) supported |

These advertisements let registries and orchestrators filter agents by auth modality without parsing the full `securitySchemes` block.

## 7. Trust tiers

The TACO registry model defines three trust tiers (see [`security.md`](../security)):

| Tier | Label | Verification |
|------|-------|--------------|
| 0 | Unverified | Self-published; no claims validated |
| 1 | Org Verified | Domain ownership verified by the registry |
| 2 | Cert Attested | Compliance certification (SOC2, ISO 27001, etc.) confirmed by the registry |

The agent **MAY** declare its trust tier in `x-construction.security.trustTier`. Registries **SHALL** validate any tier-1 or tier-2 claim before publishing the agent at that tier; unverified self-claims **SHALL** be displayed at tier 0.

## 8. Companion material

- [Security model (prose)](../security)
- [ADR-0003 — Construction-shaped scopes](../decisions/construction-shaped-scopes)
- [Best Practices on auth](../best-practices#security-in-production)
- [Pitfalls #6](../pitfalls) — auth in dev vs auth in prod
