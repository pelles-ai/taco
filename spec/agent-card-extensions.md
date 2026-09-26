# TACO Agent Card Extensions

TACO extends the standard A2A Agent Card with construction-specific metadata using the `x-construction` extension field. These fields are optional — any A2A client that does not understand them will simply ignore them per the A2A specification.

## Canonical Extension URI

A2A v1 added `AgentCapabilities.extensions[]` — a formal way for agents to advertise which protocol extensions they implement, identified by URI. TACO declares its construction extension under:

```
https://taco.construction/extensions/x-construction/v1
```

A TACO agent card carrying the inline `x-construction` field **also** lists this URI under `capabilities.extensions[]`, so A2A v1 clients can discover support via capability negotiation without parsing the inline field:

```json
{
  "capabilities": {
    "streaming": false,
    "extensions": [
      {
        "uri": "https://taco.construction/extensions/x-construction/v1",
        "description": "TACO construction-domain agent metadata: trade, CSI divisions, project types, certifications, data formats, integrations, security.",
        "required": false
      }
    ]
  },
  "x-construction": { "...": "..." }
}
```

In Python the constant is exposed as `taco.X_CONSTRUCTION_EXTENSION_URI`, and `taco.apply_construction_extension_declaration(card)` mutates a card so it carries the declaration (idempotent — `ConstructionAgentCard.to_a2a()` calls it automatically).

The inline `x-construction` field is preserved for back-compatibility with readers that ignore the `extensions[]` array.

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

The TACO Agent Registry supports querying agents using these extension fields:

```
GET /agents?trade=mechanical&taskType=schedule-coordination&projectType=healthcare&integration=procore
```

This returns all registered Agent Cards matching the filter criteria.

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

TACO exports Pydantic models for both so agent cards can declare them today even while the SDK still emits v0.3-shaped wire payloads:

- `taco.AuthorizationCodeOAuthFlowV1` — adds the optional `pkceRequired` field.
- `taco.DeviceCodeOAuthFlow` — full RFC 8628 flow shape.
- `taco.MutualTLSSecurityScheme` — re-exported from the A2A SDK for convenience.

These models will become direct pass-throughs to `a2a.types` after the v1 wire-format cutover. Clients reading a card serialized with a `deviceCode` flow today MUST treat it as a forward-compatible extension and ignore it if their A2A SDK does not understand the field.
