---
title: "quote-v1 — Supplier Quote"
description: Supplier material quote schema — pricing, availability, lead times, and terms.
---

import SchemaExplorer, {SchemaExample} from '@site/src/components/SchemaExplorer';

# quote-v1 — Supplier Quote

The Quote schema defines a standardized format for supplier material quotes. It captures pricing, availability, lead times, and terms.

**JSON Schema:** [`spec/schemas/quote-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/quote-v1.json)

**Status:** Defined. The schema structure is complete and implemented in the SDK.

## Fields

Generated from [`spec/schemas/quote-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/quote-v1.json). Open a field to see what it holds, or switch to **Validate** to check a payload of your own.

<SchemaExplorer schemaId="quote-v1" />

## Example

<SchemaExample schemaId="quote-v1" />

## Python SDK

```python
from taco import QuoteV1

quote = QuoteV1.model_validate(json_data)
print(quote.summary.total)
print(quote.terms.payment_terms)
```

:::info Contributing
This schema is defined. See the [JSON Schema file](https://github.com/pelles-ai/taco/blob/main/spec/schemas/quote-v1.json) for the full specification. Feedback and improvements welcome via [GitHub Issues](https://github.com/pelles-ai/taco/issues).
:::
