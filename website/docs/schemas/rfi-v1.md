---
title: "rfi-v1 — Request for Information"
description: RFI schema for design conflicts, missing information, and clarifications — with drawing references and priority levels.
---

import SchemaExplorer, {SchemaExample} from '@site/src/components/SchemaExplorer';

# rfi-v1 — Request for Information

The RFI schema defines a standardized format for construction Requests for Information. It captures design conflicts, missing information, and clarification requests with drawing references and priority levels.

**JSON Schema:** [`spec/schemas/rfi-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/rfi-v1.json)

## Fields

Generated from [`spec/schemas/rfi-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/rfi-v1.json). Open a field to see what it holds, or switch to **Validate** to check a payload of your own.

<SchemaExplorer schemaId="rfi-v1" />

## Example

<SchemaExample schemaId="rfi-v1" />

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
