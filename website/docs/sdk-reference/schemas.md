---
title: "Schema lookup"
description: "Find the Pydantic model for a canonical schema name such as `bom-v1`. The models themselves have interactive pages under Data Schemas."
sidebar_position: 11
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Schema lookup

Find the Pydantic model for a canonical schema name such as `bom-v1`. The models themselves have interactive pages under Data Schemas.

## `get_schema_model()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/schemas.py#L507)

```python
get_schema_model(schema_id: 'str') -> 'type[SchemaModel]'
```

Return the model for a canonical schema name such as ``"bom-v1"``.

``schema_id`` is the bare name used in ``inputSchema`` / ``outputSchema``
(SPEC-003 §3.2). Raises :class:`KeyError` naming the known ids when it is
not a canonical TACO schema.

### `SCHEMA_MODELS`

```python
SCHEMA_MODELS: Mapping = {
    "bom-v1": BOMV1,
    "change-order-v1": ChangeOrderV1,
    "estimate-v1": EstimateV1,
    "quote-v1": QuoteV1,
    "rfi-v1": RFIV1,
    "schedule-v1": ScheduleV1,
}
```

## See also

- [Data Schemas](/docs/schemas/)
- [SDK Guide: data schema models](/docs/sdk#data-schema-models)
- [ADR-0002: JSON Schema as source of truth](/docs/decisions/json-schema-source-of-truth)

