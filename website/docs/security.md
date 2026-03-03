---
sidebar_position: 6
title: Security
---

# Security

Security in TACO builds on A2A's native authentication model and adds construction-specific authorization concepts: project-scoped credentials, trade-level permission boundaries, and a registry trust model for verified agents.

:::note
This document defines the TACO security model. Implementation is optional for sandbox deployments and recommended for production multi-company deployments.
:::

**Visual references:** [Authentication Flow](pathname:///taco/taco-auth-flow.html) | [Security Model Diagram](pathname:///taco/taco-security-model.html)

## Overview

TACO inherits the A2A protocol's authentication framework without modification. A2A defines five authentication scheme types (`apiKey`, `http`, `oauth2`, `openIdConnect`, `mutualTLS`), JWS-signed Agent Cards for tamper detection, and OAuth 2.0 Token Exchange ([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693)) as the recommended delegation mechanism.

TACO adds three things on top:

1. A **scope taxonomy** that maps OAuth scopes to construction concepts — trades, CSI divisions, project IDs, and task types
2. A **registry trust model** with three verification tiers
3. A `security` sub-object in the [`x-construction`](./agent-card-extensions) extension

## Deployment Scenarios

| Scenario | Recommended Scheme | Notes |
|----------|-------------------|-------|
| Open / sandbox | None, or `apiKey` | For development and public demo agents |
| Single-company internal | `http` with `bearer` | JWT issued by internal IdP |
| GC-to-subcontractor | `oauth2` with Token Exchange | GC exchanges token for narrower scope before calling sub's agent |
| Multi-company project | `oauth2` + `openIdConnect` | Federated identity; project membership determines auth |
| High-assurance / regulated | `mutualTLS` | Certificate pinning, for federal/DoD/critical infrastructure |

## Scope Taxonomy

TACO defines a scope naming convention that makes construction authorization semantics machine-readable:

```
taco:{dimension}:{value}[:{action}]
```

- `dimension`: one of `trade`, `task`, `csi`, `project`, `registry`
- `value`: a construction-domain identifier
- `action` (optional): `read`, `write`, or `admin`. Defaults to `write` if omitted.

### Scope Reference

| Scope Pattern | Meaning | Example |
|---------------|---------|---------|
| `taco:trade:{trade}` | Access to all workflows for a trade | `taco:trade:mechanical` |
| `taco:task:{taskType}` | Permission to submit a specific task type | `taco:task:estimate` |
| `taco:csi:{division}` | Access scoped to a CSI division | `taco:csi:23` |
| `taco:project:{id}:read` | Read access to a project's artifacts | `taco:project:PRJ-0042:read` |
| `taco:project:{id}:write` | Write access on a specific project | `taco:project:PRJ-0042:write` |
| `taco:registry:read` | Discover agents in the registry | `taco:registry:read` |
| `taco:registry:publish` | Publish/update an Agent Card | `taco:registry:publish` |

### Scope Combination Rules

1. **Scopes are additive.** `taco:trade:mechanical` + `taco:task:estimate` = only estimate tasks on mechanical agents.
2. **Project scopes require a task or trade scope.** A project scope alone is not meaningful.
3. **Agents validate scope against task type.** An agent advertising `taco:task:takeoff` rejects tokens that only carry `taco:task:estimate`.

## Token Delegation

Construction workflows commonly involve chains of three or more agents from different organizations. Each hop should narrow the token's authority using OAuth 2.0 Token Exchange ([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693)).

### Example: GC → Estimator → Supplier

1. GC orchestrator authenticates → receives `taco:trade:mechanical taco:project:PRJ-0042:write`
2. Exchanges for `taco:task:estimate taco:project:PRJ-0042:write` before calling estimator
3. Estimator exchanges for `taco:task:material-procurement taco:project:PRJ-0042:write` before calling supplier
4. Each agent only holds authority for its own task on this specific project

```
POST /oauth/token HTTP/1.1
Host: auth.buildright.io

grant_type=urn:ietf:params:oauth:grant-type:token-exchange
&subject_token=<orchestrator_token>
&subject_token_type=urn:ietf:params:oauth:token-type:access_token
&scope=taco:task:estimate+taco:project:PRJ-0042:write
&audience=https://api.mech-estimating.io/a2a
```

**Token passthrough prohibition:** Agents must not forward their received token to downstream agents. Always perform a Token Exchange for each hop.

## Registry Trust Model

| Tier | Label | How Achieved | What It Means |
|------|-------|-------------|---------------|
| 0 | Unverified | Self-published | Agent Card indexed; no claims validated |
| 1 | Org Verified | Domain ownership verification | Agent URL's domain belongs to a verified org |
| 2 | Cert Attested | Certification verified by registry | SOC2, ISO27001, etc. confirmed, not self-declared |

## Agent Card Security Declaration

```json
{
  "securitySchemes": {
    "tacoOAuth": {
      "type": "oauth2",
      "flows": {
        "clientCredentials": {
          "tokenUrl": "https://auth.buildright.io/oauth/token",
          "scopes": {
            "taco:trade:mechanical": "Access mechanical trade workflows",
            "taco:task:estimate": "Submit estimate tasks"
          }
        }
      }
    }
  },
  "security": [
    { "tacoOAuth": ["taco:trade:mechanical", "taco:task:estimate"] }
  ],
  "x-construction": {
    "security": {
      "trustTier": 1,
      "scopesOffered": ["taco:trade:mechanical", "taco:task:estimate"],
      "projectScoped": true,
      "delegationSupported": true
    }
  }
}
```

## Implementation Checklist

For production deployments:

1. Choose the auth scheme for your deployment scenario
2. Declare `securitySchemes` and `security` in the Agent Card
3. Define TACO scopes for each task type and trade
4. Validate incoming bearer tokens on every `message/send` request
5. Do not pass received tokens downstream — use Token Exchange
6. If project-scoped, verify the token carries a matching `taco:project:{id}` scope
7. Submit to the registry for trust tier elevation after certification
