---
title: "Push Notifications"
description: "Multi-subscriber push notification configs per task. Used by `TacoClient.create_push_config()` and friends."
sidebar_position: 9
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Push Notifications

Multi-subscriber push notification configs per task. Used by `TacoClient.create_push_config()` and friends.

## `PushNotificationConfig`

*Extends:* `A2ABaseModel`

Defines the configuration for setting up push notifications for task updates.

#### Constructor

```python
PushNotificationConfig(*, authentication: a2a.compat.v0_3.types.PushNotificationAuthenticationInfo | None = None, id: str | None = None, token: str | None = None, url: str) -> None
```


## `PushNotificationAuthenticationInfo`

*Extends:* `A2ABaseModel`

Defines authentication details for a push notification endpoint.

#### Constructor

```python
PushNotificationAuthenticationInfo(*, credentials: str | None = None, schemes: list[str]) -> None
```


## `TaskPushNotificationConfig`

*Extends:* `A2ABaseModel`

A container associating a push notification configuration with a specific task.

#### Constructor

```python
TaskPushNotificationConfig(*, pushNotificationConfig: a2a.compat.v0_3.types.PushNotificationConfig, taskId: str) -> None
```


