---
title: "change-order-v1 — Change Order"
description: Change order analysis schema — cost impact, schedule impact, and scope modifications.
---

import SchemaExplorer, {SchemaExample} from '@site/src/components/SchemaExplorer';

# change-order-v1 — Change Order

The Change Order schema defines a standardized format for construction change order analysis, including cost impact, schedule impact, and scope modifications.

**JSON Schema:** [`spec/schemas/change-order-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/change-order-v1.json)

**Status:** Defined.

## Fields

Generated from [`spec/schemas/change-order-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/change-order-v1.json). Open a field to see what it holds, or switch to **Validate** to check a payload of your own.

<SchemaExplorer schemaId="change-order-v1" />

## Validation Rules

- Line items list must contain at least one item
- `changeOrderNumber` and `title` must be non-empty
- Line item `id` must be non-empty
- `reason` must be a valid ChangeOrderReason value
- `status` must be a valid ChangeOrderStatus value
- `costImpact` and `totalCostImpact` can be negative (representing credits or savings)

## Example

<SchemaExample schemaId="change-order-v1" />

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
