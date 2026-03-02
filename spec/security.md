# CAIP Security

Security in CAIP builds on A2A's native authentication model and adds construction-specific authorization concepts: project-scoped credentials, trade-level permission boundaries, and a registry trust model for verified agents.

> **Status:** This document defines the CAIP security model. Implementation of these patterns is optional for sandbox deployments and recommended for production multi-company deployments.

## Overview

CAIP inherits the A2A protocol's authentication framework without modification. A2A defines five authentication scheme types (`apiKey`, `http`, `oauth2`, `openIdConnect`, `mutualTLS`), JWS-signed Agent Cards for tamper detection, extended Agent Cards for progressive capability disclosure, and OAuth 2.0 Token Exchange ([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693)) as the recommended delegation mechanism. Credentials are always carried in HTTP headers, never inside JSON-RPC payloads. See the [A2A specification](https://google.github.io/A2A/#/documentation?id=security) for the full authentication model.

CAIP adds three things on top of this foundation: (1) a **scope taxonomy** that maps OAuth scopes to construction concepts — trades, CSI divisions, project IDs, and task types; (2) a **registry trust model** with three verification tiers; and (3) a `security` sub-object in the [`x-construction`](agent-card-extensions.md) extension for construction-specific security metadata.

If an agent also exposes MCP tools for user-facing interactions (e.g., a GC employee querying an agent via chat), those interactions use OAuth 2.1 per the MCP specification and are complementary to A2A agent-to-agent auth. This document covers agent-to-agent security only.

## Deployment Scenarios

CAIP agents declare authentication using standard A2A `securitySchemes` and `security` fields in the Agent Card. CAIP does not add new scheme types — it recommends which of A2A's five schemes to use per deployment scenario.

| Scenario | Recommended Scheme | Notes |
|----------|-------------------|-------|
| Open / sandbox | None, or `apiKey` | For development and public demo agents. No token infrastructure required. |
| Single-company internal | `http` with `bearer` | JWT issued by internal IdP; scoped to trade and task types. |
| GC-to-subcontractor | `oauth2` with Token Exchange ([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693)) | GC orchestrator exchanges its token for a narrower token before calling a sub's agent. |
| Multi-company project network | `oauth2` + `openIdConnect` | Federated identity; project membership determines authorization. |
| High-assurance / regulated | `mutualTLS` | Certificate pinning, often combined with Bearer. For federal, DoD, or critical infrastructure projects. |

## Agent Card Security Declaration

A CAIP agent that requires authentication declares it in the standard A2A `securitySchemes` and `security` fields, alongside the `x-construction` extension:

```json
{
  "name": "BuildRight Mechanical Estimating Agent",
  "url": "https://api.buildright.io/a2a",
  "version": "1.0.0",
  "securitySchemes": {
    "caipOAuth": {
      "type": "oauth2",
      "flows": {
        "clientCredentials": {
          "tokenUrl": "https://auth.buildright.io/oauth/token",
          "scopes": {
            "caip:trade:mechanical": "Access mechanical trade workflows",
            "caip:task:estimate": "Submit estimate tasks",
            "caip:task:value-engineering": "Submit value engineering tasks"
          }
        }
      }
    }
  },
  "security": [
    { "caipOAuth": ["caip:trade:mechanical", "caip:task:estimate"] }
  ],
  "skills": [
    {
      "id": "generate-estimate",
      "name": "Generate Cost Estimate",
      "x-construction": {
        "taskType": "estimate",
        "inputSchema": "bom-v1",
        "outputSchema": "estimate-v1"
      }
    }
  ],
  "x-construction": {
    "trade": "mechanical",
    "csiDivisions": ["22", "23"],
    "certifications": ["SOC2"],
    "security": {
      "trustTier": 1,
      "scopesOffered": ["caip:trade:mechanical", "caip:task:estimate", "caip:task:value-engineering"],
      "projectScoped": true,
      "delegationSupported": false
    }
  }
}
```

The `securitySchemes` key name (`caipOAuth`) is locally defined. CAIP recommends using a descriptive name that includes the scheme type.

## CAIP Scope Taxonomy

CAIP defines a scope naming convention that makes construction authorization semantics machine-readable. These scope names are declared in `securitySchemes`, requested by orchestrators during token acquisition, and validated by agents on incoming requests.

### Scope Format

```
caip:{dimension}:{value}[:{action}]
```

- `dimension`: one of `trade`, `task`, `csi`, `project`, `registry`
- `value`: a construction-domain identifier (trade name, task type, CSI division, project ID)
- `action` (optional): `read`, `write`, or `admin`. Defaults to `write` if omitted.

### Scope Reference

| Scope Pattern | Meaning | Example |
|---------------|---------|---------|
| `caip:trade:{trade}` | Access to all workflows for a given trade | `caip:trade:mechanical` |
| `caip:task:{taskType}` | Permission to submit a specific task type | `caip:task:estimate` |
| `caip:csi:{division}` | Access scoped to a CSI MasterFormat division | `caip:csi:23` |
| `caip:project:{id}:read` | Read access to a specific project's artifacts | `caip:project:PRJ-0042:read` |
| `caip:project:{id}:write` | Write (task submission) access on a specific project | `caip:project:PRJ-0042:write` |
| `caip:registry:read` | Discover agents in the CAIP Registry | `caip:registry:read` |
| `caip:registry:publish` | Publish or update an Agent Card in the Registry | `caip:registry:publish` |

The `{trade}` values match the `trade` field in [`agent-card-extensions.md`](agent-card-extensions.md). The `{taskType}` values match the task types defined in [`task-types.md`](task-types.md). The `{id}` in project scopes should match the `projectId` field used in CAIP data schemas (`bom-v1`, `rfi-v1`, etc.).

### Scope Combination Rules

1. **Scopes are additive.** An orchestrator requesting both `caip:trade:mechanical` and `caip:task:estimate` can only call estimate tasks on mechanical agents.
2. **Project scopes require a task or trade scope.** A `caip:project:{id}` scope is not meaningful alone — it gates which project's data is accessible, while trade and task scopes gate what actions are permitted.
3. **Agents validate scope against task type.** An agent advertising `caip:task:takeoff` should reject tokens that only carry `caip:task:estimate`. The incoming token's scopes must include the task type being requested.

## Token Delegation (Agent Chains)

Construction workflows commonly involve chains of three or more agents from different organizations. A GC's orchestrator delegates to a specialty contractor's estimating agent, which may sub-delegate to a supplier's quote agent. Each hop should narrow the token's authority.

### Token Exchange Pattern

OAuth 2.0 Token Exchange ([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693)) allows an agent to exchange its own token for a narrower one scoped to just what the next agent needs. The orchestrator calls the authorization server's token endpoint with `grant_type=urn:ietf:params:oauth:grant-type:token-exchange` and receives a new token with reduced scope, a shorter TTL, and an audience locked to the target agent.

**Example: GC → Estimator → Supplier chain**

1. GC orchestrator authenticates to the auth server with `client_credentials`; receives a token scoped to `caip:trade:mechanical caip:project:PRJ-0042:write`.
2. Before calling the mechanical estimating agent, the orchestrator exchanges its token for one scoped to `caip:task:estimate caip:project:PRJ-0042:write` (narrowed: no longer full trade scope, only the estimate task).
3. Estimating agent validates the narrow token; executes the estimate; returns `estimate-v1`.
4. If the estimating agent needs to call the supplier quote agent, it exchanges again: requests `caip:task:material-procurement caip:project:PRJ-0042:write`.
5. Each agent only ever holds authority for its own task, on this specific project.

```
POST /oauth/token HTTP/1.1
Host: auth.buildright.io
Content-Type: application/x-www-form-urlencoded

grant_type=urn:ietf:params:oauth:grant-type:token-exchange
&subject_token=<orchestrator_token>
&subject_token_type=urn:ietf:params:oauth:token-type:access_token
&scope=caip:task:estimate+caip:project:PRJ-0042:write
&audience=https://api.mech-estimating.io/a2a
```

### Token Passthrough Prohibition

Agents must not forward their own received token to downstream agents. This prohibition mirrors the MCP specification's stance on user tokens. In CAIP's multi-company context, it also prevents a compromised agent from escalating its authority by re-using its caller's token with a different downstream agent. Always perform a Token Exchange to obtain a new, appropriately-scoped token for each hop.

## Registry Trust Model

The CAIP Agent Registry is the mechanism by which orchestrators discover agents. Trust in a discovered agent depends on how it was listed.

### Trust Tiers

| Tier | Label | How Achieved | What It Means |
|------|-------|-------------|---------------|
| 0 | Unverified | Self-published via `caip:registry:publish` scope | Agent Card is indexed; no claims are validated. Suitable for development and sandbox use. |
| 1 | Org Verified | Organization passed domain ownership verification (DNS TXT record or HTTPS challenge on the `url` domain) | The agent URL's domain belongs to a verified organization. Organization claims are trusted; certification claims remain self-declared. |
| 2 | Cert Attested | `certifications` array items (e.g., `SOC2`, `ISO27001`) were verified by the registry against a third-party attestation service or uploaded audit report | Certification claims are confirmed by the registry, not self-declared. |

> **Note:** The `trustTier` field in `x-construction.security` is assigned by the registry. Agents should not self-declare a tier they have not achieved. The existing `certifications` field in `x-construction` is self-declared metadata; `trustTier` is registry-verified. These are distinct concepts.

### JWS-Signed Agent Cards

A2A supports signing Agent Cards using JSON Web Signature ([RFC 7515](https://datatracker.ietf.org/doc/html/rfc7515)). CAIP recommends that Tier 1 and Tier 2 agents sign their cards to prevent tampering when cards pass through intermediary registries or brokers. A signed card proves the card content hasn't been modified in transit — it does not by itself establish trust tier.

### Registry Queries and Auth

Querying the registry to discover agents requires a `caip:registry:read` scope. The registry returns Agent Cards in full. The consuming orchestrator is responsible for evaluating the trust tier and deciding whether to proceed. Agents at higher trust tiers may appear higher in search results, but the registry does not filter out lower-tier agents unless the query explicitly requests a minimum tier.

## x-construction Security Extension

CAIP adds a `security` sub-object to the top-level `x-construction` extension to carry construction-specific security metadata that supplements A2A's `securitySchemes`. See [`agent-card-extensions.md`](agent-card-extensions.md) for the full extension specification.

```json
{
  "x-construction": {
    "trade": "mechanical",
    "csiDivisions": ["22", "23"],
    "security": {
      "trustTier": 1,
      "scopesOffered": ["caip:trade:mechanical", "caip:task:estimate"],
      "projectScoped": true,
      "delegationSupported": true,
      "extendedCardUrl": "https://api.buildright.io/a2a/agent-extended.json"
    }
  }
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trustTier` | integer | No | Registry trust tier: `0` (unverified), `1` (org verified), `2` (cert attested). Assigned by the registry; agents should not self-declare a tier they have not achieved. |
| `scopesOffered` | string[] | No | CAIP scopes this agent will accept on incoming requests. Derived from the Agent Card's `securitySchemes`; surfaced here for quick registry filtering without requiring a full OAuth discovery flow. |
| `projectScoped` | boolean | No | If `true`, the agent requires a `caip:project:{id}` scope in addition to task/trade scopes. Allows orchestrators to know in advance whether they need a project-specific token. |
| `delegationSupported` | boolean | No | If `true`, the agent can participate in Token Exchange (RFC 8693) sub-delegation chains. |
| `extendedCardUrl` | string | No | URL of the extended Agent Card (per A2A spec) that reveals additional capabilities after authentication. |

> `scopesOffered` is informational — it enables registry filtering by scope without a full OAuth flow. The authoritative scope declaration remains in the Agent Card's `securitySchemes`.

## Construction Authorization Concepts

### Trade Boundaries

Trade scopes (`caip:trade:{trade}`) align with how construction projects are organized. A mechanical subcontractor's agent should only accept tasks for mechanical trade workflows. A multi-trade GC orchestrator may hold multiple trade scopes but should only pass the relevant trade scope to each downstream agent via Token Exchange.

### Project Membership

In a typical commercial construction project, three levels of project access exist:

1. **Project owner / GC** — full project write access across trades (`caip:project:{id}:write` + multiple `caip:trade:*` scopes).
2. **Trade contractors** — write access to their own CSI divisions within the project (`caip:project:{id}:write` + `caip:csi:{div}` + `caip:trade:{trade}`).
3. **Consultants** (architects, engineers) — read access for review tasks (`caip:project:{id}:read`).

The CAIP scope taxonomy can express all three levels through scope combination.

### Human-in-the-Loop and Credential Handling

Some task types (notably `rfi-generation`, `submittal-review`, `change-order-analysis`) may reach a state of `input-required` per the A2A task lifecycle, pausing for human review. When an agent pauses for human input, any credentials held in-memory should not be persisted to disk. Orchestrators should re-acquire tokens when resuming a paused task rather than caching long-lived tokens across task suspension points.

## Implementation Checklist

For production deployments:

1. Choose the auth scheme appropriate for the deployment scenario (see table above).
2. Declare `securitySchemes` and `security` in the Agent Card using A2A field conventions.
3. Define CAIP scopes for each task type and trade the agent supports; add them to `x-construction.security.scopesOffered`.
4. Validate incoming bearer tokens on every `message/send` request. Reject with HTTP 401 if no token; HTTP 403 if the token lacks a required scope.
5. Do not pass received tokens downstream — perform Token Exchange for each agent hop.
6. If the agent is project-scoped, extract `projectId` from the incoming data payload and verify the token carries a matching `caip:project:{id}` scope.
7. Submit to the CAIP Registry for trust tier elevation after achieving SOC2, ISO27001, or equivalent certification.

## Adding New Scopes

New scope dimensions or patterns can be proposed via GitHub issue. A proposal should include:

1. Scope string following the `caip:{dimension}:{value}` pattern
2. Dimension (must be one of: `trade`, `project`, `csi`, `task`, `registry`, or a proposed new dimension)
3. Description of what the scope permits
4. At least one concrete authorization scenario demonstrating the need
