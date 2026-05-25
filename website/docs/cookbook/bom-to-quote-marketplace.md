---
title: BOM-to-Quote Marketplace
description: Fan a single BOM out to multiple supplier agents in parallel, then level the quotes. asyncio.gather with TACO clients plus best-quote selection.
sidebar_position: 3
---

import SequenceDiagram from '@site/src/components/SequenceDiagram';

# BOM-to-Quote Marketplace

When you need pricing from several suppliers, the right move is parallel, not serial. This recipe fans a single typed BOM out to every supplier agent in the registry that handles the right trade, awaits all of them concurrently, and selects the best quote by a policy you control (cheapest, fastest, cheapest-with-acceptable-lead, weighted score).

## Goal

Get apples-to-apples quotes from many suppliers in one round-trip, with no per-supplier integration code.

## Agents involved

| Agent | Role | Skills advertised |
|------|---------------------|---------------------|
| **Procurement Orchestrator** | Caller | (consumes `material-procurement`) |
| **PipeWorks Supply** | Supplier #1 | `material-procurement` |
| **MetroFlow Distributors** | Supplier #2 | `material-procurement` |
| **Cast Iron Materials** | Supplier #3 | `material-procurement` |

All three suppliers advertise themselves with `trade: "mechanical"` and `skills: [material-procurement]`. The orchestrator discovers them generically.

## Sequence

<SequenceDiagram
  actors={[
    {id: 'orch', label: 'Procurement', sub: 'orchestrator'},
    {id: 's1', label: 'Supplier A', sub: 'PipeWorks'},
    {id: 's2', label: 'Supplier B', sub: 'MetroFlow'},
    {id: 's3', label: 'Supplier C', sub: 'Cast Iron'},
  ]}
  messages={[
    {from: 'orch', to: 's1', label: 'send_message(bom)', schema: 'bom-v1'},
    {from: 'orch', to: 's2', label: 'send_message(bom)', schema: 'bom-v1'},
    {from: 'orch', to: 's3', label: 'send_message(bom)', schema: 'bom-v1'},
    {from: 's1', to: 'orch', label: 'returns', schema: 'quote-v1', kind: 'return'},
    {from: 's2', to: 'orch', label: 'returns', schema: 'quote-v1', kind: 'return'},
    {from: 's3', to: 'orch', label: 'returns', schema: 'quote-v1', kind: 'return'},
  ]}
/>

The three `send_message` calls are dispatched concurrently with `asyncio.gather`; total wall time is roughly the slowest single supplier, not the sum.

## Full Python

<p>
  <a className="sandbox-open-link" href="/sandbox?preset=bom-to-quote-marketplace">
    ▶ Open this recipe in the in-browser sandbox →
  </a>
</p>

```python
import asyncio
from taco import (
    AgentRegistry,
    TacoClient,
    extract_structured_data,
)


async def quote_one(agent_card, bom):
    """Ask a single supplier for a quote. Returns (agent_name, quote) or None."""
    async with TacoClient(agent_url=agent_card.url) as client:
        try:
            task = await client.send_message("material-procurement", bom)
        except Exception as exc:
            print(f"[{agent_card.name}] failed: {exc}")
            return None
    return agent_card.name, extract_structured_data(task.artifacts[0].parts[0])


def quote_total(quote):
    return sum(item["unitPrice"] * item["quantity"] for item in quote["items"])


def max_lead_time(quote):
    return max(item["leadTimeDays"] for item in quote["items"])


async def main() -> None:
    registry = AgentRegistry()
    for url in [
        "http://pipeworks.example.com:8002",
        "http://metroflow.example.com:8004",
        "http://castiron.example.com:8005",
    ]:
        await registry.register(url)

    suppliers = registry.find(
        trade="mechanical", task_type="material-procurement"
    )
    print(f"Found {len(suppliers)} mechanical suppliers")

    bom = {
        "projectId": "PRJ-2026-OAKRIDGE-MEDICAL",
        "trade": "mechanical",
        "csiDivision": "23",
        "lineItems": [
            {"id": "L-001", "description": "Copper pipe, type L",
             "quantity": 120, "unit": "LF", "size": "3/4\""},
            {"id": "L-002", "description": "Ball valve, brass",
             "quantity": 8, "unit": "EA", "size": "3/4\""},
        ],
        "metadata": {"generatedBy": "procurement-orchestrator-v1",
                     "generatedAt": "2026-05-24T15:00:00Z"},
    }

    # Fan-out
    quotes = await asyncio.gather(*[quote_one(s, bom) for s in suppliers])
    quotes = [q for q in quotes if q is not None]

    if not quotes:
        print("No supplier responded.")
        return

    # Level + report
    print("\nQuotes received:")
    print(f"{'Supplier':<28} {'Total':>10}   {'Max lead':>10}")
    print("-" * 52)
    for name, quote in quotes:
        print(f"{name:<28} ${quote_total(quote):>9,.2f}   "
              f"{max_lead_time(quote):>7}d")

    # Pick by policy — cheapest with acceptable lead time
    MAX_LEAD = 7  # days
    eligible = [
        (name, q) for name, q in quotes if max_lead_time(q) <= MAX_LEAD
    ]
    if not eligible:
        print(f"\nNo quote met lead-time ceiling of {MAX_LEAD}d.")
        return

    winner_name, winner = min(eligible, key=lambda p: quote_total(p[1]))
    print(f"\nSelected: {winner_name} (${quote_total(winner):,.2f}, "
          f"lead {max_lead_time(winner)}d)")


if __name__ == "__main__":
    asyncio.run(main())
```

## Selection policy is a choice

The example above uses *cheapest within a lead-time ceiling*. Real procurement teams use many others — preferred-supplier weighting, on-time delivery history, current rebate programs. The point is that **the policy lives in your code, not in the protocol** — TACO just makes sure every supplier returns the same shape so you can compare them at all.

## Variations

- **Add a minimum trust tier.** `registry.find(trade="mechanical", min_trust_tier=1)` excludes unverified suppliers.
- **Cap concurrency.** Wrap each `quote_one` call in a semaphore if you don't want to hammer suppliers with N parallel requests.
- **Combine with [Schedule-Aware Procurement](./schedule-aware-procurement).** Cross-check the winning lead time against the activity's planned start date before committing.
- **Cache and re-level.** Persist quotes with their `validUntil`, re-level next time the BOM changes.

## Common mistakes

**No concurrency cap.** `asyncio.gather` with N=50 suppliers is a great way to get rate-limited (or banned) from your supplier ecosystem. Wrap each `quote_one` call in a `asyncio.Semaphore(8)` (or whatever feels neighborly). Most suppliers will silently start dropping requests above some threshold without telling you why.

**Picking the cheapest quote, full stop.** The cheapest quote is often the wrong one — wrong lead time, wrong terms, wrong substitution allowed. Encode the project's actual policy (cheapest with lead < 7d AND preferred-supplier-bonus AND no exclusions). The code is the policy; document it.

**Forgetting `validUntil`.** Suppliers price for a window; a quote received Tuesday might be invalid by Friday. Persist quotes with their `validUntil` and re-quote (or auto-decline) when stale.

**Caching quotes too aggressively.** A BOM that changes by one line item invalidates every cached quote. If you cache, key by a hash of the normalized BOM, not by `projectId`.

**Ignoring the supplier's `flaggedItems`.** A supplier returning a quote with `flaggedItems: [{itemId: "L-001", reason: "discontinued"}]` is telling you something important. Surface this in your selection logic before "the cheapest one won."

## Debugging

**Print the leveled comparison before selecting.** The table the example prints (`Supplier · Total · Max lead`) is exactly what a project manager wants to see in audit logs — not just the winner. Log all of it; the selection rationale is part of your defense in a procurement dispute.

**Cap parallelism in dev, not just prod.** Hitting `asyncio.gather` with 8 supplier agents on your laptop will routinely hit local file descriptor limits or DNS rate limits, depending on the OS. Set the semaphore at 4 in dev to avoid mysterious "Connection refused" errors that aren't actually about supplier capacity.

**When a supplier fails silently, instrument the timeout.** A supplier that responds slowly but eventually is different from a supplier that hangs. Use `asyncio.wait_for(quote_one(...), timeout=30)` to bound each call and tag failures with which timeout fired.

## See also

- [`bom-v1`](../schemas/bom-v1) · [`quote-v1`](../schemas/quote-v1)
- [`AgentRegistry`](/docs/sdk#agentregistry)
- [Task type: `material-procurement`](../task-types)
- [Best Practices](../best-practices)
- [Common Pitfalls](../pitfalls)
