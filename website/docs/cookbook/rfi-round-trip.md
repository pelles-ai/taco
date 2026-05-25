---
title: RFI Round-trip
description: A drawing-audit agent flags a design conflict, generates an RFI, and routes it to a design-side agent that drafts a typed response.
sidebar_position: 2
---

import SequenceDiagram from '@site/src/components/SequenceDiagram';

# RFI Round-trip

The simplest two-agent document workflow. An audit agent on the construction side reads coordinated drawings and flags conflicts. Instead of writing a PDF to a portal, it emits a typed [`rfi-v1`](../schemas/rfi-v1) and sends it to a design-side agent that drafts a typed response.

End-to-end the round-trip is two messages and zero glue code.

## Goal

Turn a design-coordination conflict into a typed, machine-readable RFI and a typed response — so both sides can analytics it, route it, escalate it, or feed it into the next phase of the project automatically.

## Agents involved

| Agent | Trade | Skills advertised |
|------|-------|---------------------|
| **Drawing Auditor** | `multi-trade` | `rfi-generation` |
| **Design Responder** | `architectural` | `rfi-response` |

## Sequence

<SequenceDiagram
  actors={[
    {id: 'auditor', label: 'Drawing Auditor', sub: 'multi-trade'},
    {id: 'designer', label: 'Design Responder', sub: 'architectural'},
  ]}
  messages={[
    {from: 'auditor', to: 'auditor', label: 'audit drawings (local)', note: 'detect conflict at C/4'},
    {from: 'auditor', to: 'designer', label: 'send_message("rfi-response", rfi)', schema: 'rfi-v1'},
    {from: 'designer', to: 'auditor', label: 'returns response', schema: 'rfi-response-v1', kind: 'return'},
  ]}
/>

## Full Python

```python
import asyncio
from taco import (
    AgentRegistry,
    TacoClient,
    extract_structured_data,
)

async def main() -> None:
    registry = AgentRegistry()
    await registry.register("http://design-responder.example.com:8003")
    responder = registry.find(task_type="rfi-response")[0]

    # An audit agent has detected a conflict — build the typed RFI
    rfi = {
        "projectId": "PRJ-2026-OAKRIDGE-MEDICAL",
        "subject": "Pipe routing conflict at column line C/4",
        "question": (
            "Detail M-201 shows a 4\" hot water supply routed through the "
            "structural beam at column line C/4. S-201 shows the beam as "
            "continuous with no penetration. Please clarify the intended "
            "routing or confirm a beam penetration is acceptable."
        ),
        "category": "design-conflict",
        "priority": "high",
        "references": [
            {"sheetId": "M-201", "area": "grid C4"},
            {"sheetId": "S-201", "area": "grid C4"},
        ],
        "metadata": {
            "generatedBy": "drawing-auditor-v1",
            "generatedAt": "2026-05-24T15:00:00Z",
        },
    }

    async with TacoClient(agent_url=responder.url) as client:
        task = await client.send_message("rfi-response", rfi)

    response = extract_structured_data(task.artifacts[0].parts[0])
    print(f"RFI {rfi['subject']} → response:")
    print(response.get("response", "(no response text)"))
    print(f"\nResponder: {response.get('respondedBy')}")
    print(f"Status: {response.get('status')}")


if __name__ == "__main__":
    asyncio.run(main())
```

## What the typed RFI looks like

```json
{
  "projectId": "PRJ-2026-OAKRIDGE-MEDICAL",
  "subject": "Pipe routing conflict at column line C/4",
  "question": "Detail M-201 shows ...",
  "category": "design-conflict",
  "priority": "high",
  "references": [
    {"sheetId": "M-201", "area": "grid C4"},
    {"sheetId": "S-201", "area": "grid C4"}
  ],
  "metadata": {
    "generatedBy": "drawing-auditor-v1",
    "generatedAt": "2026-05-24T15:00:00Z"
  }
}
```

The `category` and `priority` enums are part of [`rfi-v1`](../schemas/rfi-v1) — they let downstream routing logic (escalation rules, SLAs, dashboards) work the same way against any TACO-compatible auditor, not just yours.

## Variations

- **Route by category.** Use `registry.find(task_type="rfi-response")` to discover multiple responders, then dispatch by `category` (structural conflicts → structural engineer agent, code-compliance → code reviewer agent).
- **Persist + track.** Wire the responder's task ID back into your project record with [`reference_task_ids`](/docs/sdk) so the round-trip is auditable.
- **Streaming.** Use `stream_message` to surface partial responses in a chat-style UI while the designer agent is still composing.
- **Add a triage agent.** Insert a third agent between auditor and responder that classifies, deduplicates, or prioritizes incoming RFIs before they hit the design team.

## See also

- [`rfi-v1`](../schemas/rfi-v1)
- [Task types: `rfi-generation`, `rfi-response`](../task-types)
- [Agent-to-Agent Communication](../getting-started/multi-agent)
