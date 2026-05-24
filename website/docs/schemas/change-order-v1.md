---
title: "change-order-v1 — Change Order"
description: Change order analysis schema — cost impact, schedule impact, and scope modifications.
---

import SchemaExplorer from '@site/src/components/SchemaExplorer';

# change-order-v1 — Change Order

The Change Order schema defines a standardized format for construction change order analysis, including cost impact, schedule impact, and scope modifications.

Change orders are how scope changes get tracked, costed, and approved. A change-order agent typically consumes the current [`estimate-v1`](./estimate-v1) and [`schedule-v1`](./schedule-v1) and emits a `change-order-v1` describing the delta.

<SchemaExplorer schemaId="change-order-v1" />

## Python SDK

```python
from taco import ChangeOrderV1

co = ChangeOrderV1.model_validate(json_data)
print(co.description)
print(co.cost_impact.amount, co.cost_impact.currency)
output = co.model_dump(by_alias=True, exclude_none=True)
```

## See also

- [`estimate-v1`](./estimate-v1) — typical input for cost-impact analysis
- [`schedule-v1`](./schedule-v1) — typical input for schedule-impact analysis
- [Task type: `change-order-analysis`](../task-types)
- [JSON Schema source](https://github.com/pelles-ai/taco/blob/main/spec/schemas/change-order-v1.json)
