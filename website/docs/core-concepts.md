---
sidebar_position: 2
title: Core Concepts
description: The key abstractions in TACO — Agent Cards, Skills, Tasks, Messages, Parts, and Artifacts — and how they fit together.
---

# Core Concepts

This page explains the key abstractions in TACO and how they fit together. Understanding these concepts makes the rest of the documentation easier to follow.

:::tip Visual deep dive
For an interactive walkthrough of the protocol layers, agent interactions, and data flow, see the [Architecture Overview diagram](pathname:///taco-architecture-overview.html).
:::

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Card                               │
│  Who am I? What can I do? What trade do I serve?                │
│  Served at /.well-known/agent.json                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ advertises
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                         Skills                                   │
│  Each skill has a task_type, input_schema, and output_schema     │
└──────────────────────────┬───────────────────────────────────────┘
                           │ handles
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                          Task                                    │
│  A unit of work: submitted → working → completed/failed          │
│  Contains Messages (inbound) and Artifacts (outbound)            │
└──────────────────────────┬───────────────────────────────────────┘
                           │ produces
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Artifact                                  │
│  The result of a task — contains one or more Parts               │
│  Parts can be text (TextPart), structured data (DataPart),       │
│  or files (FilePart)                                             │
└──────────────────────────────────────────────────────────────────┘
```

## Agent Card

An **Agent Card** is a JSON document that describes an agent's identity and capabilities. It's served at `/.well-known/agent.json` and is how other agents (and humans) discover what your agent can do.

```json
{
  "name": "My Mechanical Estimating Agent",
  "description": "Generates cost estimates from BOMs",
  "url": "http://localhost:8001",
  "version": "1.0.0",
  "skills": [...],
  "x-construction": {
    "trade": "mechanical",
    "csiDivisions": ["22", "23"]
  }
}
```

The `x-construction` extension is what makes a TACO agent different from a plain A2A agent — it adds construction-specific metadata like trade, CSI divisions, project types, and integrations.

In Python, you build an Agent Card using `ConstructionAgentCard`:

```python
from taco import ConstructionAgentCard, ConstructionSkill

card = ConstructionAgentCard(
    name="My Mechanical Estimating Agent",
    trade="mechanical",
    csi_divisions=["22", "23"],
    skills=[...],
)

# Convert to the standard A2A AgentCard (with x-construction populated)
a2a_card = card.to_a2a()
```

See [Agent Card Extensions](/docs/agent-card-extensions) for all available fields.

## Skills

A **Skill** describes one thing your agent can do. Each skill has:

| Field | Purpose | Example |
|-------|---------|---------|
| `id` | Unique identifier | `"generate-estimate"` |
| `task_type` | The TACO task type this skill handles | `"estimate"` |
| `input_schema` | Expected input data format (optional) | `"bom-v1"` |
| `output_schema` | Output data format | `"estimate-v1"` |

```python
ConstructionSkill(
    id="generate-estimate",
    task_type="estimate",
    input_schema="bom-v1",
    output_schema="estimate-v1",
)
```

An agent can have multiple skills. Other agents use the skill list to decide which agent to call for a given task type.

See [Task Types](/docs/task-types) for the full vocabulary and [Data Schemas](/docs/schemas/) for the typed schemas.

## Tasks

A **Task** is a unit of work. When a client sends a message to an agent, the server creates a task to track it.

### Task lifecycle

```
submitted → working → completed
                    → failed
                    → canceled
```

| State | Meaning |
|-------|---------|
| `submitted` | Task received, not yet started |
| `working` | Handler is processing the task |
| `completed` | Handler finished successfully — artifacts are available |
| `failed` | Handler threw an exception or returned an error |
| `canceled` | Task was canceled by the client |

You don't manage task states directly — the server handles transitions automatically. Your handler just returns an `Artifact` (success) or raises an exception (failure).

### Task structure

```python
Task(
    id="task-abc-123",
    context_id="ctx-456",
    status=TaskStatus(state=TaskState.completed),
    artifacts=[...],      # Results from the handler
    metadata={"taskType": "estimate"},
)
```

The `context_id` groups related tasks into a conversation. If you send multiple messages with the same `context_id`, they share context (useful for multi-turn interactions).

## Messages and Parts

A **Message** is the envelope for communication. It has a `role` (who sent it) and a list of `parts` (the content).

| Role | Who sends it |
|------|-------------|
| `user` | The caller (human or another agent) |
| `agent` | The agent responding |

**Parts** are the content units inside a message. There are three types:

| Part type | `kind` field | Content | When to use |
|-----------|-------------|---------|-------------|
| `TextPart` | `"text"` | Plain text | Human-readable messages, status updates |
| `DataPart` | `"data"` | JSON object | Structured data (BOMs, estimates, queries) |
| `FilePart` | `"file"` | File reference | Documents, drawings, attachments |

In a JSON-RPC request, parts look like this:

```json
{
  "parts": [
    {"kind": "text", "text": "Generate an estimate for this BOM"},
    {"kind": "data", "data": {"projectId": "PRJ-001", "lineItems": [...]}}
  ]
}
```

In Python, use the helper functions:

```python
from taco import make_text_part, make_data_part

text_part = make_text_part("Processing your request...")
data_part = make_data_part({"projectId": "PRJ-001", "lineItems": [...]})
```

## Artifacts

An **Artifact** is the result of a completed task. It contains one or more Parts (usually a `DataPart` with structured output).

```python
from taco import make_artifact, make_data_part

artifact = make_artifact(
    parts=[make_data_part({"total": 45000, "currency": "USD"})],
    name="cost-estimate",
    description="Mechanical cost estimate for PRJ-001",
)
```

To extract data from an artifact you received:

```python
from taco import extract_structured_data

# After receiving a task response
data = extract_structured_data(task.artifacts[0].parts[0])
# data = {"total": 45000, "currency": "USD"}
```

## How it all fits together

Here's the complete flow when one agent calls another:

```
Caller                                    Agent
  │                                         │
  │  1. GET /.well-known/agent.json         │
  │────────────────────────────────────────▶│
  │◀────────────────────────────────────────│
  │     Agent Card (skills, trade, etc.)    │
  │                                         │
  │  2. POST / (JSON-RPC message/send)      │
  │     Message with DataPart               │
  │     metadata: {taskType: "estimate"}    │
  │────────────────────────────────────────▶│
  │                                         │  3. Server creates Task
  │                                         │     (submitted → working)
  │                                         │
  │                                         │  4. Handler runs
  │                                         │     handler(task, input_data)
  │                                         │     → returns Artifact
  │                                         │
  │                                         │  5. Task → completed
  │◀────────────────────────────────────────│
  │     Task (with Artifact containing      │
  │     the result as a DataPart)           │
  │                                         │
```

1. **Discovery** — Caller fetches the Agent Card to learn what the agent can do
2. **Request** — Caller sends a JSON-RPC `message/send` with input data and a `taskType`
3. **Task creation** — Server creates a Task and transitions it to `working`
4. **Handler** — Your handler processes the input and returns an Artifact
5. **Response** — Server transitions the task to `completed` and returns it with the Artifact

For streaming responses, use `message/stream` instead of `message/send` — the server sends incremental SSE events as the handler yields Parts.

## Python SDK classes

| Class | Role | When to use |
|-------|------|-------------|
| `ConstructionAgentCard` | Defines your agent's identity | Always — every agent needs one |
| `ConstructionSkill` | Defines one capability | Always — each skill maps to a handler |
| `A2AServer` | Receives tasks, routes to handlers | When your agent only receives tasks |
| `TacoAgent` | Receives and sends tasks | When your agent also calls other agents |
| `TacoClient` | Calls another agent | When you need direct agent-to-agent calls |
| `AgentRegistry` | Discovers and filters agents | When you need to find agents by trade/skill |

See the [SDK Reference](/docs/sdk) for full API details.
