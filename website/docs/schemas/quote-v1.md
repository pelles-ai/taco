---
title: "quote-v1 — Supplier Quote"
description: Supplier material quote schema — pricing, availability, lead times, and terms.
---

import SchemaExplorer from '@site/src/components/SchemaExplorer';

# quote-v1 — Supplier Quote

The Quote schema defines a standardized format for supplier material quotes. It captures pricing, availability, lead times, and terms.

A quote is what a supplier (or supplier-side agent) returns when asked to price a [`bom-v1`](./bom-v1). Procurement, estimating, or value-engineering agents consume the typed quote to make ordering decisions.

<SchemaExplorer schemaId="quote-v1" />

## Python SDK

```python
from taco import QuoteV1

quote = QuoteV1.model_validate(json_data)
print(quote.supplier.name, quote.valid_until)
for item in quote.items:
    print(item.sku, item.unit_price, item.lead_time_days)
output = quote.model_dump(by_alias=True, exclude_none=True)
```

## See also

- [`bom-v1`](./bom-v1) — the typical input that a quote prices
- [Task type: `material-procurement`](../task-types) — the workflow that produces quotes
- [JSON Schema source](https://github.com/pelles-ai/taco/blob/main/spec/schemas/quote-v1.json)
