---
title: "SPEC-003 — Data Schemas"
description: Normative requirements for the canonical TACO JSON schemas — publication, naming, versioning, and validation behavior.
sidebar_position: 3
---

# SPEC-003 — Data Schemas

**Status:** Stable
**Version:** 1.0
**Date:** 2026-05-25

## 1. Introduction

This specification defines how TACO canonical data schemas are published, named, validated, and evolved.

The key words **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 2. Schema authoring

### 2.1 Source of truth

TACO canonical schemas **SHALL** be authored as [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/schema) documents, committed to the repository at `/spec/schemas/{name}-vN.json`.

The JSON Schema document is the **single source of truth**. SDK models (Pydantic, future TypeScript) mirror the schema but are not authoritative; when they disagree, the schema wins.

This decision is recorded in [ADR-0002](../decisions/json-schema-source-of-truth).

### 2.2 Publication

Each canonical schema **SHALL** be published at the stable URL:

```
https://taco-protocol.com/schemas/{name}-vN.json
```

The document at that URL **SHALL** be the byte-identical canonical version. Conformance testers and downstream tooling **SHALL** be able to fetch the schema via HTTPS without authentication.

## 3. Schema identification

### 3.1 Naming

Canonical schemas **SHALL** be named using the pattern:

```
{lowercase-domain-noun}-v{major-version}
```

Examples: `bom-v1`, `rfi-v1`, `estimate-v1`, `quote-v1`, `schedule-v1`, `change-order-v1`.

Names **SHALL** use kebab-case for the domain noun. The major version suffix **SHALL** be `-v` followed by a positive integer.

### 3.2 Bare names in agent cards

When a TACO Agent Card's skill declares `inputSchema` or `outputSchema` as a bare name (no URL prefix), the bare name **SHALL** refer to the canonical TACO schema at `https://taco-protocol.com/schemas/{name}.json`.

Bare names that do not match any canonical TACO schema **SHALL** be considered invalid.

### 3.3 Full URL references

A skill **MAY** declare a non-canonical, vendor-defined schema by giving a fully-qualified `https://` URL in `inputSchema` or `outputSchema`. The URL **SHALL** resolve to a JSON Schema document. Such schemas are not standardized but are valid for vendor-specific workflows.

## 4. Validation semantics

### 4.1 Strict validation

Validation against a canonical TACO schema **SHALL** be performed with strict semantics:

- Required fields are required
- Field types are checked
- Enum values are checked
- Unknown top-level fields are permitted only when the schema explicitly sets `additionalProperties: true`

The default `additionalProperties` policy in canonical TACO schemas is `false` — extra fields are an error. Producers **SHALL NOT** add fields beyond what the schema declares.

### 4.2 Extending TACO schemas

Vendors who need fields beyond the canonical schema **SHALL NOT** add them inline to a canonical-schema-typed artifact. They **SHOULD**:

- Use the existing `metadata` object's vendor-prefixed sub-keys (e.g. `metadata.vendorExtensions.acme.foo`), where the canonical schema permits, OR
- Publish their own vendor schema and reference it via full URL in their agent card

## 5. Versioning

Schema versioning follows the policy in [ADR-0006](../decisions/schema-versioning):

### 5.1 Permanent identifiers

A versioned schema name (e.g. `bom-v1`) is **permanent**. The semantic contract of `bom-v1` shall not change once published widely.

### 5.2 Additive evolution within a major

Within a major version (e.g. `bom-v1`), the following changes are permitted:

- **SHALL** be permitted: adding new optional fields, adding new enum values
- **SHOULD** be cautious: enum-value additions can break strict-enum validators; consider the deployed ecosystem before adding

The following changes **SHALL NOT** be permitted within a major:

- Adding required fields
- Removing fields
- Changing field types
- Renaming fields
- Removing enum values
- Changing the semantic meaning of an existing field

### 5.3 Breaking changes mint a new major

Any change in the SHALL NOT list above **SHALL** mint a new major version (e.g. `bom-v2`) at a new URL. The new major **SHALL** coexist with the old; agents **MAY** support either or both via separate skills.

## 6. Required schema metadata

Every canonical TACO schema document **SHALL** contain:

| JSON Schema field | Required value |
|------|------|
| `$schema` | `"https://json-schema.org/draft/2020-12/schema"` |
| `$id` | The canonical URL at which the schema is published |
| `title` | A human-readable title |
| `description` | One-paragraph description of what the schema models |

### 6.1 Common payload metadata

Every canonical TACO **payload** (the JSON object an agent produces, as distinct from the schema itself) **SHALL** include a `metadata` object containing at minimum:

| Field | Type | Required |
|------|------|--------|
| `generatedBy` | string | SHALL — identifier of the producing agent |
| `generatedAt` | string (ISO 8601 date-time) | SHALL — when this artifact was generated |
| `confidence` | number (0-1) | MAY — overall confidence score |

Schemas that don't include these requirements in their `properties.metadata` definition are non-conformant to this spec.

## 7. The canonical schema set

As of this spec version, six canonical TACO schemas are defined:

| Schema | Published | Spec section |
|------|--------|--------|
| [`bom-v1`](../schemas/bom-v1) | `https://taco-protocol.com/schemas/bom-v1.json` | This spec |
| [`rfi-v1`](../schemas/rfi-v1) | `https://taco-protocol.com/schemas/rfi-v1.json` | This spec |
| [`estimate-v1`](../schemas/estimate-v1) | `https://taco-protocol.com/schemas/estimate-v1.json` | This spec |
| [`quote-v1`](../schemas/quote-v1) | `https://taco-protocol.com/schemas/quote-v1.json` | This spec |
| [`schedule-v1`](../schemas/schedule-v1) | `https://taco-protocol.com/schemas/schedule-v1.json` | This spec |
| [`change-order-v1`](../schemas/change-order-v1) | `https://taco-protocol.com/schemas/change-order-v1.json` | This spec |

Additional schemas may be added in future minor versions of this spec (additive). Removing a schema would require a major version bump.

## 8. Companion material

- [Data Schemas index](../schemas/) — interactive schema explorer
- [ADR-0002 — JSON Schema as source of truth](../decisions/json-schema-source-of-truth)
- [ADR-0006 — Schema versioning policy](../decisions/schema-versioning)
