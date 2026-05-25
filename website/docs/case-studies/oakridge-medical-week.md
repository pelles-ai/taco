---
title: "Case study: A typical week on the Oakridge Medical project"
description: A week-by-week walkthrough of how TACO agents coordinate across a 50-story medical project — takeoffs, RFIs, procurement, scheduling, change orders, and bid leveling, told as a continuous narrative.
sidebar_position: 1
---

# Case study: A typical week on the Oakridge Medical project

:::note Illustrative
This case study is fictional but realistic. Project name, agents, and specifics are composed from patterns we've seen in early TACO deployments. Use it to understand how the recipes fit together in actual project flow, not as a real project record.
:::

## The project

**Oakridge Medical Center.** 1.2M square feet, 50 stories, mixed-use medical + research. Three trade subs primary, fifteen secondary. Project ID `PRJ-2026-OAKRIDGE-MEDICAL`. Currently 18 months into a 36-month build, in the mechanical-rough-in phase for floors 12–22.

The GC is BuildRight Partners. They've been on TACO for nine months. Their agent stack:

- **`gc-orchestrator`** — multi-trade, runs in BuildRight's VPC; the conductor for everything in this story
- **`mech-estimator-pro`** — mechanical, third-party (Climatec); priced + lead-time intelligence for HVAC and plumbing
- **`pipeworks-supply`** — mechanical supplier, lives at PipeWorks' DC; quotes copper, valves, fittings against `bom-v1`
- **`metroflow-distribution`** — second supplier; same skill, different inventory model
- **`design-responder`** — architectural, runs in the architect's environment; handles RFI responses
- **`schedule-coordinator`** — multi-trade, internal BuildRight tool; canonical source for `schedule-v1`
- **`drawing-auditor`** — multi-trade, internal; audits coordinated drawings for conflicts

Trust tiers: all internal agents tier-1 (org verified); third-party agents tier-2 (cert-attested via PipeWorks' SOC2 and Climatec's). The design responder runs against a tier-1 verification of the architect's domain.

---

## Monday — RFI from the drawing audit

**8:12 AM.** The drawing-auditor agent runs its overnight pass against the latest coordinated set (Rev D, issued Friday). It flags 14 candidate conflicts. After deduplication against open RFIs and severity filtering, 3 are forwarded for human review.

One is selected to dispatch: a 4" hot-water supply on M-201 routed through a structural beam at column line C/4, but S-201 shows the beam as continuous with no penetration.

The auditor emits an `rfi-v1`:

```json
{
  "projectId": "PRJ-2026-OAKRIDGE-MEDICAL",
  "subject": "Pipe routing conflict at column line C/4",
  "question": "M-201 shows 4\" hot water supply routed through structural beam at C/4. S-201 shows beam continuous. Confirm intended routing or beam penetration acceptance.",
  "category": "design-conflict",
  "priority": "high",
  "references": [
    {"sheetId": "M-201", "area": "grid C4"},
    {"sheetId": "S-201", "area": "grid C4"}
  ],
  "metadata": {
    "generatedBy": "drawing-auditor-v1",
    "generatedAt": "2026-05-25T13:12:00Z",
    "confidence": 0.94
  }
}
```

**8:13 AM.** The orchestrator (which had subscribed to the auditor's push notifications) receives the artifact. It dispatches the RFI to `design-responder` via `send_message("rfi-response", rfi)`. Token narrowed via [Token Exchange](/docs/security) — `taco:task:rfi-response taco:project:PRJ-2026-OAKRIDGE-MEDICAL:write` is what the responder receives, not the orchestrator's broader scope.

**11:47 AM.** The responder agent, after consulting the architect's CDE for the latest structural drawing version, returns a typed response artifact:

```json
{
  "status": "answered",
  "response": "Confirmed: the beam at C/4 between floors 12–22 has been redesigned with a penetration sleeve. See revised S-201 Rev E (uploaded today). Mechanical routing per M-201 is correct.",
  "respondedBy": "architect-design-responder-v2",
  "respondedAt": "2026-05-25T16:47:00Z",
  "referenceTaskIds": ["task-auditor-1812"]
}
```

The orchestrator persists the round-trip linked via `reference_task_ids`. The whole RFI from detection to typed response took 3 hours 35 minutes. Pre-TACO, the same flow at this GC averaged 4.5 days.

---

## Tuesday — Takeoff, estimate, and a procurement fan-out

**6:30 AM.** Takeoff trigger fires for the floor 18 mechanical rough-in package. The orchestrator calls the internal takeoff agent (not shown explicitly in this case study; conceptually similar to the [GC chain recipe](/docs/cookbook/gc-estimator-supplier-chain)).

The takeoff returns a `bom-v1` with 247 line items, totaling 8,400 LF of copper, 320 valves, 1,100 fittings. Confidence 0.91 — three items flagged for human review (unusual fitting sizes).

**6:33 AM.** Orchestrator dispatches `estimate` to `mech-estimator-pro`:

```python
async with TacoClient(agent_url=estimator.url) as client:
    est_task = await client.send_message("estimate", bom)
```

The estimator's response arrives in 47 seconds. Total: $187,400. Breakdown: $94,200 material, $76,800 labor (530 hours × $145), $16,400 equipment.

**6:34 AM.** Now the procurement fan-out. The orchestrator runs the [BOM-to-Quote Marketplace recipe](/docs/cookbook/bom-to-quote-marketplace) against three suppliers in parallel:

```
Supplier                       Total      Max lead
----------------------------------------------------
PipeWorks Supply               $91,200       3d
MetroFlow Distribution         $87,400       7d
Eastern Pipe + Supply          $89,100       2d
```

Selection policy on this project: cheapest within 4-day lead time. **MetroFlow's $87,400 is rejected** (lead time exceeds cap). **Eastern Pipe wins at $89,100, 2-day lead.** PipeWorks loses by $2,100.

But the orchestrator's policy logic emits a note: PipeWorks is a preferred supplier this quarter under a volume rebate. The structured decision payload carries `selection_reason: "cheapest-within-lead-cap"` and `runner_up: "pipeworks-supply"` with the delta. Tomorrow morning's project manager standup will see both and decide whether to override.

---

## Wednesday — Schedule-aware reconciliation

**9:00 AM.** The PM, reviewing yesterday's auto-selection, asks the orchestrator to run the [Schedule-Aware Procurement check](/docs/cookbook/schedule-aware-procurement) against the winning quote.

The orchestrator pulls the current schedule from `schedule-coordinator` and reconciles each line item's lead time against the activity that consumes it:

```
On time (243 items):
  CU-12-L          activity=A-1810  lead=2d  slack=11d
  EL-90-12         activity=A-1810  lead=2d  slack=11d
  ...

Late (4 items):
  SOL-CU-FLUX      activity=A-1810  lead=2d  slack=11d  decision=on-time
  VALVE-4IN-BFLY   activity=A-1830  lead=5d  slack=2d   decision=late
  GASKET-4IN       activity=A-1830  lead=5d  slack=2d   decision=late
  ...
```

Two large butterfly valves and matching gaskets won't make their activity start by enough margin. The orchestrator pushes a structured `change-order-analysis` skeleton to the PM dashboard and notifies the procurement coordinator to either expedite (Eastern's air freight option, +$340) or re-source.

The PM picks expedite. The orchestrator updates Eastern's PO via the supplier agent's `update_quote` call and the schedule's reservation stays intact.

---

## Thursday — Change order

**1:14 PM.** Owner requests adding HVAC zoning to the level 19 east wing — a late scope addition for the cancer treatment suite that's been added to the program.

The orchestrator calls `change-order-analyzer` (a thin wrapper around the [Change Order Impact recipe](/docs/cookbook/change-order-impact)). The analyzer:

1. Fetches the current `estimate-v1` from `mech-estimator-pro` (baseline material cost: $94,200 for the level-18 BOM context)
2. Fetches the current `schedule-v1` from `schedule-coordinator` (baseline shows activity A-1910 starting 2026-06-12)
3. Constructs a `bom-v1` for the proposed scope: 6 VAV boxes, 240 LF supply ductwork, 8 thermostats, control wiring
4. Calls `mech-estimator-pro` again for the new scope: $14,800
5. Computes schedule impact: 4 days additional on A-1910 (rough-in), 2 days on A-1920 (commissioning). Net 4 days because they're parallel.

Emits a `change-order-v1`:

```json
{
  "projectId": "PRJ-2026-OAKRIDGE-MEDICAL",
  "changeOrderId": "CO-2026-019",
  "description": "Add HVAC zoning for level 19 east wing (cancer treatment suite)",
  "costImpact": {
    "amount": 14800,
    "currency": "USD",
    "baselineTotal": 187400,
    "newTotal": 202200
  },
  "scheduleImpact": {
    "deltaDays": 4,
    "affectedActivities": ["A-1910", "A-1920"]
  },
  "status": "proposed",
  "metadata": {
    "generatedBy": "change-order-analyzer-v1",
    "generatedAt": "2026-05-28T13:14:00Z",
    "baselineSources": {
      "estimate": "mech-estimator-pro@2026-05-28T06:34:00Z",
      "schedule": "schedule-coordinator@2026-05-28T13:13:00Z"
    }
  }
}
```

`baselineSources` records exactly which agent versions and timestamps produced the baseline. When the owner reviews the CO and asks "what schedule was this against?", the answer is in the artifact itself, not in someone's email thread.

The PM reviews; signs the CO; the orchestrator publishes the approved version. Downstream agents (procurement, scheduling) subscribed to the CO topic receive push notifications and update their plans.

---

## Friday — Bid leveling for the next phase

**10:00 AM.** Five subcontractors have submitted bids for the floor 23–32 mechanical package. The bids landed in BuildRight's project management platform as PDFs over the past week.

The orchestrator invokes `bid-leveling-agent` (not yet in the cookbook; on the [roadmap](/docs/roadmap)). This agent:

1. Reads each bid PDF (via MCP to a PDF extraction service — see [the protocol stack](/docs/protocol-stack))
2. Normalizes each into a typed `estimate-v1` artifact
3. Identifies scope inclusions, exclusions, and assumptions per bid
4. Emits a `bid-comparison-v1` that lines them up apples-to-apples

The leveled view:

```
Sub               Base       Adj. Base    Notes
-------------------------------------------------------
Apex Mechanical   $1.84M     $1.86M       Excludes commissioning
Climatec          $1.72M     $1.78M       Includes commissioning
Northeast HVAC    $1.91M     $1.91M       Full scope
Standard Air      $1.68M     $1.74M       Excludes test/balance + commissioning
Vertex Industrial $1.79M     $1.79M       Full scope, preferred-sub
```

Adjusted base normalizes for scope differences (adding back the work some subs excluded). Standard Air's headline-low $1.68M becomes $1.74M after the gaps are priced — still the leader, but by less than they appeared.

The agent flags Vertex's bid for preferred-sub treatment (rebate program) and notes Climatec is currently this project's mechanical estimator, raising a potential conflict for the PM's awareness.

The PM exports the leveled comparison as a typed artifact for the bid review meeting Monday morning.

---

## What the week shows

In five days, this project's agent stack handled:

- **1 RFI round-trip** — 3.5 hours vs the pre-TACO 4.5-day average
- **1 takeoff + estimate + procurement chain** — generated, priced, and selected in under 90 seconds of agent time (plus human review on Wednesday)
- **1 schedule reconciliation** — caught 4 late items and triggered an expedite, no manual lead-time tracking
- **1 change order with auditable baselines** — recorded the exact source agent + timestamp for every input
- **1 bid leveling cycle** — turned 5 PDFs into a typed comparison; identified the genuine leader vs the headline-low bid

What's notable is *not* that any single operation is dramatically faster (some are; some aren't). It's that **the typed handoffs reduce coordination overhead**. The PM didn't reconcile spreadsheets; the agents passed typed artifacts. The CO had its baselines built in; nobody had to email "which schedule version was this against?" An RFI link was preserved via `reference_task_ids`; no manual cross-referencing.

The cost of this setup: BuildRight runs 7 agents (3 internal, 3 third-party supplier-side, 1 architect-side). Each was a one-time integration effort. The marginal cost of the next project is configuration (project ID, scope, supplier set), not new integrations — every TACO-compatible supplier is one `registry.register("https://...")` call away.

## Caveats worth flagging

This is a clean week. Real weeks include:

- Agents that hang and need timeouts to reach failure visibly
- Schema drift between an agent's claimed `outputSchema` and what it actually emits (caught by strict validation; see [Pitfalls](/docs/pitfalls))
- Token Exchange misconfigurations that surface as confusing 403s
- Stale registry entries pointing at dead deployments

The patterns in the [Cookbook](/docs/cookbook/) and [Pitfalls](/docs/pitfalls) cover most of these. Production teams develop instincts for which to instrument and which to alert on.

## See also

- All five [cookbook recipes](/docs/cookbook/) — this story uses each at least once
- [Best Practices](/docs/best-practices) — production-grade defaults the BuildRight team uses
- [Common Pitfalls](/docs/pitfalls) — the things this clean narrative glosses over
- [For General Contractors](/for/general-contractor) — the GC-side framing
