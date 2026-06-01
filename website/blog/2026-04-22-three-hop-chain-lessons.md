---
slug: three-hop-chain-lessons
title: Five lessons from running a 3-hop agent chain in production
authors:
  - name: Pelles + TACO contributors
    url: https://github.com/pelles-ai
tags: [cookbook, multi-agent, lessons]
---

The simplest non-trivial TACO workflow is a three-hop chain: a GC orchestrator generates a takeoff, hands it to a mechanical estimator, then to a supplier for live pricing. We wrote it up [as a recipe](/docs/cookbook/gc-estimator-supplier-chain). The recipe makes it look clean.

The first production deployment of this exact chain did not look clean. Here are five things we — and the team running it — learned the hard way.

<!-- truncate -->

## 1. The hop you forget about is the one that times out

A three-hop chain is `orchestrator → estimator → supplier`. In production the time budget per hop is whatever the slowest hop takes plus network. We sized the orchestrator's HTTP timeouts for what *we* thought the supplier agent's response time would be: a few seconds.

It wasn't. The supplier agent was wrapping a legacy ERP via REST, and that ERP's pricing endpoint took up to ninety seconds during day-end batch windows. Our orchestrator timed out, retried, got a duplicate quote, accidentally double-counted a line item. The supplier agent itself was fine.

**Lesson:** every downstream agent has its own latency envelope. Set timeouts per-call based on the downstream agent's documented SLO, not on what you'd be happy with. When in doubt, use `stream_message` and watch progress events, instead of a single blocking `send_message` with a generous timeout.

## 2. Schema mismatches are slow leaks, not loud crashes

The supplier was returning `quote-v1` payloads that *almost* validated. They had every required field, in the right shapes. What they didn't have was a `unitPrice` per line item — they had `pricePerUnit`. JSON Schema's `additionalProperties: true` made the validator green-light it. The orchestrator's downstream code that summed `item.unitPrice * item.quantity` produced... zero, for every quote, silently.

We caught it because a project manager noticed every quote was "$0.00 — too good to be true."

**Lesson:** strict schema validation at every boundary is non-negotiable in multi-agent chains. The convenience of "ignore extra fields" is exactly the kind of slow leak that escapes test environments. Set `additionalProperties: false` on your schemas (it's the default in well-designed schemas; if you removed it, put it back).

This is part of why we publish the canonical JSON Schemas at `/schemas/{name}.json` — the conformance runner and any production validator should be hitting the same authoritative document.

## 3. Token Exchange has to be real, not theoretical

Our [security docs](/docs/security) say "every hop should narrow its token via RFC 8693." The first deployment of the chain did not. The orchestrator received a token with `taco:trade:mechanical taco:project:PRJ-0042:write` and forwarded it verbatim to the estimator and the supplier.

Nothing broke. Until the supplier agent's host got compromised during a routine pen test. The forensic write-up included "the compromised agent held a project-write token covering scope beyond its skill" — which would have been a minor finding if the token had been narrowed and an emergency if it hadn't.

**Lesson:** Token Exchange isn't optional theater. If you're shipping a multi-hop chain to anyone whose data matters, implement RFC 8693 narrowing per-hop from day one. Add a CI check that fails if any hop's outgoing request carries a wider scope than its skill requires.

## 4. Streaming is wasted unless somebody is watching

We added `stream_message` support to all three agents because A2A makes it easy. The orchestrator subscribed to the supplier's status updates. The supplier dutifully emitted `TaskStatusUpdate` events as it worked.

Nobody on the orchestrator side ever looked at them. The events went into a `for event in stream:` loop that called `pass`. We had built progress instrumentation that produced no user-visible output and consumed measurable orchestrator CPU because every event required JSON parsing.

**Lesson:** decide *who watches the stream* before you build streaming. If it's a human on a dashboard, stream events should flow to the [Monitor UI](/docs/sdk-reference/server) or to a logging pipeline that surfaces them. If nobody's watching, use `send_message` and skip the streaming overhead. The Monitor UI was built for this; use it.

## 5. The registry is your dependency graph — treat it like one

In dev, the orchestrator registered the estimator and supplier via hardcoded URLs in a config file. This worked great until one of those URLs changed (the supplier moved hosts during a routine migration), nobody updated the orchestrator's config, the registry-based skill lookup happened to return a stale entry, and the orchestrator started sending traffic into the void for ninety minutes before anyone noticed.

The lesson here is two-part:

- **The registry is the dependency graph for your deployment.** Treat it like one: source-of-truth for which agents talk to which agents, version-controlled, deployed alongside your orchestrators.
- **Stale entries silently fail.** Either re-register on a schedule (the URL is wrong → catch it via 404 on the agent card fetch) or, when the hosted registry ships, subscribe to update notifications.

For self-hosted deployments today, a five-minute background task that re-`register()`s every known agent URL and logs the agent card hash catches this whole class of bug.

## What we'd have changed in the recipe

The [GC → Estimator → Supplier recipe](/docs/cookbook/gc-estimator-supplier-chain) shows the chain in its happy-path form. After these lessons, the production-grade version would add:

1. Explicit per-call timeouts sized to each downstream's SLO
2. A schema-strict validator at every boundary
3. Token Exchange between hops, not token forwarding
4. Streaming only where someone consumes it
5. A registry re-register loop that surfaces stale URLs as visible errors

These aren't in the recipe because the recipe is what the API looks like. The production wrapping is what every team has to do once and then forgets. We're working on a `production` mode for the SDK that bundles these defaults; if you have opinions, [the issue is open](https://github.com/pelles-ai/taco/issues).

## See also

- [GC → Estimator → Supplier chain recipe](/docs/cookbook/gc-estimator-supplier-chain)
- [Best Practices](/docs/best-practices)
- [Security model](/docs/security)
- [Schedule-Aware Procurement](/docs/cookbook/schedule-aware-procurement) — the cross-schema variant
