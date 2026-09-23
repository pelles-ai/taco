---
sidebar_position: 1
title: Roadmap
description: What's shipped, what's next, and where TACO is heading. v1 protocol migration, expanded schemas, and the path to a real ecosystem.
---

# Roadmap

TACO is being built in the open. This page captures what has shipped, what is in flight, and where the project is heading. For the authoritative log, see the [CHANGELOG](https://github.com/pelles-ai/taco/blob/main/CHANGELOG.md).

## Shipped

Dates come from the release tags in the repository. See the [CHANGELOG](https://github.com/pelles-ai/taco/blob/main/CHANGELOG.md) for detail.

### v0.0–v0.3.2 — Foundations (March 2026)
- Construction Agent Card extensions (`x-construction` field with trade, CSI divisions, project types, integrations)
- Six typed data schemas: `bom-v1`, `rfi-v1`, `estimate-v1`, `schedule-v1`, `quote-v1`, `change-order-v1`
- 18 named task types organized by project phase
- Security spec: scope taxonomy, trust tiers, token delegation
- `TacoClient`, in-process `AgentRegistry` with trade / task-type filtering, and the `taco` CLI (`discover`, `inspect`, `send`, `health`)
- `A2AServer` with `GET /health`, streaming handlers, and opt-in admin endpoints for skill mutation (protected by `admin_auth_token`)
- `TacoAgent` with peer discovery from `agents.yaml`, and the opt-in Agent Monitor UI at `/monitor`
- HTTP header forwarding on `TacoClient` and `TacoAgent`
- Pluggable task persistence (`task_store`) with `JsonFileTaskStore`
- LangGraph adapter for wrapping LangGraph agents as TACO agents

### v0.3.3–v0.3.13 — A2A v1 groundwork (May 2026)
- `a2a-sdk` 1.0 adopted via the v0.3 compat layer — on-the-wire JSON unchanged
- `/.well-known/agent-card.json` as the primary discovery path, with fallback to the legacy `/.well-known/agent.json`
- `A2A-Version` header on every outbound request from the client, registry, and CLI
- `ListTasks` support: `TacoClient.list_tasks()` with cursor pagination and the `taco list-tasks` CLI subcommand
- Canonical `x-construction` extension URI, declared under `capabilities.extensions[]` alongside the inline field
- `reference_task_ids` for linking follow-up tasks (RFI responses, change-order approvals)
- `return_immediately` for fire-and-forget sends
- Multiple push-notification configs per task

### v0.3.14–v0.3.15 — Fixes (September 2026)
- Streaming handlers work on `a2a-sdk` 1.1 (chunks share one artifact id; first chunk created, later chunks appended)
- Package builds on hatchling 1.28+ (the SDK ships its own `sdk/README.md`)

## In flight

### A2A v1 wire cutover (Phase 3 of the SDK migration)
The TACO SDK is on `a2a-sdk>=1.0.2`, but the on-the-wire JSON is still v0.3. Phase 3 flips the wire format to v1 one concern at a time: flattened `Part` constructors, v1 enum literals, `supportedInterfaces[]` on the Agent Card, new JSON-RPC method names (`SendMessage`, `GetTask`, and so on), and the wrapper-keyed stream event shape.

See [`sdk/V1_MIGRATION.md`](https://github.com/pelles-ai/taco/blob/main/sdk/V1_MIGRATION.md) for the full plan and [ADR-0007](/docs/decisions/v1-wire-cutover) for the reasoning.

### Remaining v1 features
Still open in the migration plan:
- JWS-signed Agent Cards (`signatures[]`), tied to `SecurityExt.trust_tier`
- mTLS, PKCE-required, and OAuth Device Code declarations on `SecurityExt`

## Next

No dates or commitments here; these are the directions the project expects to take.

### Schema breadth
Of the 18 task types defined, six have full schemas today. The next batch:
- `bid-comparison-v1` — for the `bid-leveling` task type
- `submittal-review-v1` — for `submittal-review`
- `clash-report-v1` — for `clash-detection`
- `safety-report-v1` — for `safety-compliance`
- `progress-report-v1` — for `progress-tracking`

[Open a schema proposal](https://github.com/pelles-ai/taco/issues/new) if you have strong opinions about field naming or what should be required.

### Reference implementations
- LLM-driven sandbox demo (in `examples/`) — keep working as the v1 wire format lands
- A starter "platform sidecar" template for vendors who want to wrap an existing product

### Registry as a public service
The `AgentRegistry` is in-process today with optional JSON persistence. A publicly hosted registry is under consideration: one that understands the three trust tiers (Unverified, Org Verified, Cert Attested) and exposes discovery by trade, CSI division, and task type.

### Construction-specific MCP server bundle
A reference set of [MCP](/docs/protocol-stack) servers for common construction data sources (drawings, BIM, specifications, project DBs) so any TACO agent can plug in without inventing its own connectors.

### Conformance test suite
A test pack that an agent can run against its own endpoint to verify TACO compliance — schema round-trips, advertised task types, auth declarations. What conformance means is drafted in [SPEC-005](/docs/spec/SPEC-005-conformance); until a runner exists, `taco inspect <url>` is the quickest check of a live Agent Card.

## Open questions

These are open for community input. Drop into [GitHub Discussions](https://github.com/pelles-ai/taco/discussions) if you have a take.

- **Cross-project entity identity.** How does an estimator agent reference the same "project" an architect agent is talking about, when they live in different platforms?
- **Trust tier mechanics.** Who runs the certification process for tier 2 (Cert Attested)? A foundation, a working group, or a delegated registrar set?

Settled since earlier drafts of this page: schema versioning is additive within a major version, with a rename for breaking changes ([ADR-0006](/docs/decisions/schema-versioning)).

## How to influence the roadmap

- File an issue with a concrete proposal: [github.com/pelles-ai/taco/issues](https://github.com/pelles-ai/taco/issues)
- Start a discussion: [github.com/pelles-ai/taco/discussions](https://github.com/pelles-ai/taco/discussions)
- Ship a reference implementation that proves a point — that is the fastest way to move the spec
