---
title: GC → Estimator → Supplier
description: Canonical three-hop chain — orchestrator generates a BOM, hands it to an estimator for cost, then to a supplier for live pricing. End-to-end typed.
sidebar_position: 1
---

import SequenceDiagram from '@site/src/components/SequenceDiagram';

# GC → Estimator → Supplier chain

The canonical multi-agent construction workflow: a general contractor's orchestrator agent generates a takeoff from drawings, hands the typed BOM to a mechanical estimator for pricing, and finally to a supplier agent for live unit pricing and lead times. Three companies, three agents, one chain of typed handoffs.

## Goal

Produce a priced, sourced material plan for a project — fully agent-driven, no custom integrations between vendors.

## Agents involved

| Agent | Trade | Skills advertised |
|------|-------|---------------------|
| **GC Orchestrator** | `multi-trade` | `takeoff`, `schedule-coordination` |
| **Mech Estimator Pro** | `mechanical` | `estimate`, `value-engineering` |
| **PipeWorks Supply** | `mechanical` | `material-procurement` |

Each agent advertises itself with a [Construction Agent Card](/docs/agent-card-extensions) at `/.well-known/agent-card.json`. The orchestrator discovers the other two via the [registry](/docs/sdk#agentregistry).

## Sequence

<SequenceDiagram
  actors={[
    {id: 'gc', label: 'GC Orchestrator', sub: 'multi-trade'},
    {id: 'est', label: 'Estimator', sub: 'mechanical'},
    {id: 'sup', label: 'Supplier', sub: 'mechanical'},
  ]}
  messages={[
    {from: 'gc', to: 'gc', label: 'generate takeoff (local)', schema: 'bom-v1'},
    {from: 'gc', to: 'est', label: 'send_message("estimate", bom)', schema: 'bom-v1'},
    {from: 'est', to: 'gc', label: 'returns estimate', schema: 'estimate-v1', kind: 'return'},
    {from: 'gc', to: 'sup', label: 'send_message("material-procurement", bom)', schema: 'bom-v1'},
    {from: 'sup', to: 'gc', label: 'returns quote', schema: 'quote-v1', kind: 'return'},
  ]}
/>

## Full Python

This runs against a live `taco-agent` install. Each agent is a separate process; the orchestrator finds them via the registry and chains the calls.

```python
import asyncio
from taco import (
    AgentRegistry,
    TacoClient,
    extract_structured_data,
)

PROJECT_ID = "PRJ-2026-OAKRIDGE-MEDICAL"

async def main() -> None:
    # 1. Discover the agents we need
    registry = AgentRegistry()
    await registry.register("http://estimator.example.com:8001")
    await registry.register("http://pipeworks.example.com:8002")

    estimator = registry.find(trade="mechanical", task_type="estimate")[0]
    supplier = registry.find(trade="mechanical", task_type="material-procurement")[0]

    # 2. Locally generate the BOM (in a real workflow, this would itself
    # be a `takeoff` call to a takeoff agent — kept local here for brevity)
    bom = {
        "projectId": PROJECT_ID,
        "trade": "mechanical",
        "csiDivision": "23",
        "lineItems": [
            {"id": "L-001", "description": "Copper pipe, type L",
             "quantity": 120, "unit": "LF", "size": "3/4\""},
            {"id": "L-002", "description": "90° elbow, type L",
             "quantity": 24, "unit": "EA", "size": "3/4\""},
        ],
        "metadata": {"generatedBy": "gc-orchestrator-v1",
                     "generatedAt": "2026-05-24T15:00:00Z"},
    }

    # 3. Estimator hop
    async with TacoClient(agent_url=estimator.url) as client:
        est_task = await client.send_message("estimate", bom)
    estimate = extract_structured_data(est_task.artifacts[0].parts[0])
    print(f"Estimator says total: ${estimate['summary']['total']:,} "
          f"{estimate['currency']}")

    # 4. Supplier hop — note the BOM (not the estimate) is sent;
    #    suppliers price the BOM directly
    async with TacoClient(agent_url=supplier.url) as client:
        quote_task = await client.send_message("material-procurement", bom)
    quote = extract_structured_data(quote_task.artifacts[0].parts[0])

    print(f"\nSupplier quote from {quote['supplier']['name']}:")
    for item in quote["items"]:
        line_total = item["unitPrice"] * item["quantity"]
        print(f"  {item['sku']:<10} qty={item['quantity']:<4} "
              f"unit=${item['unitPrice']:.2f}  →  ${line_total:.2f}  "
              f"(lead {item['leadTimeDays']}d)")

    print(f"\nQuote valid until: {quote['validUntil']}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Typed data flowing through

The same `bom-v1` artifact reaches both the estimator and the supplier — that's the whole point. Neither agent has to guess at the input shape because both declared `inputSchema: "bom-v1"` in their Agent Cards.

The estimator returns an [`estimate-v1`](../schemas/estimate-v1), the supplier returns a [`quote-v1`](../schemas/quote-v1). The orchestrator can persist both as typed records linked to the project ID.

## Variations

- **Add a value-engineering pass.** Insert a `value-engineering` call between the estimate and the supplier hops. The VE agent reads the estimate, suggests substitutions, and returns a revised BOM.
- **Fan out to multiple suppliers.** Use the [BOM-to-Quote Marketplace](./bom-to-quote-marketplace) pattern to query several suppliers in parallel and select the best quote.
- **Cross-check against schedule.** See [Schedule-Aware Procurement](./schedule-aware-procurement) — reject quotes whose lead time exceeds the activity's planned start.
- **Streaming progress.** Replace `send_message` with `stream_message` and watch each agent's `TaskStatusUpdate` events as they work. Useful for long-running takeoffs.

## See also

- [Core Concepts: Tasks, Messages, Artifacts](../core-concepts)
- [`bom-v1`](../schemas/bom-v1) · [`estimate-v1`](../schemas/estimate-v1) · [`quote-v1`](../schemas/quote-v1)
- [Agent-to-Agent Communication](../getting-started/multi-agent)
