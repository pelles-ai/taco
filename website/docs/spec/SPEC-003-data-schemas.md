---
title: "SPEC-003 — Data Schemas"
description: Normative requirements for the canonical TACO JSON schemas — publication, naming, versioning, and validation behavior.
sidebar_position: 3
---

# SPEC-003 — Data Schemas

**Status:** Provisional
**Version:** 0.3
**Date:** 2026-05-25

## 1. Introduction

This specification defines how TACO canonical data schemas are published, named, validated, and evolved.

The key words **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 2. Schema authoring

### 2.1 Source of truth

TACO canonical schemas **SHALL** be authored as [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/schema) documents, committed to the repository at [`spec/schemas/{name}-vN.json`](https://github.com/pelles-ai/taco/tree/main/spec/schemas).

The JSON Schema document is the **single source of truth**. SDK models (Pydantic, future TypeScript) mirror the schema but are not authoritative; when they disagree, the schema wins.

This decision is recorded in [ADR-0002](../decisions/json-schema-source-of-truth).

### 2.2 Publication

Each canonical schema's `$id` is of the form:

```
https://taco-protocol.dev/schemas/{name}-vN.json
```

The `$id` is the schema's identifier. The TACO website does not currently serve schema documents at that URL or any other. Until a stable hosted URL exists, the canonical, publicly readable copy of each schema is the file in [`spec/schemas/`](https://github.com/pelles-ai/taco/tree/main/spec/schemas) on the repository's `main` branch, which tooling can fetch over HTTPS without authentication.

## 3. Schema identification

### 3.1 Naming

Canonical schemas **SHALL** be named using the pattern:

```
{lowercase-domain-noun}-v{major-version}
```

Examples: `bom-v1`, `rfi-v1`, `estimate-v1`, `quote-v1`, `schedule-v1`, `change-order-v1`.

Names **SHALL** use kebab-case for the domain noun. The major version suffix **SHALL** be `-v` followed by a positive integer.

### 3.2 Bare names in agent cards

When a TACO Agent Card's skill declares `inputSchema` or `outputSchema` as a bare name (no URL prefix), a bare name that matches a canonical TACO schema **SHALL** refer to that schema, defined in `spec/schemas/{name}.json`.

Bare names that do not match any canonical TACO schema (for example `plan-sheets`, used as an input identifier in the canonical agent-card extension spec) are not standardized. Conformance checks **SHOULD** flag them as warnings. The reference SDK does not check schema identifiers.

### 3.3 Full URL references

A skill **MAY** declare a non-canonical, vendor-defined schema by giving a fully-qualified `https://` URL in `inputSchema` or `outputSchema`. The URL **SHOULD** resolve to a JSON Schema document. Such schemas are not standardized but are valid for vendor-specific workflows.

## 4. Validation semantics

### 4.1 Strict validation

Validation against a canonical TACO schema **SHALL** be performed with strict semantics:

- Required fields are required
- Field types are checked
- Enum values are checked
- Unknown fields are handled according to the schema (see below)

None of the six canonical schemas sets `additionalProperties`, so under JSON Schema's default, unknown properties are currently permitted and pass validation. Producers **SHOULD NOT** add fields beyond what the schema declares, and consumers **SHOULD** ignore unknown properties rather than reject the payload.

### 4.2 Extending TACO schemas

Vendors who need fields beyond the canonical schema **SHOULD NOT** add them inline to a canonical-schema-typed artifact. They **SHOULD**:

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

Any change in the SHALL NOT list above **SHALL** mint a new major version (e.g. `bom-v2`) with a new name and `$id`. The new major **SHALL** coexist with the old; agents **MAY** support either or both via separate skills.

## 6. Required schema metadata

Every canonical TACO schema document **SHALL** contain:

| JSON Schema field | Required value |
|------|------|
| `$schema` | `"https://json-schema.org/draft/2020-12/schema"` |
| `$id` | The schema's canonical identifier URI (currently `https://taco-protocol.dev/schemas/{name}.json`) |
| `title` | A human-readable title |
| `description` | One-paragraph description of what the schema models |

### 6.1 Common payload metadata

Every canonical TACO **payload** (the JSON object an agent produces, as distinct from the schema itself) **SHALL** include a `metadata` object containing at minimum:

| Field | Type | Required |
|------|------|--------|
| `generatedBy` | string | SHALL — identifier of the producing agent |
| `generatedAt` | string (ISO 8601 date-time) | SHALL — when this artifact was generated |
| `confidence` | number (0-1) | MAY — overall confidence score |

Schemas whose `metadata` definition (inline or via `$ref`) doesn't include these requirements are non-conformant to this spec. All six canonical schemas require `generatedBy` and `generatedAt`.

## 7. The canonical schema set

As of this spec version, six canonical TACO schemas are defined:

| Schema | `$id` | Source file |
|------|--------|--------|
| [`bom-v1`](../schemas/bom-v1) | `https://taco-protocol.dev/schemas/bom-v1.json` | [`spec/schemas/bom-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/bom-v1.json) |
| [`rfi-v1`](../schemas/rfi-v1) | `https://taco-protocol.dev/schemas/rfi-v1.json` | [`spec/schemas/rfi-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/rfi-v1.json) |
| [`estimate-v1`](../schemas/estimate-v1) | `https://taco-protocol.dev/schemas/estimate-v1.json` | [`spec/schemas/estimate-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/estimate-v1.json) |
| [`quote-v1`](../schemas/quote-v1) | `https://taco-protocol.dev/schemas/quote-v1.json` | [`spec/schemas/quote-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/quote-v1.json) |
| [`schedule-v1`](../schemas/schedule-v1) | `https://taco-protocol.dev/schemas/schedule-v1.json` | [`spec/schemas/schedule-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/schedule-v1.json) |
| [`change-order-v1`](../schemas/change-order-v1) | `https://taco-protocol.dev/schemas/change-order-v1.json` | [`spec/schemas/change-order-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/change-order-v1.json) |

Additional schemas may be added in future minor versions of this spec (additive). Removing a schema would require a major version bump.

## 8. Companion material

- [Data Schemas index](../schemas/) — a page per canonical schema
- [ADR-0002 — JSON Schema as source of truth](../decisions/json-schema-source-of-truth)
- [ADR-0006 — Schema versioning policy](../decisions/schema-versioning)
