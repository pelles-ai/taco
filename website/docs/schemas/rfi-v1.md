---
title: "rfi-v1 — Request for Information"
description: RFI schema for design conflicts, missing information, and clarifications — with drawing references and priority levels.
---

import SchemaExplorer from '@site/src/components/SchemaExplorer';

# rfi-v1 — Request for Information

The RFI schema defines a standardized format for construction Requests for Information. It captures design conflicts, missing information, and clarification requests, complete with drawing references, bounding-box markups, and priority levels.

An RFI is the typed output of agents that audit drawings, specs, or coordinated BIM models against project context. Downstream agents (design teams, owners, GCs) consume it as machine-readable design feedback.

<SchemaExplorer schemaId="rfi-v1" />

## Python SDK

```python
from taco import RFIV1

# Parse from JSON
rfi = RFIV1.model_validate(json_data)

# Access with snake_case
print(rfi.subject)
print(rfi.references[0].sheet_id)
print(rfi.priority)

# Serialize to camelCase JSON
output = rfi.model_dump(by_alias=True, exclude_none=True)
```

## See also

- [Task types: `rfi-generation`, `rfi-response`](../task-types) — workflows that produce and consume RFIs
- [JSON Schema source](https://github.com/pelles-ai/taco/blob/main/spec/schemas/rfi-v1.json)
