---
title: "SPEC-005 — Conformance"
description: Defines what TACO conformance means, the test suite for verifying it, and the trust model for attestations.
sidebar_position: 5
---

# SPEC-005 — Conformance

**Status:** Provisional
**Version:** 0.3
**Date:** 2026-05-25

## 1. Introduction

This specification defines TACO conformance: what claims a "TACO-compliant" agent makes, how those claims are verified, and how attestations are produced.

The key words **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 2. What conformance covers

TACO conformance per this spec verifies the **structural** correctness of an agent — the shape of its Agent Card, the validity of its declarations, the consistency of its advertised capabilities.

Conformance per this spec does **NOT** verify:

- Semantic quality of the agent's outputs (a syntactically-conformant estimator may still produce bad estimates)
- Real end-to-end task execution against every advertised skill (covered separately by SPEC-005.x in future revisions)
- Performance characteristics (latency, throughput, streaming behavior)
- Non-A2A behaviors (mTLS handshake correctness, internal data handling)

Future revisions of this spec **MAY** add behavioral conformance categories. This version is structural-only.

## 3. Required conformance checks

A TACO-compliant agent **SHALL** pass all of the following checks. A hosted conformance runner that automates these checks is planned; until then, `taco inspect <url>` shows the card fields the checks examine (name, version, URL, `x-construction`, and each skill's task type and schemas), and `taco discover <url>` prints the full card JSON, including `capabilities` and any security declarations.

### 3.1 Agent card reachable

`GET /.well-known/agent-card.json` (or, as a fallback, `GET /.well-known/agent.json`) **SHALL** return:

- HTTP 200 OK
- Valid JSON
- A document containing at minimum the fields required by [SPEC-001 §3](./SPEC-001-agent-cards)

### 3.2 Required top-level fields

The Agent Card **SHALL** include `name`, `description`, `version`, and `url` per [SPEC-001 §3](./SPEC-001-agent-cards).

### 3.3 At least one skill

The Agent Card **SHALL** declare at least one entry in `skills[]`. Agents with no skills are not useful TACO citizens.

### 3.4 Construction extension declared

The Agent Card **SHALL** carry the inline `x-construction` field, per [SPEC-001 §4](./SPEC-001-agent-cards). It **SHOULD** also list the canonical URI in `capabilities.extensions[]`; a missing URI declaration **SHALL** be flagged as a warning.

### 3.5 Recognized trade

`x-construction.trade` **SHALL** be one of the recognized trades from [SPEC-001 §5.1](./SPEC-001-agent-cards). The reference SDK rejects cards with any other value, so a non-recognized trade is a failure. New trades are proposed through the RFC process.

### 3.6 Valid CSI divisions

Every entry in `x-construction.csiDivisions[]` **SHALL** match the format defined in [SPEC-001 §5.2](./SPEC-001-agent-cards) (two-digit string).

### 3.7 Recognized task types

Every `skills[].x-construction.taskType` **SHOULD** be one of the recognized task types from [SPEC-002 §2](./SPEC-002-task-types). Non-recognized types **SHALL** be flagged as warnings.

### 3.8 Recognized or URL-formatted schemas

Every skill **SHALL** declare `x-construction.outputSchema`. Every `skills[].x-construction.inputSchema` and `skills[].x-construction.outputSchema` **SHOULD** be either:

- A bare name matching a canonical TACO schema name from [SPEC-003 §7](./SPEC-003-data-schemas), OR
- A fully-qualified `https://` URL

Other bare names **SHALL** be flagged as warnings, per [SPEC-003 §3.2](./SPEC-003-data-schemas).

### 3.9 Security declaration consistency

When `security[]` is present, every named scheme **SHALL** have a matching key in `securitySchemes` per [SPEC-004 §2.2](./SPEC-004-security).

## 4. Recommended conformance checks

A TACO-compliant agent **SHOULD** pass the following additional checks. Failure of a recommended check is not a conformance failure but is captured in the report.

### 4.1 Health endpoint

`GET /health` **SHOULD** return HTTP 200 when the agent is operational.

### 4.2 Streaming support

For skills whose typical response time exceeds 10 seconds, the agent **SHOULD** implement A2A `message/stream` (Server-Sent Events).

### 4.3 Push notification subscribers

For long-running tasks, the agent **SHOULD** implement A2A push notification subscriber registration with support for multiple concurrent subscribers per task.

### 4.4 Token Exchange

For agents that call downstream agents, RFC 8693 Token Exchange **SHOULD** be implemented per [SPEC-004 §4](./SPEC-004-security).

### 4.5 Telemetry

The agent **SHOULD** emit OpenTelemetry spans for the request lifecycle, tagged with task ID, context ID, and agent identifier.

### 4.6 Documentation

The agent **SHOULD** have a publicly accessible documentation page or README describing supported task types, schemas, and authentication model.

## 5. The conformance runner (planned)

A hosted reference runner for the structural checks above is planned; it is not yet available, and there is no conformance page on the TACO site. The planned runner would:

- Operate entirely in the visitor's browser (no central service tracks tests)
- Make cross-origin fetches to the agent's well-known path
- Produce a structured report with per-check pass/fail/skip status and remediation hints
- Handle CORS failures gracefully and offer an equivalent curl invocation

Agents tested by a browser-based runner would need a CORS configuration that permits the runner's origin (see [SPEC-001 §2.2](./SPEC-001-agent-cards)). Until the runner exists, operators can review the checks by hand with `taco inspect <url>` and `taco discover <url>`, or with curl against the well-known path.

## 6. Attestation

A passing conformance report is an attestation, not a certification. Once the planned runner exists, the attestation:

- Is timestamped (the moment the runner executed)
- Is reproducible by anyone running the checks against the same URL
- Carries no signature or trust authority — it is a structural test, not a certifying authority

Owners and procurement teams **MAY** treat a recent (within 30 days) passing conformance report as evidence of structural compliance suitable for RFP responses.

## 7. Future work

Subsequent versions of this spec **MAY** extend conformance with:

- **SPEC-005.1** — Behavioral conformance: per-skill task-call testing with reference payloads
- **SPEC-005.2** — Performance conformance: latency and throughput baselines for declared skills
- **SPEC-005.3** — Conformance attestation registry: cryptographically signed reports issued by accredited testers

These are not in scope for this version of the spec.

## 8. Companion material

- [SPEC-001 — Agent Cards](./SPEC-001-agent-cards)
- [SPEC-002 — Task Types](./SPEC-002-task-types)
- [SPEC-003 — Data Schemas](./SPEC-003-data-schemas)
- [SPEC-004 — Security & Authentication](./SPEC-004-security)
