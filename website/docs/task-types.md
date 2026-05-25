---
sidebar_position: 2
title: Task Types
description: The verbs of the TACO ecosystem — takeoff, estimate, rfi-generation, schedule-coordination, and 14 more construction workflows agents can advertise.
---

import TaskTypeBrowser from '@site/src/components/TaskTypeBrowser';

# Task Types

Task types are the **verbs** of the TACO ecosystem. Each one defines a category of work that an agent can advertise and execute. Agents declare their supported task types in the `taskType` field of their Agent Card skills.

:::info Schema status
Six output schemas are fully defined and ship with the SDK: `bom-v1`, `rfi-v1`, `estimate-v1`, `quote-v1`, `schedule-v1`, `change-order-v1`. The remaining outputs listed below are **planned** — the task type is recognized, but the canonical output schema is not yet authored. [Contributions welcome.](https://github.com/pelles-ai/taco/issues)
:::

## Browse all 18 task types

<TaskTypeBrowser />

## Adding new task types

New task types can be proposed via [GitHub issue](https://github.com/pelles-ai/taco/issues). A proposal should include:

1. Task type name (kebab-case)
2. Description
3. Project phase (preconstruction, document management, field/coordination)
4. Expected input and output schema references
5. At least one real-world use case

Each accepted task type lands here, in the matrix above, and (when its output schema is also ready) in the [schema explorer](/docs/schemas/).
