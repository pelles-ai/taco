---
slug: construction-software-api-problem
title: What construction software's API problem actually looks like in 2026
authors:
  - name: Pelles + TACO contributors
    url: https://github.com/pelles-ai
tags: [industry, integration, protocol]
---

Every owner, GC, and platform vendor we talk to says some version of the same thing: *"Our construction software stack doesn't talk to itself."* It's true. It has been true for decades. What's interesting in 2026 is **why it's getting worse, fast** — and what specifically is needed now that wasn't needed five years ago.

This isn't a TACO sales post (we're going to talk about TACO at the end, but only briefly). The first part is a clear-eyed look at the state of API interoperability in construction software, what's changed recently, and why "more REST APIs" isn't the answer.

<!-- truncate -->

## The status quo: every platform is an island with a documented airport

A mature construction shop's stack in 2026 looks roughly like this:

- **A project management platform** — Procore, Autodesk Construction Cloud, CMiC, Trimble
- **A drawings tool** — Bluebeam Revu, PlanGrid, ProjectSight
- **A BIM coordination tool** — Navisworks, Revizto, Solibri
- **A scheduling tool** — Primavera P6, Microsoft Project, Smartsheet
- **A bid management tool** — BuildingConnected, SmartBid, Pantera
- **A specialty estimating tool** — Togal, STACK, PlanSwift, ConWize
- **Several trade-specific tools** — McCormick for electrical, Quote Express for mechanical, Sage for accounting
- **A document/email layer** — Bluebeam Studio, Egnyte, MS 365

Every one of these has a documented REST API. Most have an OpenAPI spec. Several have webhook subscriptions. So the API surface area is technically there.

What isn't there is **a shared way to talk about the things construction projects produce**: a takeoff, an RFI, a change order, a schedule activity. Procore's API for a Request for Information returns a different shape than Autodesk's, which is different from Bluebeam's, which is different from the homegrown thing the GC's office wrote in 2019. None of them are wrong. They're just incompatible.

Result: integration work is a permanent line item. Every two-platform pair needs its own connector. Three-platform pairs need three connectors. A modest-sized GC with five core tools is maintaining ten point-to-point integrations.

## What changed: AI agents broke the math

The integration tax was already painful with five tools. Then AI agents arrived.

In 2026, every team is shopping for or building specialty agents. Takeoff agents that read PDF drawings. Submittal-review agents. Schedule-coordination agents. RFI-drafting agents. Some come from established vendors retrofitting AI; some come from startups building agent-first products; some are internal builds.

Each agent has its own API. Each agent is a new integration. The math that was bad with five tools (ten pairs) gets catastrophic with five tools plus ten agents (45+ pairs).

Worse, agents have *different needs* than platforms. Platforms want CRUD operations. Agents want:

- **Discovery** — "find me an agent that does mechanical estimating for division 23"
- **Typed handoffs** — "send this BOM, expect an estimate back"
- **Long-running tasks** — minutes to hours, not seconds
- **Streaming progress** — partial output as work happens
- **Auth that respects multi-org chains** — token narrowed at every hop

Standard REST + OpenAPI handles approximately none of this well.

## Why "more REST APIs" doesn't fix it

The instinct in 2024–25 was: "Every platform should publish an OpenAPI spec; clients can integrate against any of them." Several vendors actually did this and the result was clarifying — the problem is harder than the API documentation question.

Three structural reasons OpenAPI alone doesn't solve it:

### 1. Vocabulary, not syntax

The differences between Procore's RFI and Autodesk's RFI aren't *syntactic* — both are JSON objects with reasonable field names. They're *semantic*: do you model RFI priority as a string enum or a numeric scale? Is the responsible party an org ID or a user ID? Are drawing references file paths or content addresses?

These are vocabulary differences. OpenAPI describes the syntax of each vendor's choices; it doesn't reconcile them into a shared model. Two OpenAPI-described platforms can be fully self-consistent and still need a custom mapping layer to talk.

### 2. Discovery isn't an API thing

If you want to find every agent on your project that handles `material-procurement`, no per-platform OpenAPI helps. You need a *registry* — a thing that lists agents by capability. Construction has never had one; standardizing one is a meta-level above any single platform's API.

### 3. The relationships are multi-hop and multi-org

A typical construction workflow crosses three or more organizations: GC, sub, supplier; or owner, GC, architect; or design lead, sub, AHJ. Each transition is a trust boundary. Each transition needs auth that's been narrowed for that specific hop. REST APIs handle the per-vendor auth; nobody handles the per-hop auth.

## What's actually needed

If you sit down with a senior IT person at a top-100 GC and ask "what would make this better?", you get a list:

1. **A shared vocabulary for the things our project produces** — agreed-on shapes for BOMs, RFIs, estimates, schedules, change orders, so any tool that produces one can be consumed by any tool
2. **A way to discover what agents and platforms exist on a project** — by trade, by capability, by trust level
3. **A trust model that respects organizational boundaries** — multi-hop auth where each agent only holds the authority it needs
4. **A way for existing platforms to participate without rewrites** — vendors won't rebuild their products to fit a new protocol; integration has to be additive
5. **An open governance** — no single vendor controls the standard; the construction industry's tolerance for vendor lock-in keeps decreasing

These are not five different products. These are the components of *a protocol*. And protocols only work when the construction industry agrees on one.

## Where TACO fits

TACO (the project this blog is published by — see [Why TACO](/docs/why-taco)) is one attempt at exactly this. We built it on top of the Linux Foundation's [A2A protocol](https://a2a-protocol.org) for the transport — see [our reasoning](/blog/why-build-on-a2a) — and added construction-specific vocabulary on top: 6 typed schemas, 18 named task types, an agent card extension for trade/division/integration metadata, a construction-shaped OAuth scope taxonomy.

Whether TACO becomes *the* answer or just *an* answer matters less than whether the construction industry recognizes the problem clearly enough to converge on one. The list above — shared vocabulary, discovery, multi-hop auth, additive integration, open governance — that's what to evaluate any candidate against. TACO included.

## What you can do this week

Whether you're at a GC, an owner, a sub, or a platform vendor:

- **Audit your integration matrix.** Count the point-to-point connectors you maintain. Multiply by their annual maintenance cost. Show the number to leadership.
- **Ask your platform vendors what their agent strategy is.** "Do you support discovery? Typed handoffs? Multi-hop auth?" The answers will be revealing.
- **Look at one workflow that crosses three organizations.** Identify where the bottleneck is. It's almost always integration glue, not the actual work.
- **Try a protocol.** TACO is the one we built; there are others worth looking at. The point is to use *something* concrete and learn from running it, rather than evaluate abstractions.

The construction software stack of 2030 will look meaningfully different from 2026's. The question is whether the interoperability layer is built deliberately by the industry or accidentally by whichever vendor captures enough market share to dictate the shape.

## See also

- [Why TACO](/docs/why-taco)
- [Why we built TACO on A2A](/blog/why-build-on-a2a)
- [Compare to alternatives](/docs/compare)
- [For platform vendors](/for/platform-vendor)
