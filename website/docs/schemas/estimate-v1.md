---
title: "estimate-v1 — Cost Estimate"
description: Cost estimate schema — material, labor, equipment, summary totals, and overhead/profit calculations.
---

import SchemaExplorer from '@site/src/components/SchemaExplorer';

# estimate-v1 — Cost Estimate

The Estimate schema defines a standardized format for construction cost estimates. It captures line-item costs (material, labor, equipment), summary totals, and overhead/profit calculations.

An `estimate-v1` is the typed output of estimating, bid-leveling, and value-engineering agents. It usually takes a [`bom-v1`](./bom-v1) as input and produces a cost figure that downstream procurement, change-order, or scheduling agents can consume.

<SchemaExplorer schemaId="estimate-v1" />

## Python SDK

```python
from taco import EstimateV1

estimate = EstimateV1.model_validate(json_data)
print(estimate.summary.total)
print(estimate.currency)
output = estimate.model_dump(by_alias=True, exclude_none=True)
```

## See also

- [`bom-v1`](./bom-v1) — typical input for an estimate
- [`change-order-v1`](./change-order-v1) — change orders modify an estimate
- [Task types: `estimate`, `bid-leveling`, `value-engineering`](../task-types)
- [JSON Schema source](https://github.com/pelles-ai/taco/blob/main/spec/schemas/estimate-v1.json)
