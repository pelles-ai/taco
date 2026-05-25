---
title: ADR-0007 — Phased A2A v1 wire cutover
description: Why the SDK adopts A2A v1.0.2 in three phases (compat layer → wire flip per concern → final v1 only) rather than a single coordinated jump.
sidebar_position: 7
---

# ADR-0007 — Phased A2A v1 wire cutover

**Status:** Accepted (mid-execution)
**Date:** 2026-05-10

## Context

A2A v1.0.2 shipped with significant wire-format changes from v0.3 (the version TACO had been built on through v0.3.x). The changes include:

- `Part` discriminator removed (`Part(root=TextPart(...))` → `Part(text=...)`)
- Enums in SCREAMING_SNAKE_CASE with type prefixes (`TaskState.completed` → `TaskState.TASK_STATE_COMPLETED`)
- JSON-RPC method renames (`message/send` → `SendMessage`; `tasks/get` → `GetTask`; new `ListTasks`)
- Stream-event format wrapper-keyed (`{"taskStatusUpdate": {…}}` instead of `{"kind": "taskStatusUpdate", "final": true, …}`)
- AgentCard restructure (top-level `url`/`protocolVersion`/`preferredTransport` consolidated into `supportedInterfaces[]`)
- New formal `extensions[]` arrays on Message/Artifact/Task/AgentCapabilities
- Well-known path change (`/.well-known/agent.json` → `/.well-known/agent-card.json`)
- HTTP+JSON URL prefix dropped (`POST /v1/message:send` → `POST /message:send`)

The original v1 migration plan (drafted before `a2a-sdk` 1.0.2 actually shipped) assumed a one-line dependency bump using the v0.3 compatibility shim. That plan was incomplete — the released v1 SDK also restructured several internal modules TACO depends on (`A2AFastAPIApplication` removed, `a2a.utils.message/parts/artifact` removed, request handlers moved). A single-PR cutover would have meant a massive, hard-to-review change with high regression risk.

## Decision

Adopt v1 in **three phases**, each landing as a self-contained epic that ships independently:

- **Phase 1 — SDK adoption.** Bump to `a2a-sdk>=1.0.2,<2`. Use the v0.3 compat layer (`a2a.compat.v0_3.types`) so the wire format stays v0.3. Rewrite TACO's internal imports to match the new module structure (e.g. `LegacyRequestHandler` + `create_jsonrpc_routes(enable_v0_3_compat=True)` instead of the removed `A2AFastAPIApplication`). **Status: shipped in v0.3.3.**

- **Phase 2 — Wire-compatible v1 features.** Land v1-only features that are additive: `ListTasks` RPC, multi push-notification configs, `reference_task_ids`, `return_immediately`, the `A2A-Version` header, the canonical `x-construction` extension URI declaration. Each is its own PR; the wire format for existing operations stays v0.3. **Status: shipped in v0.3.4–0.3.11.**

- **Phase 3 — Wire cutover.** Flip the on-the-wire JSON dialect from v0.3 to v1.0 for the agent card, `SendMessage`, `GetTask`, stream events, and the well-known path. Coordinate this across the SDK so producers and consumers flip together. Ship as v0.4 (or v1.0 of `taco-agent` itself — version naming TBD). **Status: scoped, not started.**

## Alternatives considered

### Single coordinated cutover

Pros: avoids the awkward middle state where TACO advertises v1 features over a v0.3 wire dialect.

Cons:
- The diff is enormous. Code review quality degrades; regression risk multiplies. We saw an early prototype of this approach as one PR; nobody could meaningfully review it.
- All v1-only features (ListTasks, multi push configs, `reference_task_ids`) would be blocked until the cutover lands. The migration would take months of feature freeze.
- A bug in any one wire-level change would block the whole release. Phased lets us roll back individual concerns.

### Skip the compat layer; jump to v1 wire directly

Pros: simpler conceptually; no "compat shim" overhead.

Cons:
- All existing TACO clients would break the moment we ship. Adoption velocity hits zero.
- We'd have to coordinate the cutover with every TACO deployment in the world before we could ship — and there isn't yet a registry to discover them.
- The compat layer is provided by `a2a-sdk` upstream; using it costs us nothing.

### Fork off a `taco-v1` package and let v0.3 die slowly

Pros: maintains backward compatibility for laggards by parallel maintenance.

Cons:
- Doubles maintenance burden indefinitely.
- Fragments the ecosystem: agents on `taco-agent` (v0.3 wire) and agents on `taco-v1` (v1 wire) can't talk without a translator.
- We don't have the bandwidth to maintain two SDKs.

## Consequences

### Positive

- Each phase is a small enough change to review and roll back individually.
- v1-only features (ListTasks, multi push configs) land for users *now* without waiting for the wire cutover.
- The compat layer means existing TACO clients keep working byte-identically until Phase 3 ships. No surprise breakages.
- Phase 3 itself becomes a smaller scope: just the wire-format flip, not "the wire flip plus all the new v1 features."

### Negative

- Awkward middle state. TACO 0.3.x advertises v1 features but speaks v0.3 wire. A user reading the SDK code who doesn't know about the compat layer can be confused.
- Phase 3 isn't yet scheduled. Users asking "when will TACO be v1?" get "TACO's *SDK* is on v1; TACO's *wire* will flip in v0.4 — date TBD."
- The compat shim adds a runtime translation cost per request. Negligible in practice, but real.

### Reversibility

The compat layer is upstream-maintained; we can keep using it as long as `a2a-sdk` ships it. Phase 3 is the one-way door: once we flip the wire to v1, agents that haven't upgraded stop being able to talk to upgraded peers. We commit to clear migration tooling (a `taco upgrade` CLI command that checks and migrates an agent card, for instance) before Phase 3 ships.

## References

- [`sdk/V1_MIGRATION.md`](https://github.com/pelles-ai/taco/blob/main/sdk/V1_MIGRATION.md) — the live migration tracking doc
- [A2A v1.0 release notes](https://a2a-protocol.org)
- [ADR-0001 — Build on A2A](./build-on-a2a) — the original commitment this cutover honors
