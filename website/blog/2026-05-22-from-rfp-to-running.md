---
slug: from-rfp-to-running
title: From RFP to running — what TACO-required procurement looks like
authors:
  - name: Pelles + TACO contributors
    url: https://github.com/pelles-ai
tags: [procurement, rfp, adoption]
---

We just published an [RFP template](/docs/rfp-template) for buyers who want to require TACO compatibility from vendors. The template is the artifact. This post is the operational context — what actually happens when an owner or GC puts "must be TACO-compatible" in an RFP and a vendor reads it.

<!-- truncate -->

## The current state of construction software RFPs

Most construction-tech RFPs in 2026 include some version of "must have an open API." This phrase has approximately zero discriminating power. Every vendor's marketing site says they have one. Every actual integration takes weeks of custom mapping code. The RFP question and the operational reality don't connect.

The RFP template we published does something different. It requires:

- A specific protocol (TACO, built on A2A)
- A specific verification mechanism (the [conformance runner](/conformance))
- A specific set of capabilities described in machine-readable terms (Agent Card fields, task type enums, schema names)

That difference matters. "Open API" is unfalsifiable; "passes the conformance runner with these specific checks" is testable in 60 seconds by a procurement intern.

## What a vendor reads when they see "TACO required"

If you're a platform vendor responding to an RFP that requires TACO compatibility, here's what the requirement actually translates to in your engineering team's terms:

1. Add a `/.well-known/agent-card.json` endpoint to whatever already runs your API. The card is JSON; it advertises what your platform can do, in TACO's vocabulary.
2. For each capability you want to expose, write a small translator (a "sidecar," see [ADR-0004](/docs/decisions/sidecar-pattern)) that takes a TACO request and turns it into your existing API call, and shapes the response into a TACO artifact.
3. Run the conformance runner; fix what it flags; attach the report to your RFP response.

For a vendor with a mature internal API, the work is typically 1-3 weeks per capability. Not months. Not a platform rebuild. The reason it can be so fast is exactly what TACO was designed for: the protocol layer is additive, not replacement.

The [For Platform Vendors](/for/platform-vendor) page walks through this in more detail.

## What a buyer reads in vendor responses

If you're a buyer evaluating responses, the conformance runner result is the single most informative line item in the vendor's reply.

- **All required checks pass.** The vendor's endpoint is structurally TACO-compliant. They've done the work; they're real. Score this high.
- **All required checks fail.** They haven't actually built this; they're claiming compatibility without producing it. Score this zero on the conformance line, deeply discount their other claims about "interoperability."
- **Some required checks pass, some fail.** Most useful case. The failures tell you exactly where the vendor's integration story breaks down. A vendor that's 8 of 10 with clear remediation hints might be a few weeks from full compliance; a vendor that's 2 of 10 has a lot of work ahead.

This is the part RFP buyers usually don't get with "open API" claims: a specific, testable, granular view of where the vendor stands. Use it.

## The first 90 days of a TACO-compliant deployment

Once a TACO-compliant vendor is selected, what's the real operational timeline? Drawing from early adoptions:

**Days 1-14: registration and discovery.** Your project's orchestrator agent registers the vendor's URL. Your team verifies the agent card via the conformance runner one more time (always). Your downstream agents that need to call this vendor learn to do so.

**Days 15-30: first real workflow.** A typical first workflow is something low-stakes — a takeoff for one floor, a single RFI routing — that exercises the integration without putting binding traffic through it. Watch the Monitor UI; tag any issues; iterate.

**Days 30-90: production traffic and observability.** OpenTelemetry traces flowing. Per-vendor latency and error rates visible in your dashboard. Failed tasks attributable to specific agents within minutes, not days. The integration is now what you wanted "open API" to mean from the start.

**Day 90+: routine.** New project? Add the vendor to the project's registry; everything else works the same. No new integration code per project — that's the whole point.

## What you don't get for free

Worth being honest about:

- **The RFP requirement doesn't substitute for evaluating the vendor's actual product.** A TACO-compliant agent that produces low-quality estimates is still a low-quality estimator. The protocol layer is plumbing, not magic.
- **The conformance runner is structural, not semantic.** It tells you the vendor's agent card is well-formed; it doesn't tell you the vendor's `material-procurement` workflow accurately reflects current market prices.
- **You still need someone on your team who reads the typed artifacts.** The benefit of "estimator returns `estimate-v1` instead of a PDF" only lands if your project record knows what to do with the typed artifact. Most teams need to update at least one internal process.

The protocol layer reduces integration cost. It does not reduce evaluation cost. Pick vendors carefully on the merits of their work; pick vendors via the RFP language on the merits of their integration story.

## The cultural shift

The hardest part of TACO-required procurement isn't technical — it's the conversation with vendors who haven't done it before. Common reactions:

> *"We support REST; isn't that enough?"*
> No. REST is a style; TACO is a specific shape. The conformance runner shows you the gap. The work to close it is bounded.

> *"This will lock us into a specific protocol."*
> Less than the alternative. Without TACO, you're locked into per-vendor APIs forever. With TACO, every additional vendor is one URL away.

> *"Our customers haven't asked for this."*
> They're starting to. Owners and GCs are reading the same posts; some of them are publishing RFPs with TACO requirements right now. The vendors that pick this up early get the first-mover credibility; the vendors that wait spend the next two years defending why they don't.

> *"How much does this cost us?"*
> A few weeks per capability you want to expose. No licensing — TACO is Apache 2.0. The infrastructure is whatever you'd run an HTTP service on.

## What we'd ask buyers to do

If you're an owner or GC reading this:

1. **Include the [RFP template](/docs/rfp-template) requirements** in your next vendor evaluation.
2. **Treat the conformance runner result as a first-pass filter.** Vendors who can't produce a clean report aren't ready; you save weeks by filtering them out early.
3. **Tell the vendors you're talking to that you're asking for this.** Each conversation moves the market.

The construction software market shifts when enough buyers demand a specific thing. TACO is small enough today that one or two large buyers requiring it in their next RFP cycle would meaningfully reshape vendor priorities.

## See also

- [RFP Template](/docs/rfp-template) — the artifact this post is built around
- [Conformance Runner](/conformance) — the verification mechanism
- [For Platform Vendors](/for/platform-vendor) — the framing for vendors responding to TACO RFPs
- [For Owners](/for/owner) — the framing for owner-side decision-makers
- [Compare to alternatives](/docs/compare) — the "what about X?" answer
