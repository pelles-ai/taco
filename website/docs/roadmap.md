---
sidebar_position: 1
title: Roadmap
description: What's shipped, what's next, and where TACO is heading. v1 protocol migration, expanded schemas, and the path to a real ecosystem.
---

# Roadmap

TACO is being built in the open. This page captures what has shipped, what is in flight, and where the project is heading. For the authoritative log, see the [CHANGELOG](https://github.com/pelles-ai/taco/blob/main/CHANGELOG.md).

## Shipped

### v0.3 — Foundations (Q1 2026)
- Construction Agent Card extensions (`x-construction` field with trade, CSI divisions, project types, integrations)
- Six typed data schemas: `bom-v1`, `rfi-v1`, `estimate-v1`, `schedule-v1`, `quote-v1`, `change-order-v1`
- 18 named task types organized by project phase
- A2A v1.0 SDK adoption via the v0.3 compat layer — on-the-wire JSON unchanged
- Multi push-notification subscribers per task
- JSON-file-backed task persistence (`JsonFileTaskStore`)
- Admin authentication for skill mutation endpoints
- mTLS, PKCE, and OAuth Device Code flow declarations on `SecurityExt`

## In flight

### A2A v1 wire cutover (Phase 3 of the SDK migration)
The TACO SDK is on `a2a-sdk>=1.0.2`, but the on-the-wire JSON is still v0.3. Phase 3 flips the wire format to v1 — new method names (`SendMessage`, `GetTask`, `ListTasks`), new stream event shape, new `extensions[]` arrays, the JWS-signed Agent Card field, and the `/.well-known/agent-card.json` path as primary.

See [`sdk/V1_MIGRATION.md`](https://github.com/pelles-ai/taco/blob/main/sdk/V1_MIGRATION.md) for the full plan.

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

## Next

### Registry as a public service
The `AgentRegistry` is in-process today with optional JSON persistence. We are scoping a publicly hosted registry that supports the three trust tiers (Unverified, Org Verified, Cert Attested) and exposes discovery by trade, CSI division, and task type.

### Construction-specific MCP server bundle
A reference set of [MCP](/docs/protocol-stack) servers for common construction data sources (drawings, BIM, specifications, project DBs) so any TACO agent can plug in without inventing its own connectors.

### Conformance test suite
A test pack that an agent can run against its own endpoint to verify TACO compliance — schema round-trips, advertised task types, auth declarations.

## Open questions

These are open for community input. Drop into [GitHub Discussions](https://github.com/pelles-ai/taco/discussions) if you have a take.

- **Cross-project entity identity.** How does an estimator agent reference the same "project" an architect agent is talking about, when they live in different platforms?
- **Schema versioning policy.** When does `bom-v1` become `bom-v2`? Additive vs. breaking?
- **Trust tier mechanics.** Who runs the certification process for tier 2 (Cert Attested)? A foundation, a working group, or a delegated registrar set?

## How to influence the roadmap

- File an issue with a concrete proposal: [github.com/pelles-ai/taco/issues](https://github.com/pelles-ai/taco/issues)
- Start a discussion: [github.com/pelles-ai/taco/discussions](https://github.com/pelles-ai/taco/discussions)
- Ship a reference implementation that proves a point — that is the fastest way to move the spec
