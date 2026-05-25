---
slug: why-build-on-a2a
title: Why we built TACO on A2A instead of designing our own protocol
authors:
  - name: Pelles + TACO contributors
    url: https://github.com/pelles-ai
tags: [protocol, a2a, design]
---

The most-asked question in the first month after we made TACO public was some variant of: **"Why are you building on A2A? Construction is its own world; surely you need a construction-native protocol."**

It's a fair question. Construction agents have to coordinate trades, reason about CSI divisions, handle drawings, respect bid cycles. None of that is in A2A. So why didn't we design a construction-shaped transport from scratch?

<!-- truncate -->

## What "building on A2A" actually means

A2A (the [Linux Foundation Agent-to-Agent Protocol](https://a2a-protocol.org)) defines:

- **Agent Cards** — how an agent advertises what it is and what it does, served at `/.well-known/agent-card.json`
- **JSON-RPC messaging** — `message/send`, `message/stream`, `tasks/get`, `tasks/cancel`
- **Task lifecycle** — `submitted` → `working` → `completed` / `failed` / `canceled`
- **Streaming via SSE** — incremental updates from long-running tasks
- **Five authentication schemes** — `apiKey`, `http`, `oauth2`, `openIdConnect`, `mutualTLS`

TACO takes all of this and adds:

- **`x-construction` extension** on the Agent Card (trade, CSI divisions, project types, integrations)
- **Task type vocabulary** (18 named construction workflows: `takeoff`, `estimate`, `rfi-generation`, ...)
- **Typed JSON schemas** for construction artifacts (`bom-v1`, `rfi-v1`, `estimate-v1`, `quote-v1`, `schedule-v1`, `change-order-v1`)
- **Construction-shaped OAuth scopes** (`taco:trade:mechanical`, `taco:project:PRJ-0042:write`)
- **A registry abstraction** for discovery by trade, division, or task type

Every TACO agent is a valid A2A agent. Drop the construction extension and you're left with a plain A2A agent that A2A's broader tooling — orchestrators, observers, debuggers — already knows how to talk to.

## Three things we'd have had to reinvent

### Transport

A2A's wire format is JSON-RPC over HTTP, with SSE for streaming. Mature, debuggable, browser-friendly. Building our own transport would have meant:

- Authoring (and defending) the choice of binary vs text format
- Writing a streaming spec
- Writing language SDKs from scratch
- Convincing every observability tool, every load balancer, every WAF that our protocol is benign

A2A did all of that work in the open with Linux Foundation governance. We don't have a strong opinion that we could do it meaningfully better. So we shipped on top of it.

### Task lifecycle

Long-running construction tasks (a 30-minute takeoff from a 200-sheet drawing set; a multi-trade clash run across a large IFC model) need real lifecycle semantics: a way to track progress, to cancel, to retrieve the result hours later. A2A's `submitted` → `working` → `completed` model is what we'd have invented anyway, plus or minus details. We took it.

### Discovery, capability negotiation, version handshaking

A2A v1 added formal `capabilities.extensions[]` so agents can declare which extensions they implement. TACO uses that mechanism to declare its `x-construction` extension URI — old A2A clients ignore it, new clients can negotiate it. We didn't have to design this; it was there.

## Why we resisted the urge to fork

Several thoughtful people argued, in good faith, that we should "just take what's useful from A2A and ship a construction-shaped fork." It was the most tempting alternative. We didn't, for three reasons.

### Forks fragment the ecosystem at exactly the wrong time

Agent-to-agent communication is brand new as a standard. A2A v1 shipped in early 2026. The window where "is there a generic agent protocol?" gets a confident answer is open for maybe twelve months. If TACO had forked, we'd have spent the next year explaining why our agents don't talk to non-construction agents — and watching every other industry follow the same temptation.

The price of staying in the A2A family is occasionally being annoyed that A2A's defaults aren't construction-shaped. The price of forking would have been excluding ourselves from the broader agent conversation forever.

### Governance is harder than we thought

Maintaining a protocol — handling RFCs, breaking-change debates, security disclosure processes, browser-compat issues — is a full-time job. The Linux Foundation runs it for A2A; we don't have to. We get to focus on construction semantics.

### "Construction-specific transport" wouldn't have been very different anyway

Sit down to design what a construction-native protocol would actually look like — task lifecycle, JSON-typed messages, server-sent events for streaming, OAuth for auth, well-known URLs for discovery — and you arrive at A2A within an hour. The construction-specific bits live cleanly on top, in extensions and vocabulary, not in the transport.

## What this commits us to

A2A's direction is a load-bearing assumption for TACO. When A2A breaks (the v0.3 → v1.0 wire cutover, currently mid-flight; see [`/sdk/V1_MIGRATION.md`](https://github.com/pelles-ai/taco/blob/main/sdk/V1_MIGRATION.md)), we have to track it. Our SDK's compat layer cushions the wire-level changes, but the underlying commitment is real: if A2A pivots in a direction we can't follow, we have a problem.

It's a calculated risk. So far A2A's governance and direction have been good. We've contributed back where construction-specific concerns are relevant to the broader spec. We have no reason to expect that to change.

## When you'd be right to build your own protocol

We're not arguing nobody should. If you're in a domain where:

- The transport itself has domain-specific requirements (e.g. real-time control loops at deterministic latency)
- There's no existing standard that has reached critical mass
- You can credibly run the governance overhead long-term

— then designing from scratch is the right move.

Construction wasn't that. Agent-to-agent traffic in construction looks structurally identical to agent-to-agent traffic in finance, healthcare, retail, or anywhere else: long-running tasks, typed handoffs between organizations, multi-hop auth, streaming progress updates. The construction-specific bits are *what's exchanged*, not *how it gets exchanged*.

## See also

- [ADR-0001 — Build on A2A](/docs/decisions/build-on-a2a) — the formal decision record
- [Protocol stack — A2A, MCP, and TACO](/docs/protocol-stack)
- [A2A Protocol](https://a2a-protocol.org)
