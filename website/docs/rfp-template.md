---
title: RFP Template
description: Copy-paste boilerplate owners and GCs can drop into RFPs to require TACO compatibility from vendors and agent providers. Includes evaluation criteria, scoring rubric, and verification via the conformance runner.
sidebar_position: 7
---

# RFP Template — TACO compatibility

This page is a copy-paste artifact for owners and GCs writing RFPs that should require **TACO-compatible** behavior from candidate vendors and agent providers. Lift the sections below verbatim into your RFP, or use them as a starting point for your procurement team.

The goal: move the conversation from "does your platform have an API?" (everyone says yes; the APIs don't talk to each other) to "does your platform speak TACO?" (a question with a verifiable answer via the [conformance runner](/conformance)).

:::tip Quick start for procurement
1. Lift the **[required capabilities](#required-capabilities)** section into your RFP as mandatory items.
2. Lift the **[scoring rubric](#scoring-rubric)** as your evaluation framework.
3. Tell respondents to demonstrate compliance using the [conformance runner](/conformance).
4. Use the **[citation block](#citation-block)** in your background materials.
:::

---

## Required capabilities

> The vendor SHALL provide an agent endpoint conforming to the TACO protocol (https://taco-protocol.com) with the following capabilities:
>
> **1. Agent Card discoverability.** The endpoint SHALL serve a valid Agent Card document at `/.well-known/agent-card.json` (preferred) or `/.well-known/agent.json` (legacy fallback), reachable without authentication for purposes of capability discovery.
>
> **2. Construction extension declaration.** The Agent Card SHALL declare the TACO construction extension under either the inline `x-construction` field or the canonical extension URI `https://taco.construction/extensions/x-construction/v1` in `capabilities.extensions[]`.
>
> **3. Trade scoping.** The `x-construction.trade` field SHALL be set to one of the recognized TACO trades: `mechanical`, `electrical`, `plumbing`, `structural`, `civil`, `architectural`, `fire-protection`, `general`, `multi-trade`.
>
> **4. CSI division scoping.** Where applicable, the Agent Card SHALL declare the `x-construction.csiDivisions[]` field with valid 2-digit MasterFormat division numbers covering the vendor's scope.
>
> **5. Typed skill advertisement.** Each capability the vendor provides SHALL be declared as a `skill` with a `taskType` field set to a recognized TACO task type (see https://taco-protocol.com/docs/task-types), an optional `inputSchema`, and an `outputSchema` either referencing a TACO canonical schema (`bom-v1`, `rfi-v1`, `estimate-v1`, `quote-v1`, `schedule-v1`, `change-order-v1`) or a fully-qualified URL pointing at a vendor-defined JSON Schema.
>
> **6. Schema conformance.** All artifacts emitted by the vendor's agent SHALL validate strictly (with `additionalProperties: false` semantics) against their declared output schema. Vendor-defined extensions to canonical TACO schemas SHALL be additive only and SHALL NOT modify existing field semantics.
>
> **7. Security declarations.** Where the vendor's agent requires authentication, the Agent Card SHALL declare matching `securitySchemes` and `security[]` requirements that are internally consistent (every name in `security[]` references a key in `securitySchemes`).
>
> **8. Task lifecycle adherence.** The vendor's agent SHALL emit tasks that progress through standard A2A lifecycle states (`submitted` → `working` → `completed` / `failed` / `canceled`) and SHALL distinguish system failures (`failed` state) from typed business outcomes (`completed` state with a structured rejection or no-result artifact).

---

## Recommended capabilities

> The vendor SHOULD additionally provide:
>
> **9. Health endpoint.** A `GET /health` endpoint returning HTTP 200 when the agent is operational, suitable for load-balancer and orchestrator health checks.
>
> **10. Streaming support.** Where the agent's work is long-running (>10 seconds typical response time), it SHOULD implement A2A `message/stream` (Server-Sent Events) emitting `TaskStatusUpdateEvent` records as work progresses.
>
> **11. Push notification subscribers.** Where appropriate, the agent SHOULD implement A2A push-notification subscriber registration (`tasks/pushNotificationConfig/set` and related), supporting multiple concurrent subscribers per task.
>
> **12. Token Exchange compliance.** For agents that delegate work downstream, the agent SHOULD implement RFC 8693 Token Exchange to narrow received tokens before calling downstream agents, holding only the authority required for each hop.
>
> **13. Telemetry hooks.** The agent SHOULD emit OpenTelemetry spans for the request lifecycle, tagged with the task ID, context ID, and agent identifier.
>
> **14. Conformance attestation.** The vendor SHOULD provide evidence of having run the public TACO conformance runner against their endpoint, with a timestamped report demonstrating a passing result for all required capabilities.

---

## Scoring rubric

| Criterion | Weight | Evaluation |
|----------|--------|---------------------|
| Required capabilities — all met | Pass/Fail | Demonstrated via [conformance runner](/conformance); any fail on required capabilities disqualifies the response. |
| Recommended capabilities (count met) | 20% | Score = (recommended count met) / 6 × 20. |
| Trust tier | 15% | Tier 0 (unverified) = 0; Tier 1 (org verified) = 10; Tier 2 (cert attested) = 15. |
| Schema coverage breadth | 15% | Number of TACO canonical schemas the agent produces or consumes as declared. |
| Documented integrations | 10% | Number of platform integrations declared in `x-construction.integrations[]` that match the buyer's existing stack. |
| Streaming + observability quality | 10% | Demonstrated via vendor-provided OpenTelemetry trace samples for a representative workflow. |
| Documentation completeness | 10% | Vendor agent has a publicly accessible doc page or README describing supported task types, schemas, and auth model. |
| Migration support for protocol updates | 10% | Vendor commits to tracking A2A and TACO version changes within a stated window (e.g. one minor version per quarter). |
| Pricing transparency for TACO traffic | 10% | Vendor's pricing for agent-driven traffic is documented (not "contact sales"). |

A typical evaluation lands a candidate in 60–85 range; below 50 suggests the vendor isn't ready and the buyer should expect significant integration overhead.

---

## Verification — point at the conformance runner

> To verify compliance, the buyer's evaluator SHALL navigate to the TACO conformance runner at `https://taco-protocol.com/conformance`, enter the vendor's agent URL, and capture the resulting report as part of the response file. The runner is browser-based and produces a per-check report with structured remediation notes for any failed item.

The conformance runner is open source and verifiable. Vendors can self-test before responding; buyers can re-run independently. This eliminates the "documentation says X but the API does Y" gap that plagues construction software RFPs.

---

## Citation block

For background material in the RFP or supporting documents:

> **TACO** (The A2A Construction Open-standard) — an open-source construction ontology layer built on the [A2A protocol](https://a2a-protocol.org) (Linux Foundation), licensed Apache 2.0. TACO defines a shared vocabulary of typed JSON schemas (`bom-v1`, `rfi-v1`, `estimate-v1`, `quote-v1`, `schedule-v1`, `change-order-v1`), 18 named construction task types, a construction extension to A2A Agent Cards, and a security scope taxonomy for multi-organizational workflows. Reference SDK in Python (`taco-agent` on PyPI); schemas published as JSON Schema 2020-12 at `https://taco-protocol.com/schemas/`. Conformance testing available at `https://taco-protocol.com/conformance`. See `https://taco-protocol.com/docs/standards` for alignment with CSI MasterFormat, OmniClass, ISO 19650, IFC, and other construction industry standards.

---

## Sample RFP question set

Drop these into the response form:

> **Q1.** Provide the URL of your agent endpoint and confirm reachability of the Agent Card at `/.well-known/agent-card.json`.
>
> **Q2.** Attach the output of the TACO conformance runner (`https://taco-protocol.com/conformance`) executed against your endpoint, dated within 30 days of response submission.
>
> **Q3.** Enumerate the TACO task types your agent advertises, along with their declared `inputSchema` and `outputSchema` for each.
>
> **Q4.** Describe your agent's trust tier and provide supporting verification (e.g. domain ownership proof for tier 1; SOC2 / ISO 27001 certificate for tier 2).
>
> **Q5.** Describe your authentication model and confirm support for OAuth 2.0 with RFC 8693 Token Exchange for downstream delegation.
>
> **Q6.** Confirm your commitment to tracking TACO and A2A protocol updates within [BUYER-STATED WINDOW] of upstream release.
>
> **Q7.** Provide a sample OpenTelemetry trace from a representative workflow invocation.
>
> **Q8.** Describe your incident response and security disclosure process.

---

## Why an RFP-compatible standard matters now

The construction software RFP of 2026 has a hidden problem: every vendor checks every box, but the boxes don't agree on what they mean. "Open API" means three different things in three RFPs. "Discoverable" means "documented" in some and "queryable from a registry" in others. "Interoperable" almost always means "can be made to work via integration code your team writes."

TACO compatibility is verifiable. The conformance runner is real. The schemas are public. Vendors can either pass the test or not. The space for "interpretation" closes.

This is the simplest thing buyers can do to push the construction software market toward genuine interoperability: ask for TACO compatibility in your RFPs, score it honestly, and prefer vendors who can produce a conformance report over those who can't.

---

## See also

- [Conformance runner](/conformance) — the verification target this RFP language references
- [Standards Alignment](./standards) — supporting material on what TACO aligns with
- [For Owners](/for/owner) — the longer framing for owner-side decision-makers
- [For Platform Vendors](/for/platform-vendor) — what vendors need to do to respond to TACO-compliant RFPs
- [Compare to alternatives](./compare) — why TACO and not proprietary APIs
