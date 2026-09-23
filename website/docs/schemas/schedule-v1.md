---
title: "schedule-v1 — Project Schedule"
description: Project schedule schema — activities, dependencies, milestones, and resource assignments.
---

# schedule-v1 — Project Schedule

The Schedule schema defines a standardized format for construction project schedules, including activities, dependencies, milestones, and resource assignments.

**JSON Schema:** [`spec/schemas/schedule-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/schedule-v1.json)

**Status:** Defined.

## Structure

### ScheduleV1 (top-level)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `projectId` | string | Yes | Project identifier |
| `startDate` | string | No | Project start date |
| `endDate` | string | No | Project end date |
| `activities` | ScheduleActivity[] | Yes (min 1) | List of scheduled activities (unique IDs required) |
| `milestones` | ScheduleMilestone[] | No | List of project milestones |
| `metadata` | ScheduleMetadata | Yes | Generation metadata |

### ScheduleActivity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string (min 1) | Yes | Unique activity identifier |
| `name` | string | Yes | Activity name |
| `trade` | Trade | No | Associated trade |
| `durationDays` | integer (>= 0) | Yes | Duration in days |
| `startDate` | string | No | Activity start date |
| `endDate` | string | No | Activity end date |
| `predecessors` | string[] | No | IDs of predecessor activities |
| `successors` | string[] | No | IDs of successor activities |
| `percentComplete` | float (0-100) | No | Completion percentage (default 0) |
| `isCritical` | boolean | No | Whether activity is on the critical path (default false) |
| `resources` | string[] | No | Assigned resources |

### ScheduleMilestone

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string (min 1) | Yes | Unique milestone identifier |
| `name` | string (min 1) | Yes | Milestone name |
| `date` | string | Yes | Milestone date |
| `isMet` | boolean | No | Whether milestone has been achieved (default false) |

### ScheduleMetadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `generatedBy` | string | Yes | System or agent that generated the schedule |
| `generatedAt` | string | Yes | ISO-8601 timestamp |
| `confidence` | float (0-1) | No | Confidence score |
| `notes` | string[] | No | Additional notes |

## Validation Rules

- Activities list must contain at least one activity
- Activity IDs must be unique within the schedule (duplicates raise a validation error)
- Activity and milestone `id` fields must be non-empty
- Milestone `name` must be non-empty
- `durationDays` must be >= 0
- `percentComplete` must be between 0 and 100

## Example

```json
{
  "projectId": "PRJ-2026-OAKRIDGE",
  "startDate": "2026-03-01",
  "endDate": "2026-09-30",
  "activities": [
    {
      "id": "ACT-001",
      "name": "Foundation pour",
      "trade": "structural",
      "durationDays": 5,
      "startDate": "2026-03-01",
      "endDate": "2026-03-06",
      "successors": ["ACT-002"],
      "percentComplete": 100.0,
      "isCritical": true,
      "resources": ["Crew A", "Concrete pump"]
    },
    {
      "id": "ACT-002",
      "name": "Framing",
      "trade": "structural",
      "durationDays": 15,
      "startDate": "2026-03-07",
      "predecessors": ["ACT-001"],
      "percentComplete": 0.0
    }
  ],
  "milestones": [
    {
      "id": "MS-001",
      "name": "Foundation complete",
      "date": "2026-03-06",
      "isMet": true
    }
  ],
  "metadata": {
    "generatedBy": "schedule-agent",
    "generatedAt": "2026-02-28T10:00:00Z",
    "confidence": 0.9
  }
}
```

## Python SDK

```python
from taco import ScheduleV1, ScheduleActivity, ScheduleMilestone, ScheduleMetadata

sched = ScheduleV1(
    project_id="PRJ-001",
    start_date="2026-03-01",
    activities=[
        ScheduleActivity(
            id="ACT-001",
            name="Foundation pour",
            trade="structural",
            duration_days=5,
            is_critical=True,
        ),
    ],
    milestones=[
        ScheduleMilestone(
            id="MS-001",
            name="Foundation complete",
            date="2026-03-06",
        ),
    ],
    metadata=ScheduleMetadata(
        generated_by="scheduler",
        generated_at="2026-02-28T10:00:00Z",
        confidence=0.9,
    ),
)
```
