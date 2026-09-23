---
title: "SPEC-002 — Task Types"
description: Normative requirements for declaring, dispatching, and naming TACO task types.
sidebar_position: 2
---

# SPEC-002 — Task Types

**Status:** Provisional
**Version:** 0.3
**Date:** 2026-05-25

## 1. Introduction

This specification defines the requirements for TACO task types — the vocabulary of named construction workflows an agent can advertise and execute.

The key words **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 2. Recognized task types

A TACO-compliant agent's `skills[].x-construction.taskType` field **SHOULD** reference one of the 18 recognized task types defined in this section. Task types not listed here **MAY** be used but **SHOULD** be proposed for standardization (see §6).

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

When a client sends a `message/send` or `message/stream` request, it **SHALL** communicate the task type in the request-level `params.metadata.taskType` field:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "message": { "role": "user", "parts": [ ... ], "messageId": "..." },
    "metadata": { "taskType": "estimate" }
  }
}
```

The reference SDK's `TacoClient` always sets this field. The reference server reads only the request-level field; a `taskType` placed in the inbound message's own `metadata` is not used for dispatch.

The reference server resolves the task type as follows:

1. If `metadata.taskType` is present, that value is used.
2. If it is absent and the agent has exactly one registered handler, that handler is used.
3. Otherwise the task ends in the `failed` state, with a status message naming the available task types.

If the resolved task type has no registered handler, the task ends in the `failed` state with a status message indicating that no handler exists for that task type. The request itself does not return a JSON-RPC error; the failure is reported through the task's status. Agents **SHOULD** follow the same behavior so that clients can handle both cases through the task lifecycle.

Dispatch is by registered handler. The reference server does not check the requested task type against the `skills[]` declared on the Agent Card, so agents **SHOULD** keep their declared skills and registered handlers in step.

## 5. Output artifact conformance

When an agent's skill declares an `outputSchema`, the artifact returned by that skill's handler **SHALL** validate against the declared schema's JSON Schema document.

If the declared `outputSchema` is a TACO canonical schema name, validation is against the canonical file [`spec/schemas/{name}.json`](https://github.com/pelles-ai/taco/tree/main/spec/schemas) in the TACO repository. The reference SDK does not validate handler output automatically; handlers can use the Pydantic models in `taco.schemas` to do so.

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

- [Task Types page](../task-types) — all 18 task types in one place
- [Cookbook](../cookbook/) — recipes exercising each task type in motion
- [Data Schemas](../schemas/) — the canonical output schemas
