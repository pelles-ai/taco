---
sidebar_position: 3
title: Agent Card Extensions
description: The `x-construction` extension adds trade, CSI division, project type, and platform integration metadata to standard A2A Agent Cards.
---

# Agent Card Extensions

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
| `trade` | string | Yes | Primary trade. Values: `mechanical`, `electrical`, `plumbing`, `structural`, `civil`, `architectural`, `fire-protection`, `general`, `multi-trade` |
| `csiDivisions` | string[] | Yes | CSI MasterFormat division numbers (e.g., `["22", "23"]` for plumbing and HVAC) |
| `projectTypes` | string[] | No | Supported project types: `commercial`, `residential`, `healthcare`, `education`, `industrial`, `infrastructure`, `mixed-use` |
| `certifications` | string[] | No | Security/compliance certifications: `SOC2`, `ISO27001`, `FedRAMP` |
| `dataFormats.input` | string[] | No | File formats the agent can accept |
| `dataFormats.output` | string[] | No | File formats the agent can produce |
| `integrations` | string[] | No | Platform integrations: `procore`, `acc`, `bluebeam`, `plangrid`, `p6`, `ms-project`, `sage`, `viewpoint` |
| `security` | object | No | TACO security metadata. See [Security](./security) for the full reference. |

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
| `taskType` | string | Yes | References a TACO [task type](./task-types) |
| `inputSchema` | string | No | Expected input schema identifier |
| `outputSchema` | string | Yes | Output schema identifier (see [Data Schemas](./schemas/)) |

## Setting the fields in Python

`ConstructionAgentCard` takes each field as a snake_case argument and writes the camelCase JSON above:

```python
from taco import ConstructionAgentCard, ConstructionSkill, SecurityExt

card = ConstructionAgentCard(
    name="BuildRight Mechanical Estimating Agent",
    url="https://api.buildright.io/a2a",
    trade="mechanical",
    csi_divisions=["22", "23"],
    project_types=["commercial", "healthcare"],
    certifications=["SOC2"],
    data_formats={"input": ["bom-json"], "output": ["estimate-json", "csv", "pdf"]},
    integrations=["procore", "acc"],
    construction_security=SecurityExt(scopes_offered=["taco:task:estimate"], project_scoped=True),
    skills=[
        ConstructionSkill(id="generate-estimate", name="Generate Cost Estimate",
                          task_type="estimate", input_schema="bom-v1", output_schema="estimate-v1"),
    ],
)
```

## Discovery Queries

Orchestrators find agents by these extension fields. In the reference SDK, discovery is the in-process [`AgentRegistry`](/docs/sdk-reference/registry): you register the agents you know about, then filter them with `find()`:

```python
from taco import AgentRegistry

registry = AgentRegistry()
await registry.register("https://api.buildright.io/a2a")

agents = registry.find(
    trade="mechanical",
    task_type="schedule-coordination",
    project_type="healthcare",
    integration="procore",
)
```

`find()` returns every registered Agent Card that matches all the filters given (`trade`, `task_type`, `csi_division`, `project_type`, `integration`); `task_type` matches a skill's `x-construction.taskType`. Send requests to the URL you registered (`registry.entries()` returns `(url, card)` pairs) rather than to the `url` a card declares.

There is no HTTP registry service yet. A hosted registry with a query endpoint over these fields is future work; see [ADR-0005](/docs/decisions/in-memory-registry-first) and the [roadmap](/docs/roadmap).

## Full Agent Card Example

```json
{
  "name": "BuildRight Mechanical Estimating Agent",
  "description": "AI-powered cost estimation for mechanical trades",
  "url": "https://api.buildright.io/a2a",
  "version": "1.0.0",
  "skills": [
    {
      "id": "generate-estimate",
      "name": "Generate Cost Estimate",
      "description": "Produces a detailed cost estimate from a BOM",
      "x-construction": {
        "taskType": "estimate",
        "inputSchema": "bom-v1",
        "outputSchema": "estimate-v1"
      }
    },
    {
      "id": "value-engineer",
      "name": "Value Engineering Analysis",
      "description": "Identifies cost reduction opportunities",
      "x-construction": {
        "taskType": "value-engineering",
        "inputSchema": "bom-v1",
        "outputSchema": "ve-suggestions-v1"
      }
    }
  ],
  "x-construction": {
    "trade": "mechanical",
    "csiDivisions": ["22", "23"],
    "projectTypes": ["commercial", "healthcare"],
    "certifications": ["SOC2"],
    "dataFormats": {
      "input": ["bom-json"],
      "output": ["estimate-json", "csv", "pdf"]
    },
    "integrations": ["procore", "acc"],
    "security": {
      "trustTier": 1,
      "scopesOffered": [
        "taco:trade:mechanical",
        "taco:task:estimate",
        "taco:task:value-engineering"
      ],
      "projectScoped": true,
      "delegationSupported": false
    }
  }
}
```
