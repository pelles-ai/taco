---
title: Schedule-Aware Procurement
description: Procurement that respects sequencing. Supplier lead times get cross-checked against the project schedule before any PO is committed.
sidebar_position: 5
---

import SequenceDiagram from '@site/src/components/SequenceDiagram';

# Schedule-Aware Procurement

The cheapest quote is the wrong quote if the materials arrive after the activity they're meant for. This recipe wires together a supplier agent, a scheduler agent, and a procurement coordinator that refuses to commit to any quote whose lead time pushes the receiving activity past its planned start date.

It's the cross-schema reasoning pattern that turns isolated quotes into a coherent purchasing decision.

## Goal

Make procurement decisions that respect the project schedule — automatically — so the project doesn't ship a PO that's already late on day one.

## Agents involved

| Agent | Role | Skills advertised |
|------|---------------------|---------------------|
| **Procurement Coordinator** | Orchestrator | (consumes `material-procurement` + `schedule-coordination`) |
| **PipeWorks Supply** | Supplier | `material-procurement` |
| **Project Scheduler** | Source-of-truth for schedule | `schedule-coordination` |

## Sequence

<SequenceDiagram
  actors={[
    {id: 'orch', label: 'Procurement', sub: 'Coordinator'},
    {id: 'sup', label: 'Supplier', sub: 'PipeWorks'},
    {id: 'sch', label: 'Scheduler', sub: 'baseline'},
  ]}
  messages={[
    {from: 'orch', to: 'sup', label: 'send_message(bom)', schema: 'bom-v1'},
    {from: 'sup', to: 'orch', label: 'returns quote', schema: 'quote-v1', kind: 'return'},
    {from: 'orch', to: 'sch', label: 'get schedule', schema: 'bom-v1'},
    {from: 'sch', to: 'orch', label: 'returns', schema: 'schedule-v1', kind: 'return'},
    {from: 'orch', to: 'orch', label: 'reconcile lead time vs activity start', note: 'reject items past activity start'},
  ]}
/>

## Full Python

```python
import asyncio
from datetime import datetime, timedelta
from taco import (
    AgentRegistry,
    TacoClient,
    extract_structured_data,
)

# Map BOM line items to the schedule activity that needs them.
# In a real workflow this mapping itself often comes from the takeoff
# agent or a value-engineering pass.
LINE_TO_ACTIVITY = {
    "L-001": "A-210",  # rough plumbing
    "L-002": "A-220",  # trim
}


async def fetch(agent, task_type, payload):
    async with TacoClient(agent_url=agent.url) as client:
        task = await client.send_message(task_type, payload)
    return extract_structured_data(task.artifacts[0].parts[0])


def days_until(activity_start_iso: str, *, today: datetime) -> int:
    start = datetime.fromisoformat(activity_start_iso.replace("Z", "+00:00"))
    return (start - today).days


def reconcile(quote: dict, schedule: dict, today: datetime) -> dict:
    """
    Walk the quote items, map each back to a schedule activity, and flag
    any whose lead time exceeds time-to-activity-start.
    Returns a structured decision payload.
    """
    activity_by_id = {a["id"]: a for a in schedule["activities"]}
    on_time, late = [], []
    for item in quote["items"]:
        activity_id = LINE_TO_ACTIVITY.get(item.get("sku") or item.get("lineItemId"))
        if not activity_id or activity_id not in activity_by_id:
            on_time.append({**item, "decision": "no-schedule-link"})
            continue
        activity = activity_by_id[activity_id]
        days_before_needed = days_until(activity["startDate"], today=today)
        slack = days_before_needed - item["leadTimeDays"]
        record = {
            **item,
            "activityId": activity_id,
            "activityStart": activity["startDate"],
            "slackDays": slack,
            "decision": "on-time" if slack >= 2 else "late",
        }
        (on_time if record["decision"] == "on-time" else late).append(record)
    return {"onTime": on_time, "late": late}


async def main() -> None:
    registry = AgentRegistry()
    for url in [
        "http://pipeworks.example.com:8002",
        "http://scheduler.example.com:8006",
    ]:
        await registry.register(url)

    supplier = registry.find(task_type="material-procurement")[0]
    scheduler = registry.find(task_type="schedule-coordination")[0]

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
        "metadata": {"generatedBy": "procurement-coordinator-v1",
                     "generatedAt": "2026-05-24T15:00:00Z"},
    }

    # Fetch quote + schedule in parallel
    quote, schedule = await asyncio.gather(
        fetch(supplier, "material-procurement", bom),
        fetch(scheduler, "schedule-coordination", {"projectId": bom["projectId"]}),
    )

    decision = reconcile(quote, schedule, today=datetime.utcnow())

    print(f"On time   ({len(decision['onTime'])} items):")
    for r in decision["onTime"]:
        print(f"  {r.get('sku', r.get('lineItemId')):<10}"
              f"  decision={r['decision']}")
    print(f"\nLate      ({len(decision['late'])} items):")
    for r in decision["late"]:
        print(f"  {r.get('sku'):<10}  activity={r['activityId']}  "
              f"lead={r['leadTimeDays']}d  slack={r['slackDays']}d")

    if decision["late"]:
        print("\nHold PO — escalate late items to expediter agent or"
              " request alternate suppliers.")
    else:
        print("\nAll items clear the schedule. Safe to commit PO.")


if __name__ == "__main__":
    asyncio.run(main())
```

## What "schedule-aware" actually buys you

Without the schedule cross-check, a procurement chain is one supplier away from accidentally ordering material that arrives after the activity it's meant for. With it, the decision is auditable: every line item carries `slackDays`, `activityId`, and the exact `decision` rule that produced its status. When the project manager asks "why didn't you order from the cheapest supplier?", the answer is in the typed record.

## Variations

- **Multi-supplier + schedule-aware.** Combine with [BOM-to-Quote Marketplace](./bom-to-quote-marketplace) — fan out, then pick the cheapest quote whose lead time clears the activity.
- **Re-plan instead of holding.** When items are late, push the activities out and re-emit the schedule via the scheduler agent (its `schedule-coordination` skill can also produce updated schedules).
- **Subscribe to slack.** Push the typed decision back as a notification when slack drops below a threshold during the project lifecycle.

## See also

- [`bom-v1`](../schemas/bom-v1) · [`quote-v1`](../schemas/quote-v1) · [`schedule-v1`](../schemas/schedule-v1)
- [Task types: `material-procurement`, `schedule-coordination`](../task-types)
- [Change Order Impact](./change-order-impact) — sibling cross-schema recipe
