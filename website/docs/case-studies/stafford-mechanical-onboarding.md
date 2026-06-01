---
title: "Case study: Stafford Mechanical's first TACO deployment"
description: A 3-week onboarding narrative — a regional mechanical sub's path from "what is TACO" to discoverable by every GC on their roster. Deliberately small-scale and adoption-mode, complementing the larger Oakridge tower case study.
sidebar_position: 2
---

# Case study: Stafford Mechanical's first TACO deployment

:::note Illustrative
Fictional but realistic. Composed from patterns we've seen in early sub-side adoptions. Use it to understand what a *first* TACO deployment looks like — the steady-state running of an established stack is the [Oakridge Medical case study](./oakridge-medical-week).
:::

## The shop

**Stafford Mechanical Contractors.** A regional mechanical sub in the Mid-Atlantic — about 45 field staff, 8 in the office. Mostly mid-sized commercial (medical office buildings, school renovations, smaller industrial). Annual revenue around $22M. They've been in business 23 years.

Their tech stack before TACO:
- **FastPIPE** (Trimble) for hydronic takeoffs
- **Accubid** for estimating
- **Excel** for everything else (lead times, supplier comparisons, schedule reservations)
- **One Procore login** because three of their GC customers require it

They don't have a CTO. They have **Lia**, who runs operations and writes Excel macros. The owner, **Marcus**, has been hearing about "agent stuff" from three different GCs in the past quarter and asked Lia to "figure out what we actually have to do."

This is the story of the three weeks Lia spent getting Stafford onto TACO.

---

## Week 1 — Reading and a quick-start

**Monday.** Lia starts on the TACO docs. Reads the [Why TACO](/docs/why-taco) page, then [For Subcontractors](/for/subcontractor), then [For Mechanical Trades](/for/mechanical). Total reading time: about 90 minutes.

Two things land for her:

1. The protocol doesn't require Stafford to rebuild Accubid or FastPIPE. It requires a small new agent that translates between TACO's typed surface and their existing tools.
2. "Discoverable by every GC on their roster" isn't marketing — it's mechanical: each GC's orchestrator runs `registry.find(trade="mechanical")`. If Stafford's agent shows up there, they're discoverable.

Lia messages Marcus: "I think this is doable. Let me try the quick-start."

**Tuesday morning.** Lia opens the [Quick Start](/docs/getting-started/quick-start), runs `pip install taco-agent`, copies the 30-line example into `stafford_estimator.py`, runs it. Local agent is up, returning canned data.

```bash
$ python stafford_estimator.py
INFO:     Started server process [42137]
INFO:     Uvicorn running on http://0.0.0.0:8080
```

She opens `/monitor` in her browser. Sends the example task via curl. Watches the trace flow through the dashboard. **8:14 PM Tuesday: she's seen an agent work end to end.** That's the moment that flips this from "another protocol fad" to "I can actually do this."

**Wednesday.** Lia walks through [Build a Custom Agent](/docs/getting-started/build-agent) and the [For Mechanical Trades](/for/mechanical) page side by side. She mocks up Stafford's agent card:

```python
card = ConstructionAgentCard(
    name="Stafford Mech Estimator",
    description="Mechanical estimating for mid-sized commercial projects (MD/VA/DC).",
    url="http://localhost:8080",
    trade="mechanical",
    csi_divisions=["22", "23"],
    project_types=["commercial", "healthcare", "education"],
    integrations=["procore"],
    skills=[
        ConstructionSkill(
            id="generate-estimate",
            task_type="estimate",
            input_schema="bom-v1",
            output_schema="estimate-v1",
            description="Estimate mechanical work from a typed BOM. Returns "
                        "line-item cost, labor hours, and overhead/profit summary.",
        ),
    ],
)
```

She handwrites the handler. For now it returns a fake estimate (sum of line items times a flat rate). The point this week is structure, not logic.

**Thursday.** Lia points the [conformance runner](/conformance) at her local agent. It catches three issues:

- Her agent card declares `trade: "Mechanical"` (capital M) instead of `"mechanical"`. **Fixed.**
- Her `csi_divisions` were `["22.0", "23.0"]` (Python float-ish) instead of `["22", "23"]`. **Fixed.**
- The agent doesn't expose `/health`. **Fixed by adding `enable_health=True` to `A2AServer(...)`.**

She runs it again. All required checks pass.

**Friday.** Lia shows the running agent + the green conformance report to Marcus. Marcus: "OK. Now what?"

Lia: "Now I make the handler actually call Accubid instead of fake data. And we get a real URL with TLS. And we tell the GCs we work with."

---

## Week 2 — Wiring the real handler

**Monday.** Lia replaces the fake handler logic with a real one. Stafford's Accubid system runs on an internal server; she writes a small client that:

1. Receives a `bom-v1` from the TACO handler
2. Converts each line item to Accubid's CSV import format
3. POSTs it to Accubid's internal estimate endpoint (this took 4 hours of poking at Accubid's documentation; she now knows more about Accubid's API than she ever wanted to)
4. Reads back the estimate as a CSV
5. Parses the CSV into a typed `estimate-v1` artifact

The handler is about 80 lines. Lia commits a `stafford_estimator/` Python package to a private GitHub repo.

**Tuesday.** Lia tests the real handler with last quarter's actual BOMs (she has them in a `/archive/` folder). For 8 of 10 historical BOMs, the agent's returned estimate matches Accubid's spreadsheet output within $200. For 2 of them, the agent's output is materially wrong — turns out Accubid's labor markup rules don't import cleanly from CSV. She files this as `flaggedItems: [...]` in the estimate's metadata and works around it for now.

**Wednesday.** Deployment. Marcus has a small DigitalOcean account. Lia spins up a $24/mo droplet, gets Let's Encrypt working for `agents.staffordmech.com`, deploys the estimator with `uvicorn`. Total infrastructure cost: ~$300/year.

She runs the conformance runner against the public URL. **All required + 4 of 6 recommended checks pass.** The two she's skipping for v1: OpenTelemetry traces (no observability stack yet) and Token Exchange (no OAuth provider yet — she's using a simple bearer-token allowlist for now).

**Thursday.** Lia drafts an email to Stafford's top three GC customers. The email is short:

> Hi [Marie / Dan / Chen],
>
> We've published a TACO-compatible estimating agent at `https://agents.staffordmech.com`. Your orchestrator can discover it via `registry.find(trade="mechanical", csi_divisions=["22", "23"])`.
>
> If you'd like a typed estimate on a current bid, your agent stack can talk directly to ours — no portal scraping, no PDFs.
>
> Conformance report attached. Happy to discuss.
>
> — Lia, Stafford Mechanical

Two of the three reply within 48 hours. One says "great, we'll register your URL in our staging orchestrator and try it on the [REDACTED] project this week." The other says "we don't have an orchestrator yet but we're starting to. Will keep your URL on file." The third doesn't respond for two weeks but eventually loops in their PM.

**Friday.** First real call from a customer's orchestrator. Stafford's agent receives a `bom-v1` for a small medical office HVAC scope, returns an `estimate-v1`. The customer's PM emails back: "Total looks about right; can you also break out the labor hours separately?"

Lia checks the artifact she's emitting — it already includes labor hours in `lineItems[].labor.hours`. The PM was looking at the summary view in their dashboard, which only showed the total. Lia explains. The PM updates their dashboard query.

This is the first round-trip that resulted in someone actually reading typed structured output instead of a PDF.

---

## Week 3 — Iteration and the first conflict

**Monday.** Lia gets a second call from the same customer — different scope, different project. She watches the request in `/monitor`. The estimate comes back, the customer's orchestrator persists it.

But there's a problem: the orchestrator's logs show it tried `registry.find(trade="mechanical", task_type="material-procurement")` and got nothing. Stafford doesn't advertise that skill — they don't quote material directly; that's their supplier's role.

Lia could add a `material-procurement` skill that's actually a passthrough to PipeWorks' agent. But that would be wrong — Stafford isn't a supplier. She emails the customer's PM and says "for procurement, register PipeWorks' agent: `https://pipeworks.example.com/.well-known/agent-card.json`." The customer does so. Now their orchestrator finds both.

This is when Lia understands the registry model viscerally: the *project* has a registry. Each org adds the agents they want their orchestrator to know about. Stafford doesn't have to provide every capability — they just have to provide *theirs* accurately.

**Tuesday.** Marcus, watching from outside, asks Lia for a one-page summary of where Stafford is.

Lia writes it:

> **Stafford Mechanical — TACO deployment, Week 3**
>
> - One agent live at `https://agents.staffordmech.com`. Cost: $300/yr infrastructure + ~2 weeks of my time.
> - Conformance: all required checks pass, 4 of 6 recommended.
> - Discoverable by `registry.find(trade="mechanical", csi_divisions=["22", "23"])`.
> - 2 of our top 3 GCs have registered our URL. 6 estimate calls received in the first 5 days (3 dev/test, 3 real bids).
> - 0 portals scraped, 0 PDFs hand-rebuilt, 0 spreadsheet handoffs for those 3 real bids.
>
> Next: add OpenTelemetry so we can see latency / failures in the dashboard. Then handle the labor-markup edge case properly so all estimates match Accubid within $50.

Marcus signs off on the next month of iteration.

**Wednesday.** Lia hits her first production issue. A bid comes in via the agent; her handler crashes on a line item with `unit: "MSF"` (thousand square feet — a non-standard unit her CSV parser doesn't recognize). The task transitions to `failed`. The customer's orchestrator logs the failure clearly because the task ID + context ID + error class are all tagged.

Lia adds `MSF` to her unit handling, ships a fix, the customer's orchestrator retries successfully. **The whole incident — failure, diagnosis, fix, retry — took 47 minutes.** Pre-TACO, the same incident would have been "your estimate looks weird," a phone call, a re-send of the PDF, a manual re-estimate. Probably half a day.

**Thursday.** Lia adds OpenTelemetry. Three lines of code in her handler, spans appearing in their existing Datadog account (which they already had for accounting). She now has p50/p95/p99 latency for every call.

**Friday — end of Week 3.** Lia tells Marcus they're production-ready. Marcus asks her to write up the experience for the rest of the office. She drafts a one-pager and pins it to their internal wiki.

---

## What the three weeks show

**Time investment:** roughly 2 weeks of one person's time. Not a project; not a budget item; just an operational priority for a few weeks.

**Cost:** $300/year infrastructure. No licensing. No consultants.

**Outcome:** Stafford is now in the registry path for any of their GC customers' orchestrators. Each typed estimate they return saves the GC team the manual rebuild step that used to consume hours per bid.

**What didn't happen:** They didn't replace Accubid. They didn't rebuild FastPIPE. They didn't change their internal workflow. The TACO agent is a thin wrapper around what they were already doing — what's new is that it's *machine-callable from outside Stafford*.

## What's hard about the sub-side

Worth being honest about:

- **Accubid CSV roundtrip.** The labor-markup edge case took two weeks of intermittent investigation. Stafford got there because Accubid is well-documented. A shop using a more bespoke estimating tool would have hit more friction.
- **The conformance runner caught configuration bugs Lia would not have found.** Without it, her trade enum capitalization issue would have lived in the agent card until a GC's orchestrator silently filtered her out.
- **The customers needed to be told.** TACO discovery isn't yet automatic — no one's orchestrator just *finds* Stafford's URL. Lia had to email them. When the hosted registry ships ([on the roadmap](/docs/roadmap)), that step closes.
- **Marcus was patient.** Three weeks is a short investment if it works; it's an eternity if you don't see anything for the first two weeks. Marcus tolerated that because Lia showed him the monitor UI in Week 1.

## What we'd tell another sub starting this week

1. **Do the quick-start on day one.** The 30-line example, running in your browser's monitor, is the moment that makes the rest believable.
2. **Wire a single skill before adding others.** Stafford launched with one skill (`estimate`). Their next addition (a `value-engineering` skill that suggests substitutions) is a week of work once the foundation is real.
3. **Run the conformance runner constantly.** Every change to the agent card; every deploy. The 30 seconds it takes catches bugs your customers would otherwise hit first.
4. **Tell your top customers manually.** Until the hosted registry ships, discovery requires that someone tells someone about your URL. Don't wait.
5. **Don't pretend to do skills you don't.** Stafford didn't add a fake `material-procurement` skill. That kind of overreach breaks downstream orchestrators and ruins your reputation in the registry faster than any feature gap would.

## See also

- [Oakridge Medical week](./oakridge-medical-week) — the sibling case study at the other end of the scale (steady-state, full GC stack)
- [For Subcontractors](/for/subcontractor) — the framing Lia started from
- [For Mechanical Trades](/for/mechanical) — the trade-specific guidance
- [Quick Start](/docs/getting-started/quick-start) — Lia's day-one
- [Build a Custom Agent](/docs/getting-started/build-agent) — Lia's day-three
- [Common Pitfalls](/docs/pitfalls) — the configuration issues the conformance runner caught for her
