---
title: Standards Alignment
description: How TACO interoperates with construction industry standards (CSI MasterFormat, OmniClass, ISO 19650, IFC, COBie) and protocol standards (A2A, MCP, JSON Schema 2020-12, OAuth 2.0, RFC 8693).
sidebar_position: 4
---

# Standards Alignment

A common RFP question: *"What standards does this align with?"* This page answers that for both the construction-side standards your team already references and the protocol-side standards your software team will care about.

Each entry follows the same shape: **what it is**, **how TACO uses it**, **what TACO does NOT claim about it**. We try to be honest about both ends.

---

## Construction industry standards

### CSI MasterFormat

**What it is.** The construction industry's standard numbering system for specifications. Organizes work into divisions (01–49) — division 23 is HVAC, 26 is electrical, 09 is finishes, and so on. Owned by the Construction Specifications Institute.

**How TACO uses it.** First-class. Every TACO Agent Card declares the CSI divisions it covers (`csiDivisions: ["22", "23"]`). The [registry](/docs/sdk-reference/registry) can filter agents by exact division. TACO data schemas (`bom-v1`, `estimate-v1`, etc.) carry a `csiDivision` field at the project/section level and individual line items can reference a `specSection` (e.g. `"23 21 13"`).

**What TACO does not claim.** TACO does not publish or license MasterFormat. It uses the public division numbers; deep specification numbering is the user's responsibility. Agents that need the full canonical MasterFormat structure should consult CSI directly.

### OmniClass

**What it is.** A multi-axis classification system for the built environment — products, processes, properties, organizational roles, locations, and more. Broader than MasterFormat.

**How TACO uses it.** Indirectly. TACO does not bake in OmniClass tables today; the primary trade-scoping axis is MasterFormat. Future schema iterations may add optional OmniClass identifiers at the line-item level for object-level classification.

**What TACO does not claim.** No OmniClass conformance today. If your project requires OmniClass identifiers on artifacts, your agent is free to add them as additional fields beyond the TACO-defined schema.

### ISO 19650 (BIM information management)

**What it is.** International standard for organizing information about buildings and civil works using BIM throughout the asset lifecycle.

**How TACO uses it.** Compatible by design. ISO 19650 is primarily about *information management workflows* (CDEs, naming conventions, status approvals); TACO is the *protocol* agents use to communicate within those workflows. The two layers do not conflict.

**What TACO does not claim.** TACO is not an ISO 19650 implementation. It does not encode the standard's information container model. Projects subject to ISO 19650 can use TACO agents that produce ISO 19650-conformant outputs when required.

### IFC (Industry Foundation Classes)

**What it is.** The buildingSMART open BIM data model — the file format that lets design tools exchange 3D building information without vendor lock-in.

**How TACO uses it.** TACO is agent-protocol, not file-format. A clash-detection agent or a takeoff agent that reads IFC files is a perfectly valid TACO agent — the IFC stays the input, the typed TACO artifact (`bom-v1`, `clash-report-v1`) is the output.

**What TACO does not claim.** TACO does not parse or emit IFC. There is no TACO data schema that mirrors IFC entities.

### COBie

**What it is.** The Construction-Operations Building Information Exchange — a spreadsheet-based standard for handing project data from construction to facilities operations.

**How TACO uses it.** Compatible at handoff. TACO governs the *during-construction* multi-agent traffic; COBie governs the *project-to-operations* handoff. An end-of-project agent can absolutely consume TACO artifacts (BOMs, change orders, schedules) and emit a COBie spreadsheet.

**What TACO does not claim.** TACO does not auto-generate COBie. The reference SDK ships no `cobie-v1` schema today.

### AIA / ConsensusDocs / contract documents

**What it is.** The American Institute of Architects' contract forms — and ConsensusDocs, the alternative family — define the legal relationships between owners, GCs, designers, and subs.

**How TACO uses it.** Not directly. TACO's RFI, change order, and submittal schemas reflect *workflow* artifacts that exist regardless of contract family. Nothing in TACO contradicts AIA or ConsensusDocs.

**What TACO does not claim.** TACO is not a contract-execution platform. The typed artifacts agents exchange have no legal force on their own — that's the human-in-the-loop's job.

---

## Protocol and open-source standards

### A2A Protocol (Linux Foundation)

**What it is.** The agent-to-agent communication standard maintained under the Linux Foundation. Defines Agent Cards, JSON-RPC messaging, the task lifecycle, streaming, and five authentication schemes.

**How TACO uses it.** TACO is built *on* A2A — it is not a fork or a modification of A2A. Every TACO agent is a valid A2A agent. TACO's contribution is the construction-specific vocabulary that rides on top, via the `x-construction` extension and the named task types + typed schemas.

**Where it lives.** [a2a-protocol.org](https://a2a-protocol.org)

### Model Context Protocol (MCP)

**What it is.** Anthropic's open protocol for connecting AI models to external tools and data sources.

**How TACO uses it.** Orthogonally. A2A is between agents; MCP is between an agent and its tools/data. TACO doesn't depend on MCP, and TACO doesn't dictate that you use MCP. But MCP is the natural choice for an LLM-driven TACO agent that needs to reach Procore, AutoCAD, or a database. See [A2A, MCP, and TACO](/docs/protocol-stack).

**Where it lives.** [modelcontextprotocol.io](https://modelcontextprotocol.io)

### JSON Schema 2020-12

**What it is.** The most recent stable draft of the JSON Schema spec — the format used to describe the structure of JSON documents.

**How TACO uses it.** Every TACO data schema (`bom-v1`, `rfi-v1`, `estimate-v1`, `quote-v1`, `schedule-v1`, `change-order-v1`) is published as a JSON Schema 2020-12 document. The canonical files are served at `/schemas/{name}.json` and embedded in the [interactive Schema Explorer](/docs/schemas/) on each schema page.

### OAuth 2.0 + RFC 8693 Token Exchange

**What it is.** OAuth 2.0 is the industry-standard delegated-auth framework. RFC 8693 adds a token-exchange grant that lets one token be narrowed into a smaller-scope token for a downstream call.

**How TACO uses it.** OAuth 2.0 is the recommended auth scheme for multi-org TACO deployments. The [security model](/docs/security) defines a construction-shaped scope taxonomy (`taco:trade:mechanical`, `taco:project:PRJ-0042:write`) and prescribes RFC 8693 Token Exchange for cross-agent delegation — every hop narrows the token, no agent ever forwards a wider token downstream.

### Mutual TLS (mTLS) · PKCE · OAuth Device Authorization

**What it is.** Standard auth flows beyond plain OAuth 2.0. mTLS for high-assurance deployments. [PKCE (RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636) for public clients. [Device Authorization Grant (RFC 8628)](https://datatracker.ietf.org/doc/html/rfc8628) for input-constrained devices.

**How TACO uses it.** First-class advertisement. `SecurityExt` on the construction agent card carries `mtlsSupported`, `pkceRequired`, and `deviceCodeSupported` booleans so registries and orchestrators can filter on auth modality without parsing the full `securitySchemes` block.

### Server-Sent Events (SSE)

**What it is.** A one-way HTTP streaming format. The W3C standard for server-pushed updates over a single long-lived connection.

**How TACO uses it.** SSE is the transport for `message/stream`. A TACO agent that handles long-running work (a 30-minute takeoff, an iterative bid-leveling pass) streams `TaskStatusUpdate` events to its caller as it makes progress.

---

## What's not yet aligned

We are honest about the gaps:

- **gbXML / Green Building XML** — energy-model interchange. No TACO schema yet.
- **buildingSMART Data Dictionary (bSDD)** — terminology registry. Future alignment is a candidate; not implemented.
- **TARGET / VRIP / EVMS standards** — earned-value reporting. Possible future schema territory.
- **Spec-Right / SpecsIntact / SpecLink integrations** — specification authoring formats. Out of scope today.

If your team needs one of these for an RFP response, [open an issue](https://github.com/pelles-ai/taco/issues) — it helps us prioritize.

---

## Citation block

You may need to cite TACO and the standards it aligns with in technical proposals. A copy-paste block:

> **TACO** (The A2A Construction Open-standard) — open-source construction ontology layer built on the [A2A protocol](https://a2a-protocol.org) (Linux Foundation). TACO aligns with [CSI MasterFormat](https://www.csiresources.org/standards/masterformat) for trade and division scoping, and publishes its data schemas as [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/schema). Security follows [OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749) with [RFC 8693 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693) for cross-agent delegation. Apache 2.0. [taco-protocol.com](https://taco-protocol.com)
