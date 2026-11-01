---
title: "bom-v1 — Bill of Materials"
description: Standardized Bill of Materials schema — line items, quantities, materials, sizes, and provenance for construction takeoffs.
---

import SchemaExplorer, {SchemaExample} from '@site/src/components/SchemaExplorer';

# bom-v1 — Bill of Materials

The Bill of Materials schema defines a standardized format for construction material takeoffs. It captures line items with quantities, materials, sizes, and provenance metadata.

**JSON Schema:** [`spec/schemas/bom-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/bom-v1.json)

## Fields

Generated from [`spec/schemas/bom-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/bom-v1.json). Open a field to see what it holds, or switch to **Validate** to check a payload of your own.

<SchemaExplorer schemaId="bom-v1" />

## Example

<SchemaExample schemaId="bom-v1" />

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
