---
title: SDK Reference
description: Per-symbol reference for the TACO Python SDK — auto-generated from source.
sidebar_position: 0
---

:::info Generated
These pages are auto-generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
:::

# SDK Reference

Every public class, function, and constant in `taco-agent`, introspected directly from the source. For high-level usage examples, see the [SDK Guide](../sdk) and the [Cookbook](../cookbook).

## Groups

| Group | Symbols |
|------|--------|
| [Agent Cards](./agent-cards) | `ConstructionAgentCard`, `ConstructionSkill`, `AgentCard` + 10 more |
| [Server](./server) | `A2AServer`, `TacoTaskError`, `enable_monitor` |
| [Auth](./auth) | `AuthContext`, `TokenVerifier`, `current_auth` + 1 more |
| [Client](./client) | `TacoClient`, `TacoClientError`, `RpcError` + 1 more |
| [Agent (server + client pool)](./agent) | `TacoAgent` |
| [Registry](./registry) | `AgentRegistry` |
| [Tasks & Messages](./tasks-and-messages) | `Task`, `TaskStatus`, `TaskState` + 7 more |
| [Helpers](./helpers) | `make_message`, `make_text_part`, `make_data_part` + 12 more |
| [Persistence](./persistence) | `TaskStore`, `JsonFileTaskStore` |
| [Push Notifications](./push-notifications) | `PushNotificationConfig`, `PushNotificationAuthenticationInfo`, `TaskPushNotificationConfig` |
| [Schema lookup](./schemas) | `get_schema_model`, `SCHEMA_MODELS` |
| [Enums](./enums) | `Trade`, `ProjectType`, `Integration` + 6 more |

## Schema models

Schema models have dedicated interactive pages with a live validator — they are not duplicated here.

| Symbol | Page |
|------|------|
| [`BOMV1`](/docs/schemas/bom-v1) | TACO schema model — explore the typed structure interactively. |
| [`RFIV1`](/docs/schemas/rfi-v1) | TACO schema model — explore the typed structure interactively. |
| [`EstimateV1`](/docs/schemas/estimate-v1) | TACO schema model — explore the typed structure interactively. |
| [`QuoteV1`](/docs/schemas/quote-v1) | TACO schema model — explore the typed structure interactively. |
| [`ScheduleV1`](/docs/schemas/schedule-v1) | TACO schema model — explore the typed structure interactively. |
| [`ChangeOrderV1`](/docs/schemas/change-order-v1) | TACO schema model — explore the typed structure interactively. |

## Regenerating

```bash
cd sdk && pip install -e ".[all]"
cd ../website && python scripts/gen-sdk-reference.py
```

Use Python 3.10, the SDK's minimum version: a few signatures (Enum constructors, for example) render differently on newer versions.
