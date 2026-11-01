---
title: "schedule-v1 — Project Schedule"
description: Project schedule schema — activities, dependencies, milestones, and resource assignments.
---

import SchemaExplorer, {SchemaExample} from '@site/src/components/SchemaExplorer';

# schedule-v1 — Project Schedule

The Schedule schema defines a standardized format for construction project schedules, including activities, dependencies, milestones, and resource assignments.

**JSON Schema:** [`spec/schemas/schedule-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/schedule-v1.json)

**Status:** Defined.

## Fields

Generated from [`spec/schemas/schedule-v1.json`](https://github.com/pelles-ai/taco/blob/main/spec/schemas/schedule-v1.json). Open a field to see what it holds, or switch to **Validate** to check a payload of your own.

<SchemaExplorer schemaId="schedule-v1" />

## Validation Rules

- Activities list must contain at least one activity
- Activity IDs must be unique within the schedule (duplicates raise a validation error)
- Activity and milestone `id` fields must be non-empty
- Milestone `name` must be non-empty
- `durationDays` must be >= 0
- `percentComplete` must be between 0 and 100

## Example

<SchemaExample schemaId="schedule-v1" />

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
