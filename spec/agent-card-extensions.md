# TACO Agent Card Extensions

TACO extends the standard A2A Agent Card with construction-specific metadata using the `x-construction` extension field. These fields are optional — any A2A client that does not understand them will simply ignore them per the A2A specification.

## Canonical Extension URI

A2A v1 added `AgentCapabilities.extensions[]` — a formal way for agents to advertise which protocol extensions they implement, identified by URI. TACO declares its construction extension under:

```
https://taco.construction/extensions/x-construction/v1
```

A TACO agent card carrying the inline `x-construction` field **also** lists this URI under `capabilities.extensions[]`, so A2A v1 clients can discover support via capability negotiation without parsing the inline field. The declaration's `params` carry the same object as the inline field, plus `skills`: each skill's `x-construction` object, keyed by skill id.

```json
{
  "capabilities": {
    "streaming": false,
    "extensions": [
      {
        "uri": "https://taco.construction/extensions/x-construction/v1",
        "description": "TACO construction-domain agent metadata: trade, CSI divisions, project types, certifications, data formats, integrations, security.",
        "required": false,
        "params": {
          "trade": "mechanical",
          "csiDivisions": ["22", "23"],
          "skills": {
            "generate-estimate": {"taskType": "estimate", "inputSchema": "bom-v1", "outputSchema": "estimate-v1"}
          }
        }
      }
    ]
  },
  "x-construction": {"trade": "mechanical", "csiDivisions": ["22", "23"]},
  "skills": [
    {"id": "generate-estimate", "x-construction": {"taskType": "estimate", "inputSchema": "bom-v1", "outputSchema": "estimate-v1"}}
  ]
}
```

A2A v1 card parsers keep the extension declaration but drop the inline `x-construction` fields, so for v1 readers `params` is where the metadata lives. The inline fields stay, with identical content, for v0.3 readers and for readers that ignore `extensions[]`. Readers **SHOULD** use the inline fields when present and fall back to `params`, so cards written for A2A v1 alone are understood too.

In Python the constant is exposed as `taco.X_CONSTRUCTION_EXTENSION_URI`, and `taco.apply_construction_extension_declaration(card)` mutates a card so it carries the declaration (idempotent — `ConstructionAgentCard.to_a2a()` calls it automatically). `A2AServer` fills `params` from the inline fields each time it serves the card, so they cannot drift apart; set the fields once, on the card model.

## Protocol Versions

A TACO server answers A2A v0.3 and A2A v1 requests on the same JSON-RPC endpoint ([ADR-0010](https://taco-protocol.com/docs/decisions/negotiate-v1-wire-format)). Its card lists both in `supportedInterfaces`, `1.0` first, and keeps the v0.3 `url` and `protocolVersion` fields:

```json
{
  "url": "https://api.buildright.io/a2a",
  "protocolVersion": "0.3.0",
  "supportedInterfaces": [
    {"url": "https://api.buildright.io/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"},
    {"url": "https://api.buildright.io/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "0.3"}
  ]
}
```

A2A v1 clients pick the `1.0` interface and send v1 requests (`SendMessage`, `A2A-Version: 1.0`); v0.3 clients read `url` and send `message/send` as before. A card without `supportedInterfaces` is a v0.3 card. A card written for A2A v1 alone may have no top-level `url`; TACO's readers then use the first JSON-RPC interface's URL.

`A2AServer` adds `supportedInterfaces` and `protocolVersion` when it serves the card, using the card's `url` (or the address the request reached, if `url` is empty). A card that sets either field itself is served with its own value.

## Top-Level Extension: `x-construction`

Added to the root of the Agent Card.

```json
{
  "x-construction": {
    "trade": "mechanical",
    "csiDivisions": ["22", "23"],
    "projectTypes": ["commercial", "healthcare", "education"],
    "certifications": ["SOC2"],
    "dataFormats": {
      "input": ["pdf", "dwg", "rvt", "ifc"],
      "output": ["bom-json", "csv", "pdf"]
    },
    "integrations": ["procore", "acc", "bluebeam"],
    "security": {
      "trustTier": 0,
      "scopesOffered": ["taco:trade:mechanical", "taco:task:takeoff"]
    }
  }
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trade` | string | Yes | Primary trade the agent serves. Values: `mechanical`, `electrical`, `plumbing`, `structural`, `civil`, `architectural`, `fire-protection`, `general`, `multi-trade` |
| `csiDivisions` | string[] | Yes | CSI MasterFormat division numbers this agent covers (e.g., `["22", "23"]` for plumbing and HVAC) |
| `projectTypes` | string[] | No | Project types supported. Values: `commercial`, `residential`, `healthcare`, `education`, `industrial`, `infrastructure`, `mixed-use` |
| `certifications` | string[] | No | Security/compliance certifications. Values: `SOC2`, `ISO27001`, `FedRAMP` |
| `dataFormats.input` | string[] | No | File formats the agent can accept as input |
| `dataFormats.output` | string[] | No | File formats the agent can produce |
| `integrations` | string[] | No | Platform integrations. Values: `procore`, `acc`, `bluebeam`, `plangrid`, `p6`, `ms-project`, `sage`, `viewpoint` |
| `security` | object | No | TACO security metadata. See [`security.md`](security.md) for the full field reference. |

## Skill-Level Extension: `x-construction`

Added to individual skill entries in the Agent Card's `skills` array.

```json
{
  "skills": [
    {
      "id": "generate-bom",
      "name": "Generate Bill of Materials",
      "description": "Generates a detailed BOM from construction plan sheets",
      "x-construction": {
        "taskType": "takeoff",
        "inputSchema": "plan-sheets",
        "outputSchema": "bom-v1"
      }
    }
  ]
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `taskType` | string | Yes | References a TACO task type (see [task-types.md](task-types.md)) |
| `inputSchema` | string | No | Expected input schema identifier |
| `outputSchema` | string | Yes | Output schema identifier (see `schemas/` directory) |

## Discovery Queries

Orchestrators find agents by these extension fields: `trade`, `taskType` (a skill's `x-construction.taskType`), `csiDivisions`, `projectTypes` and `integrations`. An agent matches a query when it matches every field the query names.

In the Python reference SDK, discovery is the in-process `AgentRegistry`. The orchestrator registers the agents it knows about and filters them in memory:

```python
registry = AgentRegistry()
await registry.register("https://api.buildright.io/a2a")
agents = registry.find(
    trade="mechanical",
    task_type="schedule-coordination",
    project_type="healthcare",
    integration="procore",
)
```

`find()` returns every registered Agent Card matching all the given filters (`trade`, `task_type`, `csi_division`, `project_type`, `integration`). Callers should send requests to the URL they registered (`registry.entries()` returns `(url, card)` pairs), not to the `url` a card declares about itself.

No HTTP registry service exists yet. A hosted TACO Agent Registry that answers these queries over HTTP is future work (see [ADR-0005](https://taco-protocol.com/docs/decisions/in-memory-registry-first) and the [roadmap](https://taco-protocol.com/docs/roadmap)).

## Security Extension: `x-construction.security`

The `security` sub-object carries TACO-specific security metadata. See [`security.md`](security.md) for the complete specification, including the scope taxonomy and registry trust model.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trustTier` | integer | No | Registry trust tier: `0` unverified, `1` org-verified, `2` cert-attested. Assigned by the TACO Registry. |
| `scopesOffered` | string[] | No | TACO OAuth scopes this agent will accept. See [`security.md` — Scope Taxonomy](security.md#taco-scope-taxonomy). |
| `projectScoped` | boolean | No | If `true`, incoming requests must include a `taco:project:{id}` scope. |
| `delegationSupported` | boolean | No | If `true`, the agent supports downstream Token Exchange ([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693)) sub-delegation. |
| `extendedCardUrl` | string | No | URL of the extended Agent Card, revealed after initial authentication. |
| `mtlsSupported` | boolean | No | If `true`, the agent accepts mTLS client certificates. Lets a registry/orchestrator filter on mTLS-capable agents without parsing the full `securitySchemes` block. |
| `pkceRequired` | boolean | No | If `true`, the agent requires PKCE ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)) on OAuth Authorization Code flows. Mirrors the v1 `pkceRequired` field on the AuthorizationCode flow. |
| `deviceCodeSupported` | boolean | No | If `true`, the agent supports the OAuth Device Authorization Grant flow ([RFC 8628](https://datatracker.ietf.org/doc/html/rfc8628)). Useful for headless / CI / TV-style clients. |

```json
{
  "x-construction": {
    "trade": "mechanical",
    "csiDivisions": ["23"],
    "security": {
      "trustTier": 1,
      "scopesOffered": ["taco:trade:mechanical", "taco:task:estimate"],
      "projectScoped": true,
      "delegationSupported": false,
      "mtlsSupported": true,
      "pkceRequired": true,
      "deviceCodeSupported": false
    }
  }
}
```

### Discovery filtering

Registries MAY use the auth-modality flags to narrow agent search results:

```
GET /agents?mtlsSupported=true&trade=mechanical
GET /agents?deviceCodeSupported=true
```

A consumer that does not understand these flags treats them as informational only — the canonical security configuration still lives in the top-level `securitySchemes` block.

### Declaring v1 OAuth flows on the agent card

A2A v1 added two OAuth features that the v0.3 wire format's `OAuthFlows` object did not carry:

- **`pkceRequired`** on the AuthorizationCode flow ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636))
- **DeviceCode flow** ([RFC 8628](https://datatracker.ietf.org/doc/html/rfc8628))

An agent declares them in its `securitySchemes` block with the v1 field names, next to the v0.3 fields:

```json
{
  "securitySchemes": {
    "tacoOAuth": {
      "type": "oauth2",
      "flows": {
        "authorizationCode": {
          "authorizationUrl": "https://auth.buildright.io/oauth/authorize",
          "tokenUrl": "https://auth.buildright.io/oauth/token",
          "scopes": {"taco:task:estimate": "Submit estimate tasks"},
          "pkceRequired": true
        },
        "deviceCode": {
          "deviceAuthorizationUrl": "https://auth.buildright.io/oauth/device",
          "tokenUrl": "https://auth.buildright.io/oauth/token",
          "scopes": {"taco:task:estimate": "Submit estimate tasks"}
        }
      }
    },
    "mtls": {"type": "mutualTLS"}
  }
}
```

Clients reading a card with a `deviceCode` flow or `pkceRequired` today MUST treat them as forward-compatible extensions and ignore them if their A2A SDK does not understand the fields.

In the Python SDK, `taco.AuthorizationCodeOAuthFlowV1` and `taco.DeviceCodeOAuthFlow` build these two flows, and `taco.MutualTLSSecurityScheme`, `taco.OAuth2SecurityScheme` and the other A2A scheme models are re-exported. All of them can be passed to `ConstructionAgentCard(security_schemes=...)`, also inside a `flows` dict. Put the v1 flows in a plain `flows` dict as above: the v0.3 `OAuthFlows` model drops fields it does not know, `deviceCode` included. The two flow models become pass-throughs to `a2a.types` after the v1 wire-format cutover.
