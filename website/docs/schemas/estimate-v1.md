---
title: "estimate-v1 — Cost Estimate"
description: Cost estimate schema — material, labor, equipment, summary totals, and overhead/profit calculations.
---

# estimate-v1 — Cost Estimate

The Estimate schema defines a standardized format for construction cost estimates. It captures line-item costs (material, labor, equipment), summary totals, and overhead/profit calculations.

**JSON Schema:** [`spec/schemas/estimate-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/estimate-v1.json)

**Status:** Defined. The schema structure is complete and implemented in the SDK.

## Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `projectId` | string | Unique project identifier |
| `trade` | string | Trade this estimate covers |
| `csiDivision` | string | Primary CSI division |
| `lineItems` | array | Cost breakdown per BOM line item |
| `summary` | object | Totals: material, labor, equipment, overhead, profit, grand total |
| `metadata` | object | Generation metadata with confidence score |

## Line Item Fields

Each line item references a BOM item and adds cost data:

| Field | Type | Description |
|-------|------|-------------|
| `bomItemId` | string | Reference to the BOM line item ID |
| `description` | string | Material description |
| `quantity` | number | Quantity |
| `unit` | string | Unit of measure |
| `materialUnitCost` | number | Cost per unit (material) |
| `materialTotal` | number | Total material cost |
| `laborHours` | number | Estimated labor hours |
| `laborRate` | number | Hourly labor rate |
| `laborTotal` | number | Total labor cost |
| `subtotal` | number | Line item subtotal |

## Python SDK

```python
from taco import EstimateV1

estimate = EstimateV1.model_validate(json_data)
print(estimate.summary.grand_total)
```

:::info Contributing
This schema is defined. See the [JSON Schema file](https://github.com/pelles-ai/taco/blob/main/spec/schemas/estimate-v1.json) for the full specification. Feedback and improvements welcome via [GitHub Issues](https://github.com/pelles-ai/taco/issues).
:::
