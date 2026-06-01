---
title: ADR-0006 — Schema versioning policy
description: Additive within a major version, rename for breaking changes. Why bom-v1 stays bom-v1 forever even as we add fields, and what triggers a bom-v2.
sidebar_position: 6
---

# ADR-0006 — Schema versioning policy

**Status:** Accepted
**Date:** 2026-03-25

## Context

Construction software outlives every individual contract. A BOM emitted by a takeoff agent in 2026 may be referenced in a change order in 2029. If the schema for a BOM changes between those dates in a way that breaks readers, the project's audit trail breaks with it.

But we also need to *evolve* schemas. New fields will become necessary. Some current fields will prove badly designed. The question is: how do we change schemas without breaking the agents that depend on them?

JSON Schema, Pydantic, and Protocol Buffers each have established answers. We had to pick one and write it down explicitly so future maintainers don't quietly drift.

## Decision

TACO schemas follow a **strict additive-within-a-major** policy:

1. **A versioned name is permanent.** `bom-v1` means what it means today, forever. If we need a different shape, we publish `bom-v2`. Old agents keep producing `bom-v1`; new agents can negotiate which they support via the Agent Card.

2. **Additive changes within a major are always allowed.** New optional fields can be added to `bom-v1` over time. Existing readers ignore unknown fields; writers can populate them when supported.

3. **No required-field additions, ever.** Adding a required field to `bom-v1` would break every existing producer. If the field is truly required, that's a `bom-v2` change.

4. **No field-type changes, ever.** Changing `quantity` from number to string is breaking even if "looks like" it's just a refinement.

5. **No field renames, ever.** Renames are equivalent to "remove + add"; both halves break agents.

6. **No enum-value removals.** Adding an enum value (e.g. a new `unit` in `bom-v1`) is allowed but should be done conservatively — old validators will reject it.

7. **Deprecation is documented, not enforced.** A field can be marked `"deprecated": true` in the JSON Schema; it stays in the schema until the next major.

A schema deprecation page lives at the version's doc page; the deprecation reason and the recommended successor field/schema are explicit.

## Alternatives considered

### Semver-style versioning (`bom-v1.2`, `bom-v1.3`)

Pros: matches developer intuition; minor versions communicate "compatible additions."

Cons: implies a major-version freedom that ours doesn't have. We commit to additive-only within a major; calling new releases "minor" is redundant. Worse, "v1.2" in a URL suggests "v1.3 is coming and old code might need updating to track it" — exactly the friction we're avoiding.

### Date-based versioning (`bom-2026-03`)

Pros: every change gets a new identifier; no ambiguity about which version produced what.

Cons: explosion of version identifiers in code (each agent supports a list of dates?); no clean way to express "any compatible version." Loses the contract that `bom-v1` is a stable target you can write code against.

### No versioning, schemas evolve in place

Pros: simplest, no proliferation.

Cons: every schema change is a breaking change for some downstream. Audit trails reference "the schema" without specifying which version. We've seen this pattern fail badly in older construction file formats.

## Consequences

### Positive

- A project's audit trail is stable. A `bom-v1` artifact stored in 2026 reads correctly in 2030 even if `bom-v2` exists by then.
- The versioned name itself is the API contract. No "API version" header, no negotiation per request — the type identifies its own version.
- Agents can support multiple versions simultaneously by advertising different skills (`generate-bom-v1`, `generate-bom-v2`). The registry filters do the work.
- New optional fields can land without coordination across the ecosystem.

### Negative

- A genuinely-bad design decision in `bom-v1` (e.g. ambiguous units, unfortunate field name) can't be fixed without minting `bom-v2` and asking the ecosystem to migrate. That's a real cost.
- Carrying two versions of a schema in agent registries doubles the surface area of "what task type produces what."
- The decision to call something a major version is judgment. Some changes feel borderline (e.g. adding a discriminator field to a polymorphic union). We err toward "if in doubt, mint a new major."

### Reversibility

Reversible for unreleased schemas. Once a schema is `v1`, the versioning policy is binding by definition — flipping the policy would itself be a major breakage. We treat the policy as a constitutional-level commitment.

## What triggers a new major version

The bar for `bom-v2` (or any `*-v2`) is high. We expect to mint a new major version when:

- The semantic identity of an existing field changes (e.g. `quantity` becomes "total quantity including waste" instead of "net quantity")
- A required field has to be added that no existing producer emits
- The schema's logical scope shifts (e.g. `bom-v2` covers civil scopes, requiring different unit conventions)
- Industry alignment forces a wire-level change (e.g. an ISO standard publishes a normalized form)

Cosmetic improvements, new optional fields, additional enum values, doc clarifications — none of these warrant a major bump.

## References

- [Data Schemas index](/docs/schemas/)
- [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/schema)
- [ADR-0002 — JSON Schema as source of truth](./json-schema-source-of-truth)
