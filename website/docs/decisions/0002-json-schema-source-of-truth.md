---
title: ADR-0002 — JSON Schema 2020-12 as the schema source of truth
description: Why TACO's data schemas are authored as JSON Schema 2020-12 files, with Pydantic models written to mirror them — not the other way around.
sidebar_position: 2
---

# ADR-0002 — JSON Schema 2020-12 as the schema source of truth

**Status:** Accepted
**Date:** 2026-02-22

## Context

Every typed protocol has the same question on day one: **what is the canonical form of a schema?**

For a Python-first SDK, the obvious answer is "Pydantic models" — they're ergonomic to write, they validate at runtime, and the IDE understands them. For a JSON-first protocol, the obvious answer is "JSON Schema files" — language-neutral, validatable from any runtime, and standardized.

These two answers point at different futures. Pick the Python source and JS, Go, and Java SDKs all have to derive their types from a Python tool. Pick the JSON Schema source and the Python SDK becomes a thin wrapper that mirrors the schemas (and could eventually be generated from them).

## Decision

TACO's schemas are authored as **JSON Schema 2020-12** files committed at [`/spec/schemas/`](https://github.com/pelles-ai/taco/tree/main/spec/schemas). The Pydantic models in `taco/schemas.py` mirror those files faithfully but are not the source of truth. When the JSON Schema changes, the Python models must change to match.

Both forms ship: the canonical JSON Schema files live in the repository at [`spec/schemas/`](https://github.com/pelles-ai/taco/tree/main/spec/schemas), each identified by its `$id` (for example `https://taco-protocol.dev/schemas/bom-v1.json`), and each has a reference page under [Data Schemas](/docs/schemas/); the Pydantic models are part of the `taco-agent` package. The site does not yet serve the schema documents themselves.

## Alternatives considered

### Pydantic models as source

Pros: best Python ergonomics, single edit to add a field, `model_dump()` and `model_validate()` for free.

Cons:
- Non-Python SDKs have to either reverse-engineer the JSON Schema from Pydantic's `model_json_schema()` (lossy in subtle ways — defaults, optional handling, JSON Schema-isms Pydantic doesn't fully emit) or wait for a maintainer to hand-translate.
- The protocol's authoritative form lives behind a Python import. Not friendly for non-Python ecosystems, not friendly for spec auditing, not friendly for downstream tooling that wants to codegen.
- Schema validators in other languages (ajv for JS, jsonschema for Go, every-language) all consume JSON Schema natively. Asking them to consume Python is a non-starter.

### dataclasses

Pros: stdlib, no runtime dependency.

Cons:
- No validation. The whole point of typed schemas is rejecting bad input early.
- Worse codegen story than Pydantic anyway.

### Protocol Buffers

Pros: well-understood codegen across languages, compact wire format.

Cons:
- A2A's wire format is JSON, not protobuf. Mixing protobuf source-of-truth with JSON-on-the-wire creates a translation layer at every boundary.
- Protobuf's type system maps imperfectly onto JSON Schema (`oneof`, `optional`, enum encoding all differ).
- Construction artifacts (BOMs, RFIs, schedules) are read by humans during debugging. JSON beats binary for human inspection.

## Consequences

### Positive

- Any JSON Schema 2020-12 validator can check a payload against the exact files in `spec/schemas/`, with no TACO code involved.
- Other-language SDKs (a future TypeScript SDK, for instance) can be generated directly from `spec/schemas/*.json` using off-the-shelf JSON Schema codegen.
- RFP responses that ask "where is your schema definition?" can point to a single file per schema in `spec/schemas/`, no Python install required.
- Static analysis tools that consume JSON Schema (linters, mock generators, contract testers) work out of the box.

### Negative

- Adding a field is a two-step change: edit the JSON Schema, then update the Pydantic model. We accept this drift risk in exchange for portability.
- The Pydantic model isn't auto-generated today, so it can drift from the JSON Schema. A future test that asserts `model.model_json_schema() == authoritative_schema` would close this gap; until then, code review catches it.
- Some Pydantic-isms (custom validators, complex unions) are awkward to express in JSON Schema. We resist the urge to add them; if a constraint can't live in the JSON Schema, it shouldn't be enforced by the canonical model either.

### Reversibility

Reversible if we ever find a Python-source workflow that round-trips losslessly to JSON Schema. Pydantic v2's `model_json_schema()` is close but not quite there for all of JSON Schema 2020-12. If a future Pydantic version closes the gap, we could flip the source-of-truth — the on-the-wire JSON wouldn't change.

## References

- [JSON Schema 2020-12 specification](https://json-schema.org/draft/2020-12/schema)
- [Data Schemas](/docs/schemas/)
- [`spec/schemas/`](https://github.com/pelles-ai/taco/tree/main/spec/schemas)
- [`taco.schemas`](/docs/sdk-reference/) (the Pydantic mirror)
