---
title: RFI Round-trip
description: A drawing-audit agent flags a design conflict, generates an RFI, and routes it to a design-side agent that drafts a typed response.
sidebar_position: 2
---

import SequenceDiagram from '@site/src/components/SequenceDiagram';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# RFI Round-trip

The simplest two-agent document workflow. An audit agent on the construction side reads coordinated drawings and flags conflicts. Instead of writing a PDF to a portal, it emits a typed [`rfi-v1`](../schemas/rfi-v1) and sends it to a design-side agent that drafts a typed response.

End-to-end the round-trip is two messages and zero glue code.

## Goal

Turn a design-coordination conflict into a typed, machine-readable RFI and a typed response — so both sides can analyze it, route it, escalate it, or feed it into the next phase of the project automatically.

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
    {from: 'designer', to: 'auditor', label: 'returns response', schema: 'rfi-response-v1', note: 'schema planned', kind: 'return'},
  ]}
/>

## Full code

The `rfi-response` task type returns `rfi-response-v1`, which is a planned schema: there is no published definition yet. The code below sends a fully typed `rfi-v1` and prints whatever structured data comes back, rather than assuming response field names.

<Tabs groupId="lang">
<TabItem value="python" label="Python (taco-agent)" default>

```python
import asyncio
import json
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

    # rfi-response-v1 is planned, so its field names aren't defined yet.
    # Treat the artifact as opaque structured data until the schema lands.
    response = extract_structured_data(task.artifacts[0].parts[0])
    print(f"RFI {rfi['subject']} → response (task {task.id}):")
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
```

</TabItem>
<TabItem value="ts" label="TypeScript (wire format, no SDK)">

```typescript
// Plain fetch — TACO's wire format is JSON-RPC over HTTP.
// See the GC chain recipe for the shared helpers (sendMessage, discoverAgent).

async function sendMessage(agentUrl: string, taskType: string, payload: unknown) {
  const res = await fetch(agentUrl.replace(/\/$/, '') + '/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'A2A-Version': '0.3'},
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: crypto.randomUUID(),
      method: 'message/send',
      params: {
        message: {
          kind: 'message',
          messageId: crypto.randomUUID(),
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
  return result;
}

async function main() {
  const responderUrl = 'http://design-responder.example.com:8003';

  const rfi = {
    projectId: 'PRJ-2026-OAKRIDGE-MEDICAL',
    subject: 'Pipe routing conflict at column line C/4',
    question:
      'Detail M-201 shows a 4" hot water supply routed through the structural beam at column line C/4. ' +
      'S-201 shows the beam as continuous with no penetration. Please clarify the intended routing or ' +
      'confirm a beam penetration is acceptable.',
    category: 'design-conflict',
    priority: 'high',
    references: [
      {sheetId: 'M-201', area: 'grid C4'},
      {sheetId: 'S-201', area: 'grid C4'},
    ],
    metadata: {
      generatedBy: 'drawing-auditor-ts-v1',
      generatedAt: new Date().toISOString(),
    },
  };

  const task = await sendMessage(responderUrl, 'rfi-response', rfi);
  // rfi-response-v1 is planned, so its field names aren't defined yet.
  // Treat the artifact as opaque structured data until the schema lands.
  const response: unknown = task.artifacts[0].parts[0].data;

  console.log(`RFI "${rfi.subject}" → response (task ${task.id}):`);
  console.log(JSON.stringify(response, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
```

</TabItem>
</Tabs>

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
- **Persist + track.** Store the responder's task ID in your project record, and pass it as [`reference_task_ids`](/docs/sdk-reference/client) on any follow-up message so the round-trip is auditable.
- **Streaming.** If the responder registers a streaming handler for `rfi-response`, use `stream_message` to surface partial responses in a chat-style UI while the designer agent is still composing.
- **Add a triage agent.** Insert a third agent between auditor and responder that classifies, deduplicates, or prioritizes incoming RFIs before they hit the design team.

## Common mistakes

**Routing every RFI to the same responder.** Construction RFIs split cleanly by `category` (`design-conflict` → architect/engineer; `code-compliance` → AHJ liaison; `clarification` → spec writer). A single "design responder" agent handling all of them ends up being a bottleneck and producing low-quality responses for categories outside its expertise. Filter on `category` before dispatching.

**Treating priority as decorative.** `priority: "critical"` should trigger a different routing path than `priority: "low"` — escalation, SLA timers, owner notification. If your responder treats all RFIs identically, the typed priority field is doing nothing for you.

**Putting actual base64 image data in `references.markup`.** Inline base64 markup balloons RFI payloads to megabytes; this kills task queues and breaks audit logs. Use a file reference (URL or content-addressed hash) instead, and let the responder agent fetch the markup separately when it needs to.

**Failing the task when the responder needs more info.** If the design responder can't answer without further clarification, returning `state: "failed"` is wrong — that's a *clarification request*, not a system failure. Complete the task and return the follow-up question as data in the artifact. The `rfi-response-v1` shape is still planned, so agree on the clarification fields with the other side for now. A2A also defines an `input-required` task state for this case, but TACO SDK handlers currently finish every task as `completed` or `failed`. See [Best Practices on error handling](../best-practices#error-handling).

## Debugging

**Log the RFI's references before sending.** Drawing-sheet IDs are the most error-prone field — a typo (`M-201` vs `M-021`) makes the RFI unanswerable. A pre-send validation that the sheet IDs match a known drawing list catches this at the source.

**Use `reference_task_ids` to link follow-ups back to the original.** Keep the RFI task's `task.id`. When the auditor sends a follow-up (a clarification answer, a revised RFI), pass `reference_task_ids=[original_rfi_task_id]` to `send_message` so the new task points back to the original. The registry indexes agents, not tasks, so "all responses to this RFI" is a lookup in your own project record keyed by those task IDs.

**Subscribe via push notification for slow responses.** If responder turnaround is hours-long, don't block — use the [push notification config](../sdk-reference/push-notifications) API so the responder calls back when ready instead of the orchestrator polling.

## See also

- [`rfi-v1`](../schemas/rfi-v1)
- [Task types: `rfi-generation`, `rfi-response`](../task-types)
- [Agent-to-Agent Communication](../getting-started/multi-agent)
- [Best Practices](../best-practices)
- [Common Pitfalls](../pitfalls)
