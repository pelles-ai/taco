---
title: "change-order-v1 — Change Order"
description: Change order analysis schema — cost impact, schedule impact, and scope modifications.
---

# change-order-v1 — Change Order

The Change Order schema defines a standardized format for construction change order analysis, including cost impact, schedule impact, and scope modifications.

**JSON Schema:** [`spec/schemas/change-order-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/change-order-v1.json)

**Status:** Defined.

## Structure

### ChangeOrderV1 (top-level)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `projectId` | string | Yes | Project identifier |
| `changeOrderNumber` | string (min 1) | Yes | Change order number |
| `title` | string (min 1) | Yes | Change order title |
| `reason` | ChangeOrderReason | Yes | Reason for the change order |
| `status` | ChangeOrderStatus | Yes | Current status |
| `lineItems` | ChangeOrderLineItem[] | Yes (min 1) | Line items with cost/schedule impact |
| `totalCostImpact` | float | Yes | Total cost impact (can be negative for savings) |
| `totalScheduleImpactDays` | integer | No | Total schedule impact in days (default 0) |
| `relatedRfis` | string[] | No | Related RFI identifiers |
| `metadata` | ChangeOrderMetadata | Yes | Generation metadata |

### ChangeOrderLineItem

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string (min 1) | Yes | Unique line item identifier |
| `description` | string | Yes | Description of the change |
| `trade` | Trade | No | Associated trade |
| `costImpact` | float | Yes | Cost impact (negative for credits/savings) |
| `scheduleImpactDays` | integer | No | Schedule impact in days (default 0) |
| `bomItemIds` | string[] | No | Related BOM item identifiers |

### ChangeOrderReason

One of: `design-change`, `unforeseen-condition`, `owner-request`, `value-engineering`, `code-compliance`, `error-omission`

### ChangeOrderStatus

One of: `draft`, `submitted`, `approved`, `rejected`, `withdrawn`

### ChangeOrderMetadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `generatedBy` | string | Yes | System or agent that generated the change order |
| `generatedAt` | string | Yes | ISO-8601 timestamp |
| `confidence` | float (0-1) | No | Confidence score |
| `notes` | string[] | No | Additional notes |

## Validation Rules

- Line items list must contain at least one item
- `changeOrderNumber` and `title` must be non-empty
- Line item `id` must be non-empty
- `reason` must be a valid ChangeOrderReason value
- `status` must be a valid ChangeOrderStatus value
- `costImpact` and `totalCostImpact` can be negative (representing credits or savings)

## Example

```json
{
  "projectId": "PRJ-2026-OAKRIDGE",
  "changeOrderNumber": "CO-001",
  "title": "HVAC rerouting due to structural conflict",
  "reason": "design-change",
  "status": "draft",
  "lineItems": [
    {
      "id": "COL-001",
      "description": "Reroute ductwork around beam",
      "trade": "mechanical",
      "costImpact": 15000.00,
      "scheduleImpactDays": 3,
      "bomItemIds": ["LI-001", "LI-002"]
    }
  ],
  "totalCostImpact": 15000.00,
  "totalScheduleImpactDays": 3,
  "relatedRfis": ["RFI-001"],
  "metadata": {
    "generatedBy": "change-order-agent",
    "generatedAt": "2026-02-28T14:00:00Z",
    "confidence": 0.85
  }
}
```

## Python SDK

```python
from taco import ChangeOrderV1, ChangeOrderLineItem, ChangeOrderMetadata

co = ChangeOrderV1(
    project_id="PRJ-001",
    change_order_number="CO-001",
    title="HVAC rerouting due to structural conflict",
    reason="design-change",
    status="draft",
    line_items=[
        ChangeOrderLineItem(
            id="COL-001",
            description="Reroute ductwork around beam",
            trade="mechanical",
            cost_impact=15000.00,
            schedule_impact_days=3,
        ),
    ],
    total_cost_impact=15000.00,
    metadata=ChangeOrderMetadata(
        generated_by="estimator",
        generated_at="2026-02-28T14:00:00Z",
        confidence=0.85,
    ),
)
```
