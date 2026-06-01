---
title: "SPEC-002 — Task Types"
description: Normative requirements for declaring, dispatching, and naming TACO task types.
sidebar_position: 2
---

# SPEC-002 — Task Types

**Status:** Stable
**Version:** 1.0
**Date:** 2026-05-25

## 1. Introduction

This specification defines the requirements for TACO task types — the vocabulary of named construction workflows an agent can advertise and execute.

The key words **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 2. Recognized task types

A TACO-compliant agent's `skills[].taskType` field **SHOULD** reference one of the 18 recognized task types defined in this section. Task types not listed here **MAY** be used but **SHOULD** be proposed for standardization (see §6).

### 2.1 Preconstruction

| Task Type | Typical Input | Output Schema |
|----------|---------------|---------------|
| `takeoff` | Plan sheets | `bom-v1` |
| `estimate` | `bom-v1` | `estimate-v1` |
| `bid-leveling` | Multiple `estimate-v1` | `bid-comparison-v1` *(planned)* |
| `value-engineering` | `bom-v1` + `estimate-v1` | `ve-suggestions-v1` *(planned)* |
| `scope-review` | Spec documents, `bom-v1` | `scope-report-v1` *(planned)* |
| `plan-comparison` | Two sets of plan sheets | `plan-delta-v1` *(planned)* |

### 2.2 Document Management

| Task Type | Typical Input | Output Schema |
|----------|---------------|---------------|
| `rfi-generation` | Plan sheets, `bom-v1` | `rfi-v1` |
| `rfi-response` | `rfi-v1` | `rfi-response-v1` *(planned)* |
| `submittal-review` | Submittal documents, specs | `submittal-review-v1` *(planned)* |
| `spec-compliance-check` | `bom-v1`, spec documents | `compliance-report-v1` *(planned)* |
| `change-order-analysis` | Change order docs, `bom-v1`, `schedule-v1` | `change-order-v1` |
| `drawing-markup` | Plan sheets | Marked-up plan sheets |

### 2.3 Field + Coordination

| Task Type | Typical Input | Output Schema |
|----------|---------------|---------------|
| `schedule-coordination` | `bom-v1`, `estimate-v1`, constraints | `schedule-v1` |
| `material-procurement` | `bom-v1` | `quote-v1` |
| `clash-detection` | BIM models, multi-trade `bom-v1` | `clash-report-v1` *(planned)* |
| `safety-compliance` | Site data, plan sheets | `safety-report-v1` *(planned)* |
| `progress-tracking` | Site photos/scans, `schedule-v1` | `progress-report-v1` *(planned)* |
| `punch-list` | Inspection data, photos | `punch-list-v1` *(planned)* |

## 3. Naming conventions

Task type identifiers **SHALL**:

- Use **kebab-case** (lowercase ASCII, words separated by hyphens)
- Match the regex `^[a-z][a-z0-9-]*[a-z0-9]$`
- Be 3-50 characters long

Task type identifiers **SHOULD**:

- Be descriptive verbs or verb phrases (`takeoff`, `estimate`, `rfi-generation`)
- Avoid trade-specific prefixes (use `estimate`, not `mech-estimate`)
- Avoid vendor-specific prefixes (use `submittal-review`, not `procore-submittals`)

## 4. Dispatch

When an agent receives a `message/send` (or v1 `SendMessage`) request, the task type **SHALL** be communicated via:

- The request's `metadata.taskType` field, **OR**
- A `taskType` field on the inbound message's metadata

Implementations **SHALL** accept either form. New implementations **SHOULD** emit `metadata.taskType` at the request level.

If the requested `taskType` matches no skill the agent declares, the agent **SHALL** respond with an A2A error of code `-32602` (Invalid params) and message indicating the unsupported task type.

## 5. Output artifact conformance

When an agent's skill declares an `outputSchema`, the artifact returned by that skill's handler **SHALL** validate against the declared schema's canonical JSON Schema document.

If the declared `outputSchema` is a TACO canonical schema name, validation is against `https://taco-protocol.com/schemas/{name}.json`.

Producing an artifact that fails strict validation against its declared schema **SHALL** be considered a non-compliant behavior.

## 6. Proposing new task types

New task types **MAY** be proposed via the TACO RFC process. A proposal **SHALL** include:

1. The kebab-case identifier
2. A one-paragraph description
3. Project phase classification (preconstruction, document management, field/coordination, or new phase justification)
4. Typical input schema
5. Proposed output schema (or note that the output is unstructured)
6. At least one real-world use case
7. Reference to or proposal for the output schema if not yet defined

Until standardized, agents using a proposed task type **SHOULD** use a vendor-prefixed identifier (e.g. `acme-permit-tracking`) to avoid collisions with future standardization.

## 7. Versioning

Task type identifiers are **permanent**. Once `estimate` is in this spec, it stays as `estimate` forever. Renaming would break every existing agent.

Output schema references attached to a task type **MAY** be revised (e.g. when a planned schema becomes defined), but **SHALL NOT** silently change semantic meaning. Schema versioning policy is defined in [ADR-0006](../decisions/schema-versioning).

## 8. Companion material

- [Task Types page](../task-types) — browse all 18 with the interactive filter
- [Cookbook](../cookbook/) — recipes exercising each task type in motion
- [Data Schemas](../schemas/) — the canonical output schemas
