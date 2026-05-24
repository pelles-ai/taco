---
sidebar_position: 4
title: Data Schemas
description: Typed JSON schemas for construction artifacts — bom-v1, rfi-v1, estimate-v1, schedule-v1, quote-v1, change-order-v1.
---

import SchemaGraph from '@site/src/components/SchemaGraph';

# Data Schemas

TACO defines typed JSON schemas for construction artifacts. These schemas ensure that the output from one agent is valid input for the next — enabling multi-agent workflows without custom integration code.

All schemas follow [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/schema) and use camelCase field names in their JSON representation. The Python SDK provides Pydantic models with snake_case Python attributes that serialize to the correct camelCase JSON.

## How the schemas relate

<SchemaGraph />

## Available schemas

| Schema | Status | Description |
|--------|--------|-------------|
| [`bom-v1`](./bom-v1) | **Defined** | Bill of Materials — line items, quantities, materials, alternates |
| [`rfi-v1`](./rfi-v1) | **Defined** | Request for Information — questions, references, priorities |
| [`estimate-v1`](./estimate-v1) | **Defined** | Cost Estimate — line items, labor, materials, summary |
| [`quote-v1`](./quote-v1) | **Defined** | Supplier Quote — pricing, terms, availability |
| [`schedule-v1`](./schedule-v1) | **Defined** | Project Schedule — activities, dependencies, milestones |
| [`change-order-v1`](./change-order-v1) | **Defined** | Change Order — impact analysis, cost/schedule deltas |

Every schema page includes a live JSON validator. Paste your data, see the errors highlighted.

## Schema design principles

1. **Flat where possible.** Schemas avoid deep nesting. A BOM is a flat list of line items with metadata.
2. **Required fields are minimal.** Only fields that every instance must have are required. Everything else is optional.
3. **Confidence scores.** Schemas include a `confidence` field (0-1) in metadata so downstream agents can assess reliability.
4. **Provenance.** Every schema includes `generatedBy` and `generatedAt` in metadata for traceability.

## JSON Schema files

The canonical JSON Schema definitions live in the repository at [`spec/schemas/`](https://github.com/pelles-ai/taco/tree/main/spec/schemas) and are also served directly from this site for tooling:

- [`/schemas/bom-v1.json`](/schemas/bom-v1.json)
- [`/schemas/rfi-v1.json`](/schemas/rfi-v1.json)
- [`/schemas/estimate-v1.json`](/schemas/estimate-v1.json)
- [`/schemas/quote-v1.json`](/schemas/quote-v1.json)
- [`/schemas/schedule-v1.json`](/schemas/schedule-v1.json)
- [`/schemas/change-order-v1.json`](/schemas/change-order-v1.json)

## Python SDK models

The SDK provides Pydantic v2 models for all defined schemas:

```python
from taco import BOMV1, RFIV1, EstimateV1, QuoteV1, ScheduleV1, ChangeOrderV1

# Validate incoming JSON against the schema
bom = BOMV1.model_validate(json_data)

# Access fields with snake_case
print(bom.project_id)
print(bom.line_items[0].description)

# Serialize to camelCase JSON
json_output = bom.model_dump(by_alias=True, exclude_none=True)
```
