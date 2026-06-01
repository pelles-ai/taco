---
title: "schedule-v1 — Project Schedule"
description: Project schedule schema — activities, dependencies, milestones, and resource assignments.
---

import SchemaExplorer from '@site/src/components/SchemaExplorer';

# schedule-v1 — Project Schedule

The Schedule schema defines a standardized format for construction project schedules, including activities, dependencies, milestones, and resource assignments.

Schedules are the typed output of schedule-coordination agents and a typed input to change-order analysis agents that need to reason about schedule impact.

<SchemaExplorer schemaId="schedule-v1" />

## Python SDK

```python
from taco import ScheduleV1

schedule = ScheduleV1.model_validate(json_data)
for activity in schedule.activities:
    print(activity.id, activity.duration_days, activity.dependencies)
output = schedule.model_dump(by_alias=True, exclude_none=True)
```

## See also

- [`change-order-v1`](./change-order-v1) — change orders frequently reference a schedule
- [Task types: `schedule-coordination`, `progress-tracking`](../task-types)
- [JSON Schema source](https://github.com/pelles-ai/taco/blob/main/spec/schemas/schedule-v1.json)
