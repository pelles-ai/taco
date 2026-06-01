---
title: GC → Estimator → Supplier
description: Canonical three-hop chain — orchestrator generates a BOM, hands it to an estimator for cost, then to a supplier for live pricing. End-to-end typed.
sidebar_position: 1
---

import SequenceDiagram from '@site/src/components/SequenceDiagram';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

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

## Full code

Each agent is a separate process; the orchestrator finds them via the registry and chains the calls.

<p>
  <a className="sandbox-open-link" href="/sandbox?preset=gc-estimator-supplier-chain">
    ▶ Open this recipe in the in-browser sandbox →
  </a>
</p>

<Tabs groupId="lang">
<TabItem value="python" label="Python (taco-agent)" default>

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

</TabItem>
<TabItem value="ts" label="TypeScript (wire format, no SDK)">

```typescript
// TACO doesn't ship a TypeScript SDK yet, but the wire format is plain
// JSON-RPC over HTTP. Everything here is fetch + standard types.

type AgentCard = {
  name: string;
  url: string;
  skills: Array<{id: string; taskType?: string; inputSchema?: string; outputSchema?: string}>;
  'x-construction'?: {trade?: string; csiDivisions?: string[]};
};

type Task = {
  id: string;
  status: {state: string};
  artifacts: Array<{parts: Array<{kind: string; data?: unknown; text?: string}>}>;
};

async function discoverAgent(baseUrl: string): Promise<AgentCard> {
  const res = await fetch(`${baseUrl.replace(/\/$/, '')}/.well-known/agent-card.json`);
  if (!res.ok) throw new Error(`HTTP ${res.status} fetching agent card`);
  return res.json();
}

async function sendMessage(
  agentUrl: string,
  taskType: string,
  payload: unknown,
): Promise<Task> {
  const res = await fetch(agentUrl.replace(/\/$/, '') + '/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: crypto.randomUUID(),
      method: 'message/send',
      params: {
        message: {
          role: 'user',
          parts: [{kind: 'data', data: payload}],
        },
        metadata: {taskType},
      },
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const {result, error} = await res.json();
  if (error) throw new Error(error.message ?? String(error));
  return result as Task;
}

const PROJECT_ID = 'PRJ-2026-OAKRIDGE-MEDICAL';

async function main() {
  // Discover agents by their well-known URLs (no hosted registry yet —
  // see the in-process AgentRegistry in Python for the SDK pattern)
  const estimator = await discoverAgent('http://estimator.example.com:8001');
  const supplier = await discoverAgent('http://pipeworks.example.com:8002');

  const bom = {
    projectId: PROJECT_ID,
    trade: 'mechanical',
    csiDivision: '23',
    lineItems: [
      {id: 'L-001', description: 'Copper pipe, type L', quantity: 120, unit: 'LF', size: '3/4"'},
      {id: 'L-002', description: '90° elbow, type L', quantity: 24, unit: 'EA', size: '3/4"'},
    ],
    metadata: {generatedBy: 'gc-orchestrator-ts-v1', generatedAt: new Date().toISOString()},
  };

  // Estimator hop
  const estTask = await sendMessage(estimator.url, 'estimate', bom);
  const estimate = estTask.artifacts[0].parts[0].data as {
    summary: {total: number};
    currency: string;
  };
  console.log(`Estimator says total: $${estimate.summary.total.toLocaleString()} ${estimate.currency}`);

  // Supplier hop — note the BOM (not the estimate) is sent
  const quoteTask = await sendMessage(supplier.url, 'material-procurement', bom);
  const quote = quoteTask.artifacts[0].parts[0].data as {
    supplier: {name: string};
    items: Array<{sku: string; unitPrice: number; quantity: number; leadTimeDays: number}>;
    validUntil: string;
  };

  console.log(`\nSupplier quote from ${quote.supplier.name}:`);
  for (const item of quote.items) {
    const lineTotal = item.unitPrice * item.quantity;
    console.log(
      `  ${item.sku.padEnd(10)} qty=${String(item.quantity).padEnd(4)}  ` +
      `unit=$${item.unitPrice.toFixed(2)}  →  $${lineTotal.toFixed(2)}  ` +
      `(lead ${item.leadTimeDays}d)`,
    );
  }
  console.log(`\nQuote valid until: ${quote.validUntil}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
```

:::info Where's the TypeScript SDK?
A typed TS SDK with auto-generated types from the JSON Schemas is on the
[roadmap](/docs/roadmap). The wire format shown above is stable; code
written against it now will keep working once the SDK lands.
:::

</TabItem>
</Tabs>

## Typed data flowing through

The same `bom-v1` artifact reaches both the estimator and the supplier — that's the whole point. Neither agent has to guess at the input shape because both declared `inputSchema: "bom-v1"` in their Agent Cards.

The estimator returns an [`estimate-v1`](../schemas/estimate-v1), the supplier returns a [`quote-v1`](../schemas/quote-v1). The orchestrator can persist both as typed records linked to the project ID.

## Variations

- **Add a value-engineering pass.** Insert a `value-engineering` call between the estimate and the supplier hops. The VE agent reads the estimate, suggests substitutions, and returns a revised BOM.
- **Fan out to multiple suppliers.** Use the [BOM-to-Quote Marketplace](./bom-to-quote-marketplace) pattern to query several suppliers in parallel and select the best quote.
- **Cross-check against schedule.** See [Schedule-Aware Procurement](./schedule-aware-procurement) — reject quotes whose lead time exceeds the activity's planned start.
- **Streaming progress.** Replace `send_message` with `stream_message` and watch each agent's `TaskStatusUpdate` events as they work. Useful for long-running takeoffs.

## Common mistakes

**Sending the estimate (instead of the BOM) to the supplier.** The estimator's job is to *price* a BOM; the supplier's job is to *quote* a BOM. Both consume `bom-v1`. A common beginner mistake is to chain the supplier off the estimator's output as if it were a transformation pipeline — but suppliers want the unit/quantity information from the BOM, not the rolled-up cost from the estimate.

**Forwarding the orchestrator's full-scope token to the supplier.** The supplier only needs `taco:task:material-procurement taco:project:PRJ-0042:write`. Forwarding the orchestrator's broader token means a supplier compromise leaks more than it should. Use [Token Exchange](/docs/security) at every hop.

**Treating timeout as failure.** A 90-second supplier call is not necessarily broken; some pricing systems just take that long. Size each hop's `timeout` to the downstream's documented SLO, not to your patience.

**Discarding the BOM's `metadata.generatedBy`.** When the estimator hands the BOM forward to the supplier (or persists it for audit), preserve provenance. Future change-order disputes hinge on knowing which agent produced the source data.

**Hardcoding the agent URLs.** It works in dev. In prod, agents move hosts during routine deploys and your orchestrator silently sends requests into the void. Always route through `AgentRegistry.find(...)` so URL changes are caught at discovery time, not at request time. See [the lessons-from-production post](/blog/three-hop-chain-lessons).

## Debugging

**Inspect the BOM mid-chain.** Add a `print(json.dumps(bom, indent=2))` between the takeoff and the estimator call. The most common bug — wrong `csiDivision` or empty `lineItems` — is visible in five seconds.

**Use the Monitor UI on each agent.** `A2AServer(card, enable_monitor=True)` exposes `/monitor`. Watch a request flow through all three agents in real time. The visual is more useful than logs when debugging task lifecycle issues.

**Run the conformance runner against each agent.** [`/conformance`](/conformance) catches a surprising fraction of chain bugs at the source: an estimator that doesn't declare `inputSchema: "bom-v1"` won't be discoverable by `registry.find(input_schema="bom-v1")`, which means future orchestrators won't find it even though it works fine for yours.

**Tag every log line with the task ID and context ID.** Multi-agent chains produce logs in three places. The two correlation handles from A2A are `task.id` (per-request) and `task.context_id` (per-conversation). Tag every log line with both, plus the agent's name — tracing a problem across three agents becomes a single grep.

## See also

- [Core Concepts: Tasks, Messages, Artifacts](../core-concepts)
- [`bom-v1`](../schemas/bom-v1) · [`estimate-v1`](../schemas/estimate-v1) · [`quote-v1`](../schemas/quote-v1)
- [Agent-to-Agent Communication](../getting-started/multi-agent)
- [Best Practices](../best-practices)
- [Common Pitfalls](../pitfalls)
