---
title: "Case study: City of Riverbend transit modernization — TACO in a $340M public procurement"
description: A municipal owner uses TACO compatibility as an RFP requirement on a multi-vendor transit hub project. The buy-side leverage and operational reality from required-in-RFP through first 90 days of production.
sidebar_position: 3
---

# Case study: City of Riverbend transit modernization

:::note Illustrative
Fictional but realistic. Composed from patterns we've seen in early owner-side adoptions and from public procurement processes we've reviewed. Use it to understand how the [RFP template](/docs/rfp-template) translates into operational reality on the buy side.
:::

## The project

**City of Riverbend Transit Authority** is modernizing the downtown transit hub — a 220,000 sqft mixed-use facility combining bus terminals, light rail interchange, retail, and a small parking structure. Total budget: $340M. Project duration: 30 months. Funded jointly by the federal infrastructure grant program, state matching funds, and a municipal bond.

Public procurement context. Every contract over $1M goes through formal RFP. Vendor selection requires documented evaluation against published criteria. Audit happens.

The Transit Authority's IT director, **Anika**, attended a regional construction-tech conference 6 months before the RFP cycle and heard a panel on agent interoperability. She came back with three pages of notes and one question: *how do we prevent the integration sprawl we've seen on the last two capital projects?*

The previous project — a $180M public works depot — had ended up with 14 point-to-point vendor integrations, none of which talked to each other. Project closeout took 4 months longer than planned because nobody could reconcile the data across vendor portals. The handoff to facilities operations was, in the project's after-action report, "not characterized by data quality."

Anika wasn't going to let that happen on Riverbend.

---

## The decision to require TACO

**Month -6 (relative to RFP issuance).** Anika spent two weeks reading TACO documentation. The conformance runner was the convincing part — "we can actually test whether vendors comply" was the line that moved this from "interesting" to "approved by procurement."

She brought a proposal to the Transit Authority's procurement committee:

> Add to all capital-project IT vendor RFPs (over the $250K threshold) a section requiring TACO protocol compatibility for any vendor providing software-based deliverables — agents, platforms, integrations. Verification via the public TACO conformance runner. Scored as part of the technical evaluation rubric at 15% weight.

The procurement committee asked the obvious question: "Does this prevent us from selecting good vendors?"

Anika's answer: "It prevents us from selecting vendors who can't or won't commit to interoperability. Those are the vendors who cause us downstream problems anyway."

The committee approved it for the next RFP cycle.

---

## The RFP

**Month -4.** The Transit Authority issued the RFP for the construction technology stack — agent orchestration platform, design coordination tools, scheduling, RFI/submittal management, financial integration. 17 vendors registered interest. 12 submitted responses.

The RFP language used the [TACO RFP template](/docs/rfp-template) almost verbatim. The required capabilities section was mandatory; the recommended capabilities and scoring rubric were the differentiators.

The conformance runner result was the gate question. Vendors had to attach a dated report.

---

## Vendor responses

**Month -2.** Responses came in. The pattern was educational.

### The "we have an API" responses (3 vendors)

Three established vendors responded with extensive technical documentation arguing their existing REST APIs "fundamentally provide the same capabilities as TACO." They did not run the conformance runner. They argued the requirement was "vendor-specific" and that "industry-standard REST" should be acceptable.

**Outcome:** disqualified on the required-capabilities gate. These vendors had relationships with the Authority going back years; the procurement officer had to explain to two of their account executives why their responses didn't move forward. The conversation was unpleasant. Anika held her ground because the requirement was published, mandatory, and unambiguous.

### The "we built it for this RFP" responses (4 vendors)

Four vendors had stood up a TACO sidecar in the 4-month RFP window specifically to respond. Their conformance reports showed mixed results — typically 7 of 8 required checks passing, with one usually being security-related (Token Exchange not yet implemented). Their commercial pricing reflected that the integration was new.

**Outcome:** advanced to further evaluation. The Authority's procurement team was clear that these vendors were taking a real risk — they'd built compliance for a single RFP — and weighted that in the qualitative scoring. Three of the four made the shortlist.

### The "we've been TACO-compatible for months" responses (5 vendors)

Five vendors arrived with mature TACO endpoints. Multiple agents per vendor in some cases. Conformance reports showing all required + all recommended checks. Two of them had been mentioned in TACO community channels for months.

**Outcome:** strong shortlist. These vendors had self-selected by adopting the protocol early; the RFP language identified them cleanly.

### One unusual response

One small vendor — a 6-person startup — responded only with their conformance report and a one-page summary. No marketing materials, no boilerplate. Their report showed all required + 5 of 6 recommended checks passing. Their pricing was 60% of the incumbent's.

**Outcome:** scored unusually well on the rubric. The technical evaluators flagged that the small vendor might lack the operational scale for the project. The procurement officer's recommendation: include them in the final 4 vendors invited to present.

---

## Selection

**Month 0 (RFP closes).** The Transit Authority selected three primary vendors and one specialty vendor:

- **Agent orchestration platform**: one of the "mature TACO" vendors, $1.4M / 30 months
- **Design coordination platform**: one of the "built it for the RFP" vendors, $2.1M / 30 months — chosen partly because their willingness to build compliance for this RFP signaled future cooperation
- **Scheduling + financial integration**: incumbent vendor (the Authority has used them on past projects), who happened to be in the "we've been TACO-compatible for months" group, $3.8M / 30 months
- **Specialty / niche agent for transit-specific workflows**: the 6-person startup, $440K / 30 months — selected with explicit acknowledgment of their scale risk; included as a way to validate the small-vendor-in-TACO-ecosystem thesis

Total contracted value across these four: $7.74M, roughly 2.3% of total project budget. The previous public works depot had spent 3.1% on equivalent scope with materially worse interoperability outcomes.

---

## The first 90 days of running

**Month 1.** Vendors registered their agents in the Authority's project registry. The orchestration vendor stood up the central orchestrator agent in the Authority's cloud account. The other three vendors' agents lived in their own infrastructure but were discoverable via the registry.

Anika ran the conformance runner against every registered URL in week 1. Every required check passed. (One recommended check — push notification subscribers — failed on the scheduling vendor; their fix landed in week 3.)

**Month 2.** First real workflow: an RFI generated by the design coordination platform's audit agent, routed via the orchestrator to the design team's responder agent. End-to-end turnaround: 2 hours 18 minutes, from drawing audit to typed response artifact landing in the Authority's project record.

The Authority's deputy project director, reviewing the artifact in their dashboard, noted: "This is the first RFI on a capital project where the response is actually a structured record. Not a PDF, not an email thread."

**Month 3.** First non-trivial cross-vendor workflow: takeoff from the design coordination platform → estimate from the orchestrator's mechanical sub-network → procurement quotes from the scheduling vendor's supplier integration → schedule reservation back from the scheduler. Three vendors, four agent hops, every typed handoff via TACO.

The Authority's OpenTelemetry traces showed every hop. The orchestration vendor's dashboard surfaced any failures within seconds. The scheduling vendor's integration with the financial system meant the procurement decisions automatically flowed into the budget tracking — no manual reconciliation.

---

## What the Authority got

In quantitative terms, after 90 days:

- **Zero point-to-point integrations** written by the Authority's IT team. Vendors integrate via the protocol, not via Authority-specific glue.
- **One project registry**, one set of typed artifacts. Every workflow's data is in the Authority's project record in TACO's typed schemas.
- **Conformance verification** before each vendor's quarterly check-in. The conformance runner is part of the Authority's vendor performance review.
- **Audit trail** for every change order, RFI, submittal review — including the source agent and timestamp for every typed baseline.

In operational terms:

- The Authority's project team stopped reconciling spreadsheets. The typed artifacts arrive structured; the dashboards render them; no one rebuilds anything in Excel.
- When the design coordination platform pushed an update that broke their schema validation (week 7), the Authority's orchestrator caught it within an hour — and the vendor fixed it within four hours. Pre-TACO, this kind of issue typically went unnoticed for days because nobody validated downstream.
- The small specialty vendor's agent integrated cleanly with the larger vendors. The procurement officer's worry about scale didn't materialize because TACO meant the small vendor didn't have to scale their integration team — the protocol was the integration.

---

## What the Authority gave up

Being honest:

- **Three vendors with strong existing relationships were excluded** for not meeting the gate. The procurement officer fielded calls; some of those vendors may not bid on future Authority work because of this. The Authority decided that was an acceptable cost.
- **Higher pricing on some bids.** The mature-TACO vendors knew they were qualified-set members and priced confidently. The Authority paid roughly 5% more on two contracts than they likely would have under the previous RFP regime — a premium they accepted in exchange for the integration story.
- **More technical evaluation work.** Scoring the conformance reports, evaluating recommended-capability tradeoffs, weighting trust tiers — the procurement team had to learn new things. Anika's office trained four procurement officers on the rubric during the RFP cycle.

---

## What other owners should do

Anika wrote a one-page lessons-learned for the Authority's procurement committee and shared it informally with peers in other municipalities. The summary:

1. **Add TACO requirements to your next major capital-project IT RFP.** Use the [public template](/docs/rfp-template); the language is already vetted.
2. **Treat the conformance runner result as a hard gate.** Don't let vendors argue around it. The verifiability is the point.
3. **Be ready for established vendors to push back.** They'll argue the requirement is vendor-specific. It isn't — it's a Linux Foundation-grounded open standard. Hold the line.
4. **Reserve some scoring weight for trust tier and integration breadth**, not just for "all checks pass." A vendor with all-checks-pass plus tier-2 verification and 10 supported integrations is meaningfully more valuable than one with all-checks-pass alone.
5. **Don't expect the small-vendor effect to be hypothetical.** TACO levels the technical playing field — small vendors who self-adopt can suddenly compete with incumbents on integration story. Take small-vendor responses seriously.
6. **Plan to use this language on every capital project from now on.** Single RFPs don't move markets; consistent buyer behavior does.

---

## What's still hard

- **The hosted public registry hasn't shipped yet.** The Authority runs its own project registry, which means each new vendor URL has to be registered manually. When the public registry is available ([roadmap](/docs/roadmap)), discovery becomes one less step.
- **Token Exchange remains operationally tricky.** The Authority's IT team built a custom auth server to issue project-scoped tokens; this isn't yet the easy path. Out-of-the-box deployments of common IdP products would help adoption.
- **The conformance runner is structural, not behavioral.** Anika still relies on the technical evaluation phase to catch quality issues that pass conformance but produce bad outputs. Future runner enhancements (per-skill behavioral tests) would close this gap.

---

## See also

- [Oakridge Medical week](./oakridge-medical-week) — GC-side, steady-state
- [Stafford Mechanical onboarding](./stafford-mechanical-onboarding) — sub-side, adoption mode
- [RFP Template](/docs/rfp-template) — the artifact this case study uses
- [From RFP to running](/blog/from-rfp-to-running) — the operational companion blog post
- [For Owners](/for/owner) — the broader owner-side framing
