---
title: "rfi-v1 — Request for Information"
description: RFI schema for design conflicts, missing information, and clarifications — with drawing references and priority levels.
---

# rfi-v1 — Request for Information

The RFI schema defines a standardized format for construction Requests for Information. It captures design conflicts, missing information, and clarification requests with drawing references and priority levels.

**JSON Schema:** [`spec/schemas/rfi-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/rfi-v1.json)

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `projectId` | string | Yes | Unique project identifier |
| `subject` | string | Yes | Brief subject line for the RFI |
| `question` | string | Yes | The detailed question or clarification request |
| `category` | string (enum) | Yes | RFI category (see below) |
| `priority` | string (enum) | Yes | Urgency level: `low`, `medium`, `high`, `critical` |
| `references` | array | Yes | Drawing/document references (min 1) |
| `suggestedResolution` | string | No | Agent's suggested resolution |
| `relatedBomItems` | string[] | No | BOM line item IDs related to this RFI |
| `dueDate` | string (date) | No | Requested response date |
| `assignedTo` | object | No | Intended recipient |
| `metadata` | object | Yes | Generation metadata |

### Category Values

| Value | Description |
|-------|-------------|
| `design-conflict` | Contradictory information between drawings or specs |
| `missing-information` | Required information not shown on documents |
| `clarification` | Ambiguous detail that needs confirmation |
| `substitution` | Request to substitute specified materials |
| `coordination` | Conflicts between trades requiring resolution |
| `code-compliance` | Potential building code violation |

## Reference Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sheetId` | string | Yes | Drawing sheet reference (e.g., `"M-201"`) |
| `area` | string | No | Area on the sheet (e.g., `"grid D4-E6"`) |
| `coordinates` | object | No | Bounding box: `{x, y, width, height}` |
| `markup` | string | No | Base64-encoded markup image (PNG) |

## Assignee Fields

| Field | Type | Description |
|-------|------|-------------|
| `role` | string (enum) | `architect`, `engineer`, `owner`, `contractor`, `subcontractor` |
| `company` | string | Company name |
| `contact` | string | Contact info (email) |

## Metadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `generatedBy` | string | Yes | Agent ID that generated this RFI |
| `generatedAt` | string (date-time) | Yes | Timestamp of generation |
| `confidence` | number (0-1) | No | Confidence this is a legitimate issue |
| `relatedRfis` | string[] | No | IDs of related RFIs |

## Example Payload

```json
{
  "projectId": "PRJ-2026-OAKRIDGE-MEDICAL",
  "subject": "HVAC pipe size discrepancy — Drawing M-201 vs. schedule",
  "question": "Drawing M-201 detail 3 shows a 4-inch chilled water supply line at grid D4-E6, but the pipe schedule on M-001 specifies 3-inch for this run. Which is correct?",
  "category": "design-conflict",
  "priority": "high",
  "references": [
    {
      "sheetId": "M-201",
      "area": "grid D4-E6",
      "coordinates": {
        "x": 1240,
        "y": 890,
        "width": 320,
        "height": 180
      }
    },
    {
      "sheetId": "M-001",
      "area": "pipe schedule row 14"
    }
  ],
  "suggestedResolution": "Use 4-inch as shown on plan detail — the schedule may not have been updated after the Rev C resize.",
  "relatedBomItems": ["LI-006", "LI-007"],
  "dueDate": "2026-03-15",
  "assignedTo": {
    "role": "engineer",
    "company": "Smith MEP Engineering",
    "contact": "rsmith@smithmep.com"
  },
  "metadata": {
    "generatedBy": "pelles-rfi-agent-v1",
    "generatedAt": "2026-03-01T14:22:00Z",
    "confidence": 0.91,
    "relatedRfis": ["RFI-042"]
  }
}
```

## Python SDK

```python
from taco import RFIV1

# Parse from JSON
rfi = RFIV1.model_validate(json_data)

# Access with snake_case
print(rfi.category)              # "design-conflict"
print(rfi.priority)              # "high"
print(rfi.references[0].area)    # "grid D4-E6"
print(rfi.metadata.confidence)   # 0.91

# Serialize to camelCase JSON
output = rfi.model_dump(by_alias=True, exclude_none=True)
```
