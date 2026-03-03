# TACO Agent Card Extensions

TACO extends the standard A2A Agent Card with construction-specific metadata using the `x-construction` extension field. These fields are optional — any A2A client that does not understand them will simply ignore them per the A2A specification.

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
| `dataFormats.input` | string[] | Yes | File formats the agent can accept as input |
| `dataFormats.output` | string[] | Yes | File formats the agent can produce |
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

```json
{
  "x-construction": {
    "trade": "mechanical",
    "csiDivisions": ["23"],
    "security": {
      "trustTier": 1,
      "scopesOffered": ["taco:trade:mechanical", "taco:task:estimate"],
      "projectScoped": true,
      "delegationSupported": false
    }
  }
}
```
