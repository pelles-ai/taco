---
title: "SPEC-001 — Agent Cards & Discovery"
description: Normative requirements for TACO Agent Cards, the well-known discovery path, and the x-construction extension.
sidebar_position: 1
---

# SPEC-001 — Agent Cards & Discovery

**Status:** Stable
**Version:** 1.0
**Date:** 2026-05-25

## 1. Introduction

This specification defines the requirements for a TACO-compliant Agent Card and the discovery mechanism through which other agents and registries locate it. TACO Agent Cards extend the [A2A](https://a2a-protocol.org) Agent Card with a construction-specific extension.

The key words **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 2. Discovery

### 2.1 Well-known path

A TACO-compliant agent **SHALL** serve a valid Agent Card document at:

```
GET /.well-known/agent-card.json
```

An agent **MAY** also serve the legacy path `GET /.well-known/agent.json` for backward compatibility with pre-A2A-v1 clients.

The response **SHALL**:

- Return HTTP status `200 OK` when the agent is operational
- Set `Content-Type: application/json` (or a compatible subtype)
- Return a valid JSON document conforming to the [A2A Agent Card schema](https://a2a-protocol.org) and to this specification

The well-known path **SHALL** be reachable without authentication. Agent identity discovery is intentionally public.

### 2.2 CORS

The well-known path **SHOULD** permit cross-origin requests via an appropriate `Access-Control-Allow-Origin` header. The conformance runner ([SPEC-005](./SPEC-005-conformance)) operates by making cross-origin fetches from a browser context.

## 3. Required fields

A TACO-compliant Agent Card **SHALL** contain the following top-level fields:

| Field | Type | Notes |
|------|------|-------|
| `name` | string | Human-readable agent name |
| `version` | string | Agent implementation version (e.g. `"1.4.2"`) |
| `url` | string | Base URL where the agent serves its A2A endpoints |
| `skills` | array | At least one skill **SHALL** be declared |

A TACO-compliant Agent Card **SHOULD** contain:

| Field | Type | Notes |
|------|------|-------|
| `description` | string | One-paragraph description of the agent's purpose |
| `capabilities` | object | A2A capabilities object including extension declarations (see §6) |

## 4. The `x-construction` extension

A TACO-compliant Agent Card **SHALL** declare the construction extension via **at least one** of the following two mechanisms:

### 4.1 Inline `x-construction` field

The Agent Card **MAY** include a top-level `x-construction` object containing construction-specific metadata:

```json
{
  "x-construction": {
    "trade": "mechanical",
    "csiDivisions": ["22", "23"],
    "projectTypes": ["commercial", "healthcare"],
    "integrations": ["procore", "acc"]
  }
}
```

### 4.2 Extension URI declaration

The Agent Card **MAY** declare the construction extension in `capabilities.extensions[]`:

```json
{
  "capabilities": {
    "extensions": [
      {"uri": "https://taco.construction/extensions/x-construction/v1"}
    ]
  }
}
```

The canonical URI is `https://taco.construction/extensions/x-construction/v1` (see [ADR-0009](../decisions/extension-uri-naming)).

When both mechanisms are present, they **SHALL** be consistent.

## 5. The `x-construction` field schema

When the inline `x-construction` field is present, it **SHALL** conform to:

| Field | Type | Required | Description |
|------|------|--------|---------------------|
| `trade` | string | SHOULD | One of the recognized TACO trades (§5.1) |
| `csiDivisions` | string[] | MAY | Two-digit MasterFormat division numbers (§5.2) |
| `projectTypes` | string[] | MAY | Project type identifiers the agent specializes in |
| `integrations` | string[] | MAY | Platform identifiers the agent integrates with |
| `security` | object | MAY | Security advertisement (see [SPEC-004](./SPEC-004-security)) |

### 5.1 Recognized trades

The `trade` field **SHOULD** be one of:

`mechanical`, `electrical`, `plumbing`, `structural`, `civil`, `architectural`, `fire-protection`, `general`, `multi-trade`

Agents that span multiple trades **SHOULD** declare `trade: "multi-trade"` rather than picking one arbitrarily.

### 5.2 CSI divisions

Each entry in `csiDivisions[]` **SHALL** be a string matching the regex `^[0-9]{2}$` (a two-digit MasterFormat division number, e.g. `"22"`, `"23"`, `"26"`).

Entries with leading/trailing whitespace, non-string values, or formats other than two-digit strings **SHALL** be considered invalid.

## 6. Skills

Each entry in `skills[]` **SHALL** contain:

| Field | Type | Required | Description |
|------|------|--------|---------------------|
| `id` | string | SHALL | Unique skill identifier within the agent |
| `taskType` | string | SHALL | A recognized TACO task type (see [SPEC-002](./SPEC-002-task-types)) |
| `inputSchema` | string | MAY | Canonical schema name or full URL |
| `outputSchema` | string | MAY | Canonical schema name or full URL |
| `name` | string | SHOULD | Human-readable label |
| `description` | string | SHOULD | One-sentence description of what the skill does |

When `inputSchema` or `outputSchema` is a bare schema name (e.g. `"bom-v1"`), it **SHALL** refer to a canonical TACO schema published at `https://taco-protocol.com/schemas/{name}.json`. When it is a fully-qualified URL, the URL **SHOULD** resolve to a JSON Schema document.

## 7. Skill-level construction extension

A skill **MAY** include its own `x-construction` sub-object overriding agent-level defaults for that skill specifically:

```json
{
  "id": "estimate-residential",
  "taskType": "estimate",
  "x-construction": {
    "projectTypes": ["residential"]
  }
}
```

When present, the skill-level extension **SHALL** be merged over the agent-level extension for purposes of registry filtering.

## 8. Versioning of this specification

This specification follows the versioning policy of the TACO specification set ([Spec index](./)). v1 of this spec is permanent. Additive changes will land as v1.x; breaking changes (if ever) will mint v2 at a new URL.

## 9. Companion material

- [Agent Card Extensions](../agent-card-extensions) — the prose introduction
- [ADR-0009 — Extension URI naming](../decisions/extension-uri-naming)
- [Conformance runner](/conformance) — verifies the requirements in this spec
