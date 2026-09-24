---
title: "estimate-v1 — Cost Estimate"
description: Cost estimate schema — material, labor, equipment, summary totals, and overhead/profit calculations.
---

import SchemaExplorer, {SchemaExample} from '@site/src/components/SchemaExplorer';

# estimate-v1 — Cost Estimate

The Estimate schema defines a standardized format for construction cost estimates. It captures line-item costs (material, labor, equipment), summary totals, and overhead/profit calculations.

**JSON Schema:** [`spec/schemas/estimate-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/estimate-v1.json)

**Status:** Defined. The schema structure is complete and implemented in the SDK.

## Fields

Generated from [`spec/schemas/estimate-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/estimate-v1.json). Open a field to see what it holds, or switch to **Validate** to check a payload of your own.

<SchemaExplorer schemaId="estimate-v1" />

## Example

<SchemaExample schemaId="estimate-v1" />

## Python SDK

```python
from taco import EstimateV1

estimate = EstimateV1.model_validate(json_data)
print(estimate.summary.grand_total)
```

:::info Contributing
This schema is defined. See the [JSON Schema file](https://github.com/pelles-ai/taco/blob/main/spec/schemas/estimate-v1.json) for the full specification. Feedback and improvements welcome via [GitHub Issues](https://github.com/pelles-ai/taco/issues).
:::
