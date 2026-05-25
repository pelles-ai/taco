---
title: Change Order Impact
description: When scope shifts mid-project, a change-order agent reads the current estimate AND schedule together and emits a typed delta covering cost and timeline.
sidebar_position: 4
---

import SequenceDiagram from '@site/src/components/SequenceDiagram';

# Change Order Impact

Change is the only constant on a job site. This recipe shows how a change-order agent reasons about *both* cost and schedule impact by reading two typed artifacts in parallel — the current [`estimate-v1`](../schemas/estimate-v1) and [`schedule-v1`](../schemas/schedule-v1) — and emits a [`change-order-v1`](../schemas/change-order-v1) that downstream approvers, owners, and accounting systems can act on.

## Goal

Turn a scope change request into a typed, defensible delta showing dollar impact, calendar impact, and the activities/line-items affected — all derived from authoritative current-state agents.

## Agents involved

| Agent | Role | Skills advertised |
|------|---------------------|---------------------|
| **Change Order Analyzer** | Orchestrator | `change-order-analysis` |
| **Project Estimator** | Source-of-truth for cost | `estimate` |
| **Project Scheduler** | Source-of-truth for schedule | `schedule-coordination` |

The Change Order Analyzer doesn't store anything itself. It pulls fresh state from the estimator and scheduler at request time — that's why the result is always defensible against the *current* baseline.

## Sequence

<SequenceDiagram
  actors={[
    {id: 'coa', label: 'Change Order', sub: 'Analyzer'},
    {id: 'est', label: 'Estimator', sub: 'baseline cost'},
    {id: 'sch', label: 'Scheduler', sub: 'baseline schedule'},
  ]}
  messages={[
    {from: 'coa', to: 'est', label: 'get current estimate', schema: 'bom-v1'},
    {from: 'est', to: 'coa', label: 'returns', schema: 'estimate-v1', kind: 'return'},
    {from: 'coa', to: 'sch', label: 'get current schedule', schema: 'bom-v1'},
    {from: 'sch', to: 'coa', label: 'returns', schema: 'schedule-v1', kind: 'return'},
    {from: 'coa', to: 'coa', label: 'compute delta (local)', schema: 'change-order-v1'},
  ]}
/>

The two upstream calls fan out in parallel; the analyzer joins them before computing the delta.

## Full Python

```python
import asyncio
from taco import (
    AgentRegistry,
    TacoClient,
    extract_structured_data,
)


async def fetch_artifact(agent, task_type, payload):
    async with TacoClient(agent_url=agent.url) as client:
        task = await client.send_message(task_type, payload)
    return extract_structured_data(task.artifacts[0].parts[0])


def compute_change_order(
    project_id: str,
    change_description: str,
    baseline_estimate: dict,
    baseline_schedule: dict,
    new_bom: dict,
    delta_days_per_activity: dict[str, int],
) -> dict:
    """
    Build a change-order-v1 from the baseline + the proposed change.
    Pricing the new BOM is delegated to the same estimator that produced
    the baseline (not shown — replace with a second `send_message`).
    """
    baseline_total = baseline_estimate["summary"]["total"]
    # Toy pricing for the delta — in practice ask the estimator agent.
    delta_cost = sum(li["quantity"] * 14.50 for li in new_bom["lineItems"])
    delta_days = max(delta_days_per_activity.values(), default=0)
    affected_activities = list(delta_days_per_activity.keys())

    return {
        "projectId": project_id,
        "changeOrderId": "CO-007",
        "description": change_description,
        "costImpact": {
            "amount": round(delta_cost, 2),
            "currency": baseline_estimate.get("currency", "USD"),
            "baselineTotal": baseline_total,
            "newTotal": round(baseline_total + delta_cost, 2),
        },
        "scheduleImpact": {
            "deltaDays": delta_days,
            "affectedActivities": affected_activities,
        },
        "metadata": {
            "generatedBy": "change-order-analyzer-v1",
            "generatedAt": "2026-05-24T15:30:00Z",
            "baselineSources": {
                "estimate": baseline_estimate["metadata"].get("generatedBy"),
                "schedule": baseline_schedule["metadata"].get("generatedBy"),
            },
        },
    }


async def main() -> None:
    registry = AgentRegistry()
    for url in [
        "http://estimator.example.com:8001",
        "http://scheduler.example.com:8006",
    ]:
        await registry.register(url)

    estimator = registry.find(task_type="estimate")[0]
    scheduler = registry.find(task_type="schedule-coordination")[0]

    project = {"projectId": "PRJ-2026-OAKRIDGE-MEDICAL"}

    # 1. Pull current baselines in parallel
    baseline_estimate, baseline_schedule = await asyncio.gather(
        fetch_artifact(estimator, "estimate", project),
        fetch_artifact(scheduler, "schedule-coordination", project),
    )

    # 2. The proposed scope change — adding HVAC zoning on level 3
    new_bom = {
        "projectId": project["projectId"],
        "trade": "mechanical",
        "csiDivision": "23",
        "lineItems": [
            {"id": "L-301", "description": "VAV box, 800 cfm",
             "quantity": 6, "unit": "EA"},
            {"id": "L-302", "description": "Insulated ductwork, supply",
             "quantity": 240, "unit": "LF"},
        ],
        "metadata": {"generatedBy": "scope-change-request",
                     "generatedAt": "2026-05-24T15:00:00Z"},
    }
    delta_days_per_activity = {
        "A-310": 4,  # rough-in install
        "A-320": 2,  # commissioning
    }

    # 3. Compute the typed delta
    co = compute_change_order(
        project_id=project["projectId"],
        change_description="Add HVAC zoning for level 3 east wing",
        baseline_estimate=baseline_estimate,
        baseline_schedule=baseline_schedule,
        new_bom=new_bom,
        delta_days_per_activity=delta_days_per_activity,
    )

    print(f"Change Order {co['changeOrderId']}: {co['description']}")
    print(f"  Cost:   ${co['costImpact']['amount']:>10,.2f} "
          f"(new total ${co['costImpact']['newTotal']:,.2f})")
    print(f"  Schedule: +{co['scheduleImpact']['deltaDays']}d across "
          f"{len(co['scheduleImpact']['affectedActivities'])} activities")
    print(f"  Baselines: {co['metadata']['baselineSources']}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Why pull baselines instead of caching them

A change order is binding. If the analyzer used a stale snapshot of the estimate or schedule, the delta could be off by whatever's accumulated since — accepted RFI updates, prior change orders, value-engineering substitutions. Treating the estimator and scheduler as authoritative agents (read live, every time) is what makes `change-order-v1.metadata.baselineSources` defensible later.

## Variations

- **Two-phase: propose → commit.** First call returns a draft change order with `status: "proposed"`. After human approval, a second call mutates the baseline estimate and schedule.
- **Multi-trade.** Iterate the orchestration across `mechanical`, `electrical`, `structural` estimators and sum the cost impact.
- **Substitution analysis.** Add a value-engineering hop before the analyzer — the VE agent proposes alternates that reduce cost impact.
- **Notify downstream.** Once the CO is computed, push it to subscribing agents via the [push notifications](/docs/sdk) channel.

## Common mistakes

**Caching the baseline estimate or schedule.** A change order is a binding artifact. If the analyzer computed the delta against a six-hour-old snapshot, accepted RFIs and prior change orders since then are not reflected — and the project manager's spreadsheet won't match your typed delta. **Always pull live baselines.** The cost of two extra agent calls is dwarfed by the cost of one disputed change order.

**Computing cost without a real pricing call.** The example uses toy pricing (`* 14.50`) for brevity. In production, the cost delta should come from the same estimator agent that produced the baseline — call it again with the proposed scope as a `bom-v1` and use its returned `estimate-v1` for the delta math. This way the change order inherits the estimator's actual pricing model, including labor rates and material markups.

**Forgetting to record `baselineSources`.** `change-order-v1.metadata.baselineSources` is what makes the delta defensible later. Without it, when someone in 2028 asks "what schedule version did this change order target?", the answer is a shrug.

**Setting `status: "approved"` directly from the analyzer.** Change orders need human approval. The analyzer should emit `status: "proposed"`; an approval workflow (often human-in-the-loop) flips it to `status: "approved"` with a signature. Skipping this skips the contract law.

**Mixing trades in one CO without distinguishing.** A change order that adds HVAC zoning AND moves an electrical panel needs per-trade cost rolls. Track impact by trade so the GC can chase the right sub for each scope item.

## Debugging

**Run the analyzer twice and diff.** If the baseline estimate is volatile (it shouldn't be, but reality), running the analyzer twice and diffing the outputs catches non-deterministic pricing. The delta should be identical for identical inputs; if it isn't, you have a downstream determinism bug.

**Log `baselineSources` agent names + their `generatedAt`.** When a stakeholder challenges the CO, the trail of "which agent, at what time" makes triage instant. Without it you're guessing.

**Make the analyzer's task type `change-order-analysis` (not just `estimate`).** A common mistake is reusing the estimator for change orders. They produce different artifacts (`estimate-v1` vs `change-order-v1`) and have different audit requirements. Separate agents, separate skills.

## See also

- [`estimate-v1`](../schemas/estimate-v1) · [`schedule-v1`](../schemas/schedule-v1) · [`change-order-v1`](../schemas/change-order-v1)
- [Task type: `change-order-analysis`](../task-types)
- [Best Practices](../best-practices)
- [Common Pitfalls](../pitfalls)
