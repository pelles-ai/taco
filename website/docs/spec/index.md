---
title: Specification
description: Formal numbered specification documents for TACO. Normative SHALL/SHOULD/MAY language; each spec is versioned and dated.
sidebar_position: 0
---

# TACO Specification

The TACO specification is published as a set of numbered, dated documents. Each spec defines normative requirements using [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) keywords (SHALL, SHOULD, MAY) and references the canonical schemas, agent card extensions, and protocol behavior expected of compliant implementations.

The prose docs elsewhere on this site (`/docs/agent-card-extensions`, `/docs/security`, etc.) are *companion* material — easier to read but not normative. When the two disagree, **the spec documents win**.

:::info Spec vs. ADRs vs. prose
- **Spec documents** answer *what compliance requires*. RFC 2119 language. Versioned.
- **ADRs** answer *why we chose what we chose*. See [Architecture Decisions](../decisions/).
- **Prose docs** answer *how to think about it* and *how to use it*. Companion material.

If you're implementing a TACO agent, the spec is the source of truth.
If you're trying to understand the design, start with the prose, then read the spec.
:::

## Spec index

| # | Title | Status | Version |
|---|------|--------|---------|
| [SPEC-001](./SPEC-001-agent-cards) | Agent Cards & Discovery | Provisional | 0.3 |
| [SPEC-002](./SPEC-002-task-types) | Task Types | Provisional | 0.3 |
| [SPEC-003](./SPEC-003-data-schemas) | Data Schemas | Provisional | 0.3 |
| [SPEC-004](./SPEC-004-security) | Security & Authentication | Provisional | 0.3 |
| [SPEC-005](./SPEC-005-conformance) | Conformance | Provisional | 0.3 |

## Status definitions

- **Stable** — implemented and verified; suitable for production. No spec is Stable yet.
- **Provisional** — implementable today against the 0.3 SDK, but still subject to revision in the next minor version. Every spec is Provisional while the protocol is 0.x.
- **Deprecated** — superseded; documented for historical reasoning

## Versioning

Spec versions follow a strict additive policy (see [ADR-0006](../decisions/schema-versioning)):

- **Patch updates** (1.0 → 1.0.1) — clarifications and typo fixes only; no normative changes.
- **Minor updates** (1.0 → 1.1) — additive only. New optional requirements, expanded recommendations.
- **Major updates** (1.x → 2.0) — breaking changes. New requirements that existing compliant implementations would fail.

Once a spec reaches Stable, its major version is **permanent**: SPEC-001 1.0 will mean what it means on the day it ships, forever, and a 2.0 (if ever) lives at a new URL. Provisional specs at 0.x can still change between minor versions; each change is recorded in the changelog.

## Conventions

All spec documents use:

- **SHALL / SHALL NOT** — absolute requirement / prohibition
- **SHOULD / SHOULD NOT** — recommendation, with documented exceptions allowed
- **MAY** — optional behavior

References to schemas, fields, and identifiers use `code formatting`. References to other spec documents use `[SPEC-NNN]`.

## How to propose a change

Spec changes follow the same RFC process as TACO at large:

1. Open a GitHub issue with the proposed change and rationale
2. Discussion and review in the issue or in [GitHub Discussions](https://github.com/pelles-ai/taco/discussions)
3. If accepted, a PR updates the spec document; the changelog entry references the issue
4. Major version bumps require a corresponding ADR

[Open a spec issue →](https://github.com/pelles-ai/taco/issues/new)
