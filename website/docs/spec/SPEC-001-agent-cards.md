---
title: "SPEC-001 — Agent Cards & Discovery"
description: Normative requirements for TACO Agent Cards, the well-known discovery path, and the x-construction extension.
sidebar_position: 1
---

# SPEC-001 — Agent Cards & Discovery

**Status:** Provisional
**Version:** 0.3
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

An agent **MAY** also serve the legacy path `GET /.well-known/agent.json` for backward compatibility with older clients. The reference SDK's `A2AServer` serves the same card at both paths, and its client, registry, and CLI fetch `/.well-known/agent-card.json` first and fall back to the legacy path on a 404.

The response **SHALL**:

- Return HTTP status `200 OK` when the agent is operational
- Set `Content-Type: application/json` (or a compatible subtype)
- Return a valid JSON document conforming to the [A2A Agent Card schema](https://a2a-protocol.org) and to this specification

The well-known path **SHALL** be reachable without authentication. Agent identity discovery is intentionally public.

### 2.2 CORS

The well-known path **SHOULD** permit cross-origin requests via an appropriate `Access-Control-Allow-Origin` header when the card is meant to be read from browser contexts. The reference SDK adds no CORS headers unless `cors_origins` is passed to `A2AServer` / `TacoAgent`. The browser-based [conformance check](/conformance) ([SPEC-005 §5](./SPEC-005-conformance)) depends on this to check a card from its URL.

## 3. Required fields

A TACO-compliant Agent Card **SHALL** contain the following top-level fields:

| Field | Type | Notes |
|------|------|-------|
| `name` | string | Human-readable agent name |
| `description` | string | One-paragraph description of the agent's purpose (the reference SDK rejects an empty value) |
| `version` | string | Agent implementation version (e.g. `"1.4.2"`) |
| `url` | string | Base URL where the agent serves its A2A endpoints |
| `skills` | array | At least one skill **SHALL** be declared |

A TACO-compliant Agent Card **SHOULD** contain:

| Field | Type | Notes |
|------|------|-------|
| `capabilities` | object | A2A capabilities object including extension declarations (see §4.2) |

## 4. The `x-construction` extension

A TACO-compliant Agent Card **SHALL** carry the inline `x-construction` field (§4.1) and **SHOULD** also declare the extension URI (§4.2).

### 4.1 Inline `x-construction` field

The Agent Card **SHALL** include a top-level `x-construction` object containing construction-specific metadata. This is the field the reference SDK's registry filters on:

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

The Agent Card **SHOULD** also declare the construction extension in `capabilities.extensions[]`, so A2A v1 clients can detect support without parsing the inline field. The reference SDK's `ConstructionAgentCard.to_a2a()` adds this declaration automatically; `taco.apply_construction_extension_declaration(card)` adds it to a card built another way:

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

An Agent Card that declares this URI **SHALL** also carry the inline `x-construction` field.

## 5. The `x-construction` field schema

When the inline `x-construction` field is present, it **SHALL** conform to:

| Field | Type | Required | Description |
|------|------|--------|---------------------|
| `trade` | string | SHALL | One of the recognized TACO trades (§5.1) |
| `csiDivisions` | string[] | SHALL | Two-digit MasterFormat division numbers (§5.2); **MAY** be empty |
| `projectTypes` | string[] | MAY | One or more of `commercial`, `residential`, `healthcare`, `education`, `industrial`, `infrastructure`, `mixed-use` |
| `certifications` | string[] | MAY | Self-declared certifications: `SOC2`, `ISO27001`, `FedRAMP` |
| `dataFormats` | object | MAY | `input` and `output` arrays of file formats the agent accepts and produces |
| `integrations` | string[] | MAY | One or more of `procore`, `acc`, `bluebeam`, `plangrid`, `p6`, `ms-project`, `sage`, `viewpoint` |
| `security` | object | MAY | Security advertisement (see [SPEC-004](./SPEC-004-security)) |

The reference SDK's card model rejects `trade`, `projectTypes`, `certifications`, and `integrations` values outside the lists above.

### 5.1 Recognized trades

The `trade` field **SHALL** be one of:

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
| `name` | string | SHALL | Human-readable label |
| `description` | string | SHALL | One-sentence description of what the skill does |
| `x-construction` | object | SHALL | Construction routing metadata for the skill (§7) |

The reference SDK's skill model requires `id`, `name`, and `description`; its `ConstructionSkill` factory fills `name` and `description` with defaults when they are not given, and always sets `x-construction`.

## 7. Skill-level construction extension

Each skill's `x-construction` object carries the skill's task type and schemas:

| Field | Type | Required | Description |
|------|------|--------|---------------------|
| `taskType` | string | SHALL | A TACO task type (see [SPEC-002](./SPEC-002-task-types)) |
| `inputSchema` | string | MAY | Expected input schema identifier |
| `outputSchema` | string | SHALL | Output schema identifier |

```json
{
  "id": "generate-bom",
  "name": "Generate Bill of Materials",
  "description": "Generates a detailed BOM from construction plan sheets",
  "x-construction": {
    "taskType": "takeoff",
    "inputSchema": "plan-sheets",
    "outputSchema": "bom-v1"
  }
}
```

When `inputSchema` or `outputSchema` matches the name of a canonical TACO schema (e.g. `"bom-v1"`), it **SHALL** refer to that schema, defined in [`spec/schemas/{name}.json`](https://github.com/pelles-ai/taco/tree/main/spec/schemas) in the TACO repository (see [SPEC-003](./SPEC-003-data-schemas)). Other bare identifiers, such as `"plan-sheets"` above, are descriptive and not standardized. When the value is a fully-qualified URL, the URL **SHOULD** resolve to a JSON Schema document. The reference SDK does not check these identifiers.

The skill-level `x-construction` object contains only the three fields above. Agent-level fields such as `projectTypes` are not supported at skill level, and registries do not merge skill-level values over the agent-level extension.

## 8. Versioning of this specification

This specification follows the versioning policy of the TACO specification set ([Spec index](./)). This spec is Provisional at 0.3, tracking protocol 0.3, and may still change in a minor version. When it reaches Stable as 1.0, that major version becomes permanent: additive changes land as 1.x, and breaking changes, if ever, mint 2.0 at a new URL.

## 9. Companion material

- [Agent Card Extensions](../agent-card-extensions) — the prose introduction
- [ADR-0009 — Extension URI naming](../decisions/extension-uri-naming)
- [SPEC-005 Conformance](./SPEC-005-conformance) — the checks that verify the requirements in this spec
