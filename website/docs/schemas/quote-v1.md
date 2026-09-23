---
title: "quote-v1 — Supplier Quote"
description: Supplier material quote schema — pricing, availability, lead times, and terms.
---

# quote-v1 — Supplier Quote

The Quote schema defines a standardized format for supplier material quotes. It captures pricing, availability, lead times, and terms.

**JSON Schema:** [`spec/schemas/quote-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/quote-v1.json)

**Status:** Defined. The schema structure is complete and implemented in the SDK.

## Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `projectId` | string | Unique project identifier |
| `supplierName` | string | Supplier company name |
| `quoteNumber` | string | Supplier's quote reference number |
| `validUntil` | string (date) | Quote expiration date |
| `lineItems` | array | Quoted line items with pricing |
| `summary` | object | Totals: subtotal, tax, freight, total |
| `terms` | object | Payment terms, delivery, warranty |
| `metadata` | object | Generation metadata with confidence score |

## Line Item Fields

| Field | Type | Description |
|-------|------|-------------|
| `bomItemId` | string | Reference to the BOM line item ID |
| `description` | string | Material description |
| `quantity` | number | Quoted quantity |
| `unit` | string | Unit of measure |
| `unitPrice` | number | Price per unit |
| `extendedPrice` | number | Total price for this line |
| `manufacturer` | string | Manufacturer name |
| `partNumber` | string | Part number |
| `leadTimeDays` | integer | Delivery lead time in days |
| `availability` | string | Stock status |

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
