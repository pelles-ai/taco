---
title: "SPEC-004 — Security & Authentication"
description: Normative requirements for TACO authentication, the construction-shaped scope taxonomy, Token Exchange between agents, and trust tiers.
sidebar_position: 4
---

# SPEC-004 — Security & Authentication

**Status:** Provisional
**Version:** 0.3
**Date:** 2026-05-25

## 1. Introduction

This specification defines TACO's security model: authentication schemes, the construction-shaped OAuth scope taxonomy, Token Exchange behavior between agents, and trust tiers.

The key words **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 2. Authentication

TACO inherits A2A's authentication model. An agent **MAY** require authentication on its endpoints. When it does, the agent's Agent Card **SHALL** advertise the authentication requirements in `securitySchemes` and `security[]` per the A2A specification.

:::note Reference SDK status
The 0.3 reference SDK does not yet implement this section. Its `AgentCard` model has no `securitySchemes` or `security` fields, so they are not included in the card it serves, and `A2AServer` does not authenticate requests to the JSON-RPC endpoint (only the optional `/admin/skills` endpoints take a bearer token). Agents that require authentication today enforce it outside the SDK, for example in middleware or a gateway in front of the agent.
:::

### 2.1 Supported scheme types

A TACO agent's `securitySchemes` **MAY** use any A2A-supported scheme type:

- `apiKey`
- `http` (typically with `bearer` for JWT)
- `oauth2`
- `openIdConnect`
- `mutualTLS`

The agent **SHALL** correctly implement validation for whichever scheme(s) it advertises. Advertising a scheme without enforcing it is non-conformant.

### 2.2 Consistency

If `security[]` is present, every named scheme referenced in `security[]` **SHALL** have a matching definition in `securitySchemes`. Mismatched declarations are non-conformant. This is one of the checks in [SPEC-005](./SPEC-005-conformance); a hosted conformance runner that automates them is planned, and until then `taco discover <url>` prints the full card JSON, including these fields, for manual review.

### 2.3 The well-known path

Per [SPEC-001 §2.1](./SPEC-001-agent-cards), the `/.well-known/agent-card.json` path **SHALL** be reachable without authentication. Discovery is public; usage is what gets gated.

## 3. The construction scope taxonomy

TACO defines a typed OAuth scope vocabulary for multi-organizational construction workflows. When an agent advertises OAuth-based authentication, the scopes referenced **SHOULD** follow this taxonomy.

### 3.1 Format

A TACO scope **SHALL** match the format:

```
taco:{dimension}:{value}[:{action}]
```

- `dimension` is one of: `trade`, `task`, `csi`, `project`, `registry`
- `value` is a construction-domain identifier
- `action` (optional) is one of: `read`, `write`, `admin`. When omitted, the action defaults to `write`.

The format, dimensions, actions, and default above are those defined in the canonical [`spec/security.md`](https://github.com/pelles-ai/taco/blob/main/spec/security.md).

### 3.2 Defined dimensions

| Dimension | Value | Example | Meaning |
|----------|-------|---------|---------|
| `trade` | trade identifier from [SPEC-001 §5.1](./SPEC-001-agent-cards) | `taco:trade:mechanical` | Access to mechanical-trade workflows |
| `task` | task type from [SPEC-002](./SPEC-002-task-types) | `taco:task:estimate` | Permission to submit estimate tasks |
| `csi` | 2-digit MasterFormat division | `taco:csi:23` | Access scoped to a CSI division |
| `project` | project identifier (deployment-defined; should match the payload's `projectId`) | `taco:project:PRJ-0042:read`, `taco:project:PRJ-0042:write` | Read access to a project's artifacts; write (task submission) access on a project |
| `registry` | predefined value: `read` or `publish` | `taco:registry:read`, `taco:registry:publish` | Discover agents in the registry; publish or update an Agent Card in the registry |

### 3.3 Scope combination rules

- **Scopes are additive.** A token bearing both `taco:trade:mechanical` and `taco:task:estimate` is permitted to submit estimate tasks against mechanical-trade agents.
- **Project scopes require a task or trade scope.** A token bearing only `taco:project:PRJ-0042:write` (no `taco:task:*` or `taco:trade:*`) **SHALL NOT** be considered sufficient to perform work — project scope is qualified by task or trade scope.
- **Agents validate scope against task type.** An agent **SHOULD** reject a token whose scopes do not include the task type being requested; for example, an agent advertising `taco:task:takeoff` should reject a token that only carries `taco:task:estimate`.
- **Action qualifies access.** For project scopes, `:read` grants read access to the project's artifacts and `:write` grants task submission. `spec/security.md` lists `admin` as an action but does not yet define its meaning.

### 3.4 Validation

Agents that accept OAuth tokens **SHALL** validate that the token's scopes are sufficient for the requested operation per the agent's published authorization model. Agents **SHALL NOT** accept tokens whose project scope mismatches the project ID in the payload (see §5).

The reference SDK does not parse or enforce TACO scopes; validation is the agent's responsibility. `x-construction.security.scopesOffered` is informational, and the authoritative scope declaration is the Agent Card's `securitySchemes`.

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

Cross-project requests **SHALL** be rejected with an authorization error (HTTP 403 or equivalent JSON-RPC error) rather than silently processed. Per `spec/security.md`, a request with no token is rejected with HTTP 401, and a token that lacks a required scope with HTTP 403.

## 6. mTLS, PKCE, Device Code (planned)

A2A v1 formalizes the `mutualTLS` scheme, adds PKCE on the OAuth Authorization Code flow ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)), and adds the Device Authorization Grant ([RFC 8628](https://datatracker.ietf.org/doc/html/rfc8628)). Surfacing these on `x-construction.security` is planned (`feat/mtls-pkce-device-code-security` in [`sdk/V1_MIGRATION.md`](https://github.com/pelles-ai/taco/blob/main/sdk/V1_MIGRATION.md)) but not yet defined.

In this version, `x-construction.security` defines exactly five fields: `trustTier`, `scopesOffered`, `projectScoped`, `delegationSupported`, and `extendedCardUrl` (see [`spec/security.md`](https://github.com/pelles-ai/taco/blob/main/spec/security.md)). Agents **SHALL** advertise mTLS and OAuth flow details through the standard A2A `securitySchemes` block.

## 7. Trust tiers

The TACO registry model defines three trust tiers (see [`security.md`](../security)):

| Tier | Label | Verification |
|------|-------|--------------|
| 0 | Unverified | Self-published; no claims validated |
| 1 | Org Verified | Domain ownership verified by the registry |
| 2 | Cert Attested | Compliance certification (SOC2, ISO 27001, etc.) confirmed by the registry |

The `x-construction.security.trustTier` field is assigned by the registry. Agents **SHOULD NOT** self-declare a tier they have not achieved. A registry that assigns trust tiers **SHALL** validate any tier-1 or tier-2 claim before publishing the agent at that tier; unverified self-claims **SHALL** be displayed at tier 0.

The reference SDK's in-process `AgentRegistry` does not verify, assign, or filter by trust tier; until a hosted registry exists, trust tiers are advisory (see [ADR-0005](../decisions/in-memory-registry-first)).

## 8. Companion material

- [Security model (prose)](../security)
- [ADR-0003 — Construction-shaped scopes](../decisions/construction-shaped-scopes)
- [Best Practices on auth](../best-practices#security-in-production)
- [Pitfalls #6](../pitfalls) — auth in dev vs auth in prod
