---
title: ADR-0007 — Phased A2A v1 wire cutover
description: Why the SDK adopts A2A v1.0.2 in phases (pre-bump polish → compat-layer port → per-concern wire flip, with additive v1 features in parallel) rather than a single coordinated jump.
sidebar_position: 7
---

# ADR-0007 — Phased A2A v1 wire cutover

**Status:** Accepted (mid-execution)
**Date:** 2026-05-10

## Context

A2A protocol v1.0 (and the Python `a2a-sdk` 1.0.2) shipped with significant wire-format changes from v0.3 (the version TACO had been built on through v0.3.x). The changes include:

- `Part` discriminator removed (`Part(root=TextPart(...))` → `Part(text=...)`)
- Enums in SCREAMING_SNAKE_CASE with type prefixes (`TaskState.completed` → `TaskState.TASK_STATE_COMPLETED`)
- JSON-RPC method renames (`message/send` → `SendMessage`; `tasks/get` → `GetTask`; new `ListTasks`)
- Stream-event format wrapper-keyed (`{"taskStatusUpdate": {…}}` instead of `{"kind": "taskStatusUpdate", "final": true, …}`)
- AgentCard restructure (top-level `url`/`protocolVersion`/`preferredTransport` consolidated into `supportedInterfaces[]`)
- New formal `extensions[]` arrays on Message/Artifact/Task/AgentCapabilities
- Well-known path change (`/.well-known/agent.json` → `/.well-known/agent-card.json`); TACO already made this move early (see Phase 1 below)
- HTTP+JSON URL prefix dropped (`POST /v1/message:send` → `POST /message:send`)

The original v1 migration plan (drafted before `a2a-sdk` 1.0.2 actually shipped) assumed a one-line dependency bump using the v0.3 compatibility shim. That plan was incomplete — the released v1 SDK also restructured several internal modules TACO depends on (`A2AFastAPIApplication` removed, `a2a.utils.message/parts/artifact` removed, request handlers moved). A single-PR cutover would have meant a massive, hard-to-review change with high regression risk.

## Decision

Adopt v1 in phases, each made of small PRs that ship independently. The phase numbers match the live plan in [`sdk/V1_MIGRATION.md`](https://github.com/pelles-ai/taco/blob/main/sdk/V1_MIGRATION.md); versions below are the git tags each change first shipped in.

- **Phase 1 — Pre-bump polish (still on `a2a-sdk` 0.3.x).** Prefer `/.well-known/agent-card.json` in the client, registry, and CLI, with fallback to the legacy `/.well-known/agent.json` (the server serves both); pin `a2a-sdk>=0.3.25,<1` so a v1 install could not break the SDK before it was ready; rewrite the migration guide; send the `A2A-Version` header on outbound requests. **Status: shipped** (pin in v0.3.3, well-known path in v0.3.4, migration guide in v0.3.5, `A2A-Version` header in v0.3.6).

- **Phase 2 — SDK adoption via the compat layer.** Bump to `a2a-sdk>=1.0.2,<2`. Use the v0.3 compat layer (`a2a.compat.v0_3.types`) so the wire format stays v0.3. Rewrite TACO's internal imports to match the new module structure (e.g. `LegacyRequestHandler` + `create_jsonrpc_routes(enable_v0_3_compat=True)` instead of the removed `A2AFastAPIApplication`). **Status: shipped in v0.3.7.**

- **Phase 3 — Wire cutover.** Flip the on-the-wire JSON dialect from v0.3 to v1.0 one concern at a time: `Part` constructors, enum literals, the agent card's `supportedInterfaces[]`, JSON-RPC method names (`SendMessage`, `GetTask`), and the stream-event wrapper format. Coordinate this across the SDK so producers and consumers flip together. The target release is not fixed yet. **Status: scoped, not started.**

- **Phase 4 — Additive v1 features.** Land v1 features that don't change the wire format of existing operations, each as its own PR. These did not need to wait for Phase 3 and have been landing since Phase 2: `ListTasks` RPC (v0.3.8), the canonical `x-construction` extension URI declaration (v0.3.9), `reference_task_ids` (v0.3.10), `return_immediately` (v0.3.11), and multiple push-notification configs per task (v0.3.13). **Status: in progress.** Still open: JWS agent-card signing and surfacing mTLS / PKCE / device-code support on `SecurityExt`.

## Alternatives considered

### Single coordinated cutover

Pros: avoids the awkward middle state where TACO advertises v1 features over a v0.3 wire dialect.

Cons:
- The diff is enormous. Code review quality degrades; regression risk multiplies. A single PR carrying all of it would be too large to review meaningfully.
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
- Phase 3 isn't yet scheduled. Users asking "when will TACO be v1?" get "TACO's *SDK* is on `a2a-sdk` 1.x; TACO's *wire* flips in Phase 3 — release and date TBD."
- The compat shim adds a runtime translation cost per request. Negligible in practice, but real.

### Reversibility

The compat layer is upstream-maintained; we can keep using it as long as `a2a-sdk` ships it. Phase 3 is the one-way door: once we flip the wire to v1, agents that haven't upgraded stop being able to talk to upgraded peers. We commit to clear migration tooling (a `taco upgrade` CLI command that checks and migrates an agent card, for instance) before Phase 3 ships.

## References

- [`sdk/V1_MIGRATION.md`](https://github.com/pelles-ai/taco/blob/main/sdk/V1_MIGRATION.md) — the live migration tracking doc
- [A2A v1.0 release notes](https://a2a-protocol.org)
- [ADR-0001 — Build on A2A](./build-on-a2a) — the original commitment this cutover honors
