---
title: "bom-v1 — Bill of Materials"
description: Standardized Bill of Materials schema — line items, quantities, materials, sizes, and provenance for construction takeoffs.
---

# bom-v1 — Bill of Materials

The Bill of Materials schema defines a standardized format for construction material takeoffs. It captures line items with quantities, materials, sizes, and provenance metadata.

**JSON Schema:** [`spec/schemas/bom-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/bom-v1.json)

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `projectId` | string | Yes | Unique project identifier |
| `revision` | string | No | Drawing revision this BOM was generated from |
| `trade` | string (enum) | Yes | Trade this BOM covers: `mechanical`, `electrical`, `plumbing`, `structural`, `civil`, `architectural`, `fire-protection`, `general`, `multi-trade` |
| `csiDivision` | string | Yes | Primary CSI MasterFormat division number |
| `lineItems` | array | Yes | Individual material line items (min 1) |
| `metadata` | object | Yes | Generation metadata |

## Line Item Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique line item identifier |
| `description` | string | Yes | Human-readable material description |
| `quantity` | number | Yes | Measured quantity |
| `unit` | string (enum) | Yes | Unit of measure: `EA`, `LF`, `SF`, `CF`, `CY`, `TON`, `LB`, `GAL`, `LS` |
| `size` | string | No | Size specification (e.g., `"4 inch"`) |
| `material` | string | No | Material type (e.g., `"copper"`, `"PVC"`) |
| `specSection` | string | No | Specification section reference (e.g., `"23 21 13"`) |
| `sourceSheet` | string | No | Drawing sheet this item was taken from (e.g., `"M-201"`) |
| `location` | string | No | Location within the project (e.g., `"Level 2 Wing B"`) |
| `alternates` | array | No | Acceptable alternate materials |

### Alternate Fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Alternate material description |
| `manufacturer` | string | Manufacturer name |
| `partNumber` | string | Manufacturer part number |

## Metadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `generatedBy` | string | Yes | Agent ID that generated this BOM |
| `generatedAt` | string (date-time) | Yes | Timestamp of generation |
| `confidence` | number (0-1) | No | Overall confidence score |
| `sourceDocuments` | array | No | Source document references |
| `flaggedItems` | array | No | Items flagged for human review |

## Example Payload

```json
{
  "projectId": "PRJ-2026-OAKRIDGE-MEDICAL",
  "revision": "Rev C",
  "trade": "mechanical",
  "csiDivision": "23",
  "lineItems": [
    {
      "id": "LI-001",
      "description": "Rooftop Unit, 25-ton, high-efficiency",
      "quantity": 2,
      "unit": "EA",
      "size": "25 ton",
      "material": "packaged-unit",
      "specSection": "23 81 26",
      "sourceSheet": "M-101",
      "location": "Roof Level",
      "alternates": [
        {
          "description": "Carrier 48HC",
          "manufacturer": "Carrier",
          "partNumber": "48HC-A28"
        }
      ]
    },
    {
      "id": "LI-002",
      "description": "Copper pipe, Type L",
      "quantity": 850,
      "unit": "LF",
      "size": "2 inch",
      "material": "copper",
      "specSection": "23 21 13",
      "sourceSheet": "M-201",
      "location": "Level 1-3 Risers"
    },
    {
      "id": "LI-003",
      "description": "Butterfly valve, lug style",
      "quantity": 24,
      "unit": "EA",
      "size": "4 inch",
      "material": "cast-iron",
      "sourceSheet": "M-301"
    }
  ],
  "metadata": {
    "generatedBy": "pelles-takeoff-agent-v2",
    "generatedAt": "2026-02-28T10:30:00Z",
    "confidence": 0.92,
    "sourceDocuments": [
      {
        "filename": "Oakridge-Medical-HVAC-Plans.pdf",
        "sheetId": "M-101",
        "revision": "C"
      },
      {
        "filename": "Oakridge-Medical-HVAC-Plans.pdf",
        "sheetId": "M-201",
        "revision": "C"
      }
    ],
    "flaggedItems": [
      {
        "lineItemId": "LI-001",
        "reason": "Verify tonnage — spec says 20-ton but plan detail shows 25-ton",
        "severity": "warning"
      }
    ]
  }
}
```

## Python SDK

```python
from taco import BOMV1

# Parse from JSON
bom = BOMV1.model_validate(json_data)

# Access with snake_case
print(bom.project_id)           # "PRJ-2026-OAKRIDGE-MEDICAL"
print(bom.line_items[0].size)   # "25 ton"
print(bom.metadata.confidence)  # 0.92

# Serialize to camelCase JSON
output = bom.model_dump(by_alias=True, exclude_none=True)
```
