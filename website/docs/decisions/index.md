---
title: Architecture Decision Records
description: The major design decisions behind TACO — what we chose, why we chose it, and what the alternatives were. Each ADR captures the context, the decision, and the consequences we accept.
sidebar_position: 0
---

# Architecture Decision Records

These ADRs document the load-bearing design decisions behind TACO. Each one captures the **context** that made the decision necessary, the **alternatives** we considered, the **decision** we landed on, and the **consequences** — both the wins and the costs we accept.

The format follows the [Michael Nygard ADR template](https://github.com/joelparkerhenderson/architecture-decision-record). New ADRs are appended; existing ADRs are only superseded, not edited (revision history matters when reasoning about a protocol over time).

## Status legend

- **Accepted** — the decision is in effect and reflected in the current SDK
- **Proposed** — under discussion, not yet implemented
- **Superseded** — replaced by a later ADR (linked)
- **Deprecated** — no longer in effect; documented for historical reasoning

## Index

| # | Title | Status |
|---|------|--------|
| [0001](./build-on-a2a) | Build on A2A rather than designing a new transport | Accepted |
| [0002](./json-schema-source-of-truth) | JSON Schema 2020-12 as the schema source of truth | Accepted |
| [0003](./construction-shaped-scopes) | Construction-shaped OAuth scope taxonomy | Accepted |
| [0004](./sidecar-pattern) | Sidecar pattern for platform integration | Accepted |
| [0005](./in-memory-registry-first) | In-memory registry first, hosted registry second | Accepted |
| [0006](./schema-versioning) | Schema versioning: additive within a major, rename for breaking | Accepted |
| [0007](./v1-wire-cutover) | Phased A2A v1 wire cutover (compat → features → wire flip) | Accepted (in flight) |
| [0008](./pyodide-sandbox) | Pyodide for the in-browser sandbox | Accepted |
| [0009](./extension-uri-naming) | Construction extension URI naming convention | Accepted |

## When to write a new ADR

Write one when:

- A design decision will outlive any single contributor (i.e. a future maintainer would want to know *why*)
- The decision has reasonable alternatives, and choosing one closes off the others
- The decision has costs we accept, not just upside
- Someone is going to ask "why did you do it that way?" in a year and the answer is non-obvious from the code

Skip the ADR if it's a routine implementation choice, a one-line refactor, or something well-covered by existing docs.

## Contributing

[Open a PR](https://github.com/pelles-ai/taco/edit/main/website/docs/decisions/) adding a new ADR. Number it sequentially; never reuse a number. Keep them short (one screen ideally; two screens max) — ADRs are reference material, not essays.
