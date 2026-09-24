---
sidebar_position: 2
title: Task Types
description: The verbs of the TACO ecosystem — takeoff, estimate, rfi-generation, schedule-coordination, and 14 more construction workflows agents can advertise.
---

import TaskTypeBrowser from '@site/src/components/TaskTypeBrowser';

# Task Types

Task types are the verbs of the TACO ecosystem. Each task type defines a category of work that an agent can advertise and execute. Agents declare their supported task types in the `x-construction.taskType` field of their Agent Card skills.

:::info Schema Status
Fully defined schemas: `bom-v1`, `rfi-v1`, `estimate-v1`, `quote-v1`, `schedule-v1`, and `change-order-v1`. All other output schemas listed below are planned but do not yet have schema files. Contributions welcome.
:::

## All task types

This list is generated from [`spec/task-types.md`](https://github.com/pelles-ai/taco/blob/main/spec/task-types.md). Filter by phase, or by whether the output schema is defined yet.

<TaskTypeBrowser />

## Adding New Task Types

New task types can be proposed via [GitHub issue](https://github.com/pelles-ai/taco/issues). A proposal should include:

1. Task type name (kebab-case)
2. Description
3. Project phase (preconstruction, document management, field/coordination)
4. Expected input and output schema references
5. At least one real-world use case
