---
sidebar_position: 6
title: Security
description: TACO security model — A2A auth plus project-scoped credentials, trade-level boundaries, OAuth scopes, and registry trust tiers — and how to implement it with the Python SDK.
---

# Security

Security in TACO builds on A2A's native authentication model and adds construction-specific authorization concepts: project-scoped credentials, trade-level permission boundaries, and a registry trust model for verified agents.

:::note
This document defines the TACO security model. Implementation is optional for sandbox deployments and recommended for production multi-company deployments. It follows [`spec/security.md`](https://github.com/pelles-ai/taco/blob/main/spec/security.md); the normative requirements are in [SPEC-004](/docs/spec/SPEC-004-security). [Implementing it with the SDK](#implementing-it-with-the-sdk) shows the Python SDK side.
:::

**Visual references:** [Authentication Flow](pathname:///taco-auth-flow.html) | [Security Model Diagram](pathname:///taco-security-model.html)

## Overview

TACO inherits the A2A protocol's authentication framework without modification. A2A defines five authentication scheme types (`apiKey`, `http`, `oauth2`, `openIdConnect`, `mutualTLS`), JWS-signed Agent Cards for tamper detection, extended Agent Cards for progressive capability disclosure, and OAuth 2.0 Token Exchange ([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693)) as the recommended delegation mechanism. Credentials always travel in HTTP headers, never inside JSON-RPC payloads.

TACO adds three things on top:

1. A **scope taxonomy** that maps OAuth scopes to construction concepts — trades, CSI divisions, project IDs, and task types
2. A **registry trust model** with three verification tiers
3. A `security` sub-object in the [`x-construction`](./agent-card-extensions) extension

If an agent also exposes MCP tools for people (for example a GC employee querying an agent through chat), those interactions use OAuth 2.1 per the MCP specification, alongside A2A agent-to-agent auth. This page covers agent-to-agent security only.

## Deployment Scenarios

TACO agents declare authentication with the standard A2A `securitySchemes` and `security` fields. TACO adds no new scheme types; it recommends which of A2A's five to use:

| Scenario | Recommended Scheme | Notes |
|----------|-------------------|-------|
| Open / sandbox | None, or `apiKey` | For development and public demo agents |
| Single-company internal | `http` with `bearer` | JWT issued by internal IdP; scoped to trade and task types |
| GC-to-subcontractor | `oauth2` with Token Exchange | GC exchanges its token for a narrower one before calling a sub's agent |
| Multi-company project | `oauth2` + `openIdConnect` | Federated identity; project membership determines auth |
| High-assurance / regulated | `mutualTLS` | Certificate pinning, often with Bearer; for federal, DoD and critical infrastructure |

## Agent Card Security Declaration

An agent that requires authentication declares it in the card's `securitySchemes` and `security` fields, next to the `x-construction` extension:

```json
{
  "name": "BuildRight Mechanical Estimating Agent",
  "url": "https://api.buildright.io/a2a",
  "version": "1.0.0",
  "securitySchemes": {
    "tacoOAuth": {
      "type": "oauth2",
      "flows": {
        "clientCredentials": {
          "tokenUrl": "https://auth.buildright.io/oauth/token",
          "scopes": {
            "taco:trade:mechanical": "Access mechanical trade workflows",
            "taco:task:estimate": "Submit estimate tasks",
            "taco:task:value-engineering": "Submit value engineering tasks"
          }
        }
      }
    }
  },
  "security": [
    { "tacoOAuth": ["taco:trade:mechanical", "taco:task:estimate"] }
  ],
  "x-construction": {
    "trade": "mechanical",
    "csiDivisions": ["22", "23"],
    "certifications": ["SOC2"],
    "security": {
      "trustTier": 1,
      "scopesOffered": ["taco:trade:mechanical", "taco:task:estimate", "taco:task:value-engineering"],
      "projectScoped": true,
      "delegationSupported": false
    }
  }
}
```

The `securitySchemes` key (`tacoOAuth`) is a local name. Use a descriptive one that includes the scheme type. Every name used in `security` must be defined in `securitySchemes`; the [conformance check](/conformance) tests this.

## Scope Taxonomy

TACO defines a scope naming convention that makes construction authorization semantics machine-readable. Scopes are declared in `securitySchemes`, requested by orchestrators when they get a token, and checked by agents on incoming requests.

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

`{trade}` values are the [`trade` values](./agent-card-extensions), `{taskType}` values are the [task types](./task-types), and the `{id}` in a project scope matches the `projectId` used in TACO data schemas.

### Scope Combination Rules

1. **Scopes are additive.** `taco:trade:mechanical` + `taco:task:estimate` = only estimate tasks on mechanical agents.
2. **Project scopes require a task or trade scope.** A project scope alone is not meaningful: it gates which project's data is accessible, while trade and task scopes gate what actions are permitted.
3. **Agents validate scope against task type.** An agent advertising `taco:task:takeoff` rejects tokens that only carry `taco:task:estimate`.

## Token Delegation

Construction workflows commonly involve chains of three or more agents from different organizations. Each hop should narrow the token's authority using OAuth 2.0 Token Exchange ([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693)): the calling agent exchanges its token for one with reduced scope, a shorter lifetime and an audience locked to the next agent.

### Example: GC → Estimator → Supplier

1. GC orchestrator authenticates with `client_credentials` → receives `taco:trade:mechanical taco:project:PRJ-0042:write`
2. Exchanges it for `taco:task:estimate taco:project:PRJ-0042:write` before calling the estimator
3. The estimator validates the narrow token, runs the estimate and returns `estimate-v1`
4. If the estimator needs a supplier quote, it exchanges again for `taco:task:material-procurement taco:project:PRJ-0042:write`
5. Each agent only holds authority for its own task on this specific project

```
POST /oauth/token HTTP/1.1
Host: auth.buildright.io
Content-Type: application/x-www-form-urlencoded

grant_type=urn:ietf:params:oauth:grant-type:token-exchange
&subject_token=<orchestrator_token>
&subject_token_type=urn:ietf:params:oauth:token-type:access_token
&scope=taco:task:estimate+taco:project:PRJ-0042:write
&audience=https://api.mech-estimating.io/a2a
```

### Token Passthrough Prohibition

Agents must not forward the token they received to downstream agents. This mirrors the MCP specification's stance on user tokens, and in TACO's multi-company setting it also stops a compromised agent from escalating its authority by reusing its caller's token with a different downstream agent. Always perform a Token Exchange to get a new, appropriately scoped token for each hop.

## Registry Trust Model

The registry is how orchestrators discover agents, and trust in a discovered agent depends on how it was listed:

| Tier | Label | How Achieved | What It Means |
|------|-------|-------------|---------------|
| 0 | Unverified | Self-published | Agent Card indexed; no claims validated. Fine for development and sandboxes. |
| 1 | Org Verified | Domain ownership verification (DNS TXT record or HTTPS challenge on the `url` domain) | Agent URL's domain belongs to a verified org; certification claims are still self-declared |
| 2 | Cert Attested | Certification verified by registry | SOC2, ISO27001, etc. confirmed, not self-declared |

`trustTier` in `x-construction.security` is assigned by the registry. Agents should not self-declare a tier they have not achieved. The `certifications` list in `x-construction` is self-declared; `trustTier` is registry-verified. The SDK's in-process `AgentRegistry` does not verify or assign tiers, so treat a tier on a card as a claim until a registry has validated it.

### JWS-Signed Agent Cards

A2A supports signing Agent Cards with JSON Web Signature ([RFC 7515](https://datatracker.ietf.org/doc/html/rfc7515)). TACO recommends that Tier 1 and Tier 2 agents sign their cards, so a card cannot be altered on its way through intermediary registries or brokers. A signature proves the card was not modified in transit; it does not by itself establish a trust tier.

### Registry Queries and Auth

Querying a registry for agents requires the `taco:registry:read` scope. The registry returns full Agent Cards; the orchestrator evaluates the trust tier and decides whether to proceed. Higher-tier agents may rank higher, but the registry does not filter out lower tiers unless the query asks for a minimum tier.

## x-construction Security Extension

The `security` sub-object of the top-level [`x-construction`](./agent-card-extensions) extension carries construction-specific security metadata that supplements `securitySchemes`:

```json
{
  "x-construction": {
    "trade": "mechanical",
    "csiDivisions": ["22", "23"],
    "security": {
      "trustTier": 1,
      "scopesOffered": ["taco:trade:mechanical", "taco:task:estimate"],
      "projectScoped": true,
      "delegationSupported": true,
      "extendedCardUrl": "https://api.buildright.io/a2a/agent-extended.json"
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trustTier` | integer | No | Registry trust tier: `0` (unverified), `1` (org verified), `2` (cert attested). Assigned by the registry; agents should not self-declare a tier they have not achieved. |
| `scopesOffered` | string[] | No | TACO scopes this agent accepts on incoming requests, surfaced for registry filtering without an OAuth discovery flow. Informational: `securitySchemes` remains the authoritative declaration. |
| `projectScoped` | boolean | No | If `true`, the agent requires a `taco:project:{id}` scope in addition to task/trade scopes, so orchestrators know in advance they need a project-specific token. |
| `delegationSupported` | boolean | No | If `true`, the agent can take part in Token Exchange (RFC 8693) sub-delegation chains. |
| `extendedCardUrl` | string | No | URL of the extended Agent Card (per the A2A spec) that reveals more capabilities after authentication. |

## Construction Authorization Concepts

### Trade Boundaries

Trade scopes (`taco:trade:{trade}`) follow how construction projects are organized. A mechanical subcontractor's agent should only accept tasks for mechanical workflows. A multi-trade GC orchestrator may hold several trade scopes, but passes only the relevant one to each downstream agent through Token Exchange.

### Project Membership

A typical commercial project has three levels of project access, all expressible by combining scopes:

1. **Project owner / GC** — write access across trades (`taco:project:{id}:write` + several `taco:trade:*` scopes)
2. **Trade contractors** — write access to their own CSI divisions within the project (`taco:project:{id}:write` + `taco:csi:{div}` + `taco:trade:{trade}`)
3. **Consultants** (architects, engineers) — read access for review tasks (`taco:project:{id}:read`)

### Human-in-the-Loop and Credential Handling

Some task types (notably `rfi-generation`, `submittal-review` and `change-order-analysis`) may pause in the A2A `input-required` state for human review. Credentials an agent holds in memory while a task is paused should not be written to disk, and orchestrators should get fresh tokens when a paused task resumes rather than caching long-lived tokens across the pause.

## Implementation Checklist

For production deployments:

1. Choose the auth scheme for your deployment scenario
2. Declare `securitySchemes` and `security` in the Agent Card
3. Define TACO scopes for each task type and trade; list them in `x-construction.security.scopesOffered`
4. Validate incoming bearer tokens on every `message/send` request: HTTP 401 if there is no valid token, HTTP 403 if it lacks a required scope
5. Do not pass received tokens downstream — use Token Exchange
6. If project-scoped, verify the token carries a `taco:project:{id}` scope matching the payload's `projectId`
7. Submit to the registry for trust tier elevation after certification

## Implementing it with the SDK

The Python SDK covers steps 2, 3 and 4 directly and gives you the hooks for 5 and 6. Token validation itself (JWT signatures, introspection, API keys) is deployment-specific, so you supply it as a function.

### Declare the scheme on the card

`ConstructionAgentCard` takes the A2A `security_schemes` and `security` fields, and the `x-construction.security` block as `construction_security`:

```python
from taco import ConstructionAgentCard, ConstructionSkill, SecurityExt

card = ConstructionAgentCard(
    name="BuildRight Mechanical Estimating Agent",
    url="https://api.buildright.io/a2a",
    trade="mechanical",
    csi_divisions=["22", "23"],
    certifications=["SOC2"],
    skills=[
        ConstructionSkill(id="generate-estimate", task_type="estimate",
                          input_schema="bom-v1", output_schema="estimate-v1"),
    ],
    security_schemes={
        "tacoOAuth": {
            "type": "oauth2",
            "flows": {
                "clientCredentials": {
                    "tokenUrl": "https://auth.buildright.io/oauth/token",
                    "scopes": {"taco:task:estimate": "Submit estimate tasks"},
                },
            },
        },
    },
    security=[{"tacoOAuth": ["taco:task:estimate"]}],
    construction_security=SecurityExt(
        scopes_offered=["taco:task:estimate"],
        project_scoped=True,
    ),
)
```

Leave `trust_tier` unset: the registry assigns it. The served card carries `securitySchemes` and `security`, and `taco inspect <url>` lists them.

### Validate tokens on every task request

Pass a `token_verifier` to `A2AServer`. It receives the bearer token and returns a `taco.AuthContext` (the caller's `subject`, its `scopes`, and any `claims` your handlers need), or `None` to reject the token:

```python
import asyncio

import jwt  # PyJWT, or your IdP's SDK
from taco import A2AServer, AuthContext

jwks = jwt.PyJWKClient("https://auth.buildright.io/.well-known/jwks.json")


async def verify(token: str) -> AuthContext | None:
    try:
        key = await asyncio.to_thread(jwks.get_signing_key_from_jwt, token)
        claims = jwt.decode(token, key.key, algorithms=["RS256"],
                            audience="https://api.buildright.io/a2a")
    except jwt.PyJWTError:
        return None
    return AuthContext(
        subject=claims["sub"],
        scopes=frozenset(claims.get("scope", "").split()),
        claims=claims,
    )


server = A2AServer(card, token_verifier=verify)
```

With a verifier in place, the server:

- answers HTTP 401 when the `Authorization: Bearer` header is missing, when `verify` returns `None`, or when it raises (the exception is logged, not sent);
- answers HTTP 403 when a `message/send` or `message/stream` token lacks `taco:task:<taskType>` for the requested task type (`taco.task_scope("estimate")` builds the string). Pass `require_task_scope=False` to do your own scope checks instead;
- keeps the Agent Card and `/health` public, as discovery needs them, and leaves the monitor to its own token;
- records each caller's `subject` as the owner of the tasks it creates, so `tasks/get`, `tasks/cancel` and `ListTasks` only show callers their own tasks (in memory, in `JsonFileTaskStore` and in the a2a-sdk's `DatabaseTaskStore`).

`TacoAgent` takes the same `token_verifier` and `require_task_scope` arguments for its inbound requests. Its outbound peer calls carry their own credentials (`send_to_peer(..., headers=...)`); never forward the caller's token to a peer.

### Check project scopes in the handler

The verifier only sees the token; the project is in the payload. Inside a handler, `taco.current_auth()` returns the caller's `AuthContext`, so you can compare the two:

```python
from taco import TacoTaskError, current_auth


async def handle_estimate(task, payload):
    auth = current_auth()  # None when the server has no token_verifier
    project = payload.get("projectId")
    if auth is None or not auth.has_scope(f"taco:project:{project}:write"):
        raise TacoTaskError(f"This token is not scoped to project {project}")
    ...
```

The request has already been accepted by then, so the caller gets a `failed` task carrying that message, not an HTTP 403. If your deployment needs a 403 for a project mismatch, check the payload in a gateway or middleware in front of the agent.

### Use your own token for downstream calls

`TacoClient(headers=...)` sets headers for every request, and `send_message`, `get_task` and `cancel_task` (and `TacoAgent.send_to_peer`) take per-call `headers`. Send a token obtained for the next hop, never the one your caller sent:

```python
from taco import TacoClient

supplier_token = await exchange_token(  # your RFC 8693 call to the auth server
    scope="taco:task:material-procurement taco:project:PRJ-0042:write",
    audience="https://api.pipeworks.example.com/a2a",
)
async with TacoClient(
    agent_url="https://api.pipeworks.example.com/a2a",
    headers={"Authorization": f"Bearer {supplier_token}"},
) as client:
    quote_task = await client.send_message("material-procurement", bom)
```

If the exchange needs the token your agent received as its `subject_token`, have your verifier keep it in `AuthContext.claims` so the handler can read it through `current_auth()`.

### Protect the operational endpoints

- The [monitor](/docs/sdk#agent-monitor) shows every payload. Set `monitor_auth_token` (on `A2AServer` or `TacoAgent`) before the port is reachable by anyone else, or turn it off.
- The admin skill endpoints (`enable_admin=True`) take their own `admin_auth_token`.
- `cors_origins=["*"]` lets any web page call your task endpoint from a browser. List the origins you need.

| Checklist step | In the SDK |
|----------------|------------|
| 2. Declare `securitySchemes` and `security` | `ConstructionAgentCard(security_schemes=..., security=...)` |
| 3. Scopes in `scopesOffered` | `construction_security=SecurityExt(scopes_offered=[...])` |
| 4. Validate tokens; 401 / 403 | `A2AServer(card, token_verifier=verify)`; task scope enforced by default |
| 5. No token passthrough | Your own token in `TacoClient(headers=...)` or `send_to_peer(headers=...)` |
| 6. Project scope matches `projectId` | `taco.current_auth()` in the handler |

## Adding New Scopes

New scope dimensions or patterns can be proposed via [GitHub issue](https://github.com/pelles-ai/taco/issues). A proposal should include:

1. The scope string, following the `taco:{dimension}:{value}` pattern
2. Its dimension (`trade`, `project`, `csi`, `task`, `registry`, or a proposed new one)
3. What the scope permits
4. At least one concrete authorization scenario that needs it
