---
title: "Auth"
description: "Bearer-token authentication for `A2AServer`: a verifier you supply, the caller's identity inside handlers, and the `taco:task:<taskType>` scope helper."
sidebar_position: 3
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Auth

Bearer-token authentication for `A2AServer`: a verifier you supply, the caller's identity inside handlers, and the `taco:task:<taskType>` scope helper.

## `AuthContext`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/auth.py#L48)

Who is calling, as established by a :data:`TokenVerifier`.

Attributes:
    subject: Stable caller identity (for example the token's ``sub``).
        Tasks are stored per subject.
    scopes: Granted scopes, e.g. ``{"taco:task:estimate"}``.
    claims: Any other token claims your handlers need.

#### Constructor

```python
AuthContext(subject: 'str', scopes: 'frozenset[str]' = frozenset(), claims: 'dict[str, Any]' = <factory>) -> None
```

#### Methods

### `has_scope()`

```python
def has_scope(self, scope: 'str') -> 'bool'
```

*No docstring.*


## `TokenVerifier`

*Type alias.*

`async (token) -> AuthContext | None`. Pass one to `A2AServer(token_verifier=...)`; return `None` to reject the token (HTTP 401).

```python
TokenVerifier = Callable[[str], Awaitable['AuthContext | None']]
```

## `current_auth()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/auth.py#L75)

```python
current_auth() -> 'AuthContext | None'
```

The calling peer's :class:`AuthContext` inside a task handler.

``None`` when the server has no ``token_verifier``.

## `task_scope()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/auth.py#L83)

```python
task_scope(task_type: 'str') -> 'str'
```

The scope a token needs to request ``task_type`` (``taco:task:<type>``).

## See also

- [Security: implementing it with the SDK](/docs/security#implementing-it-with-the-sdk)
- [SPEC-004 Security](/docs/spec/SPEC-004-security)
- [SDK Guide](/docs/sdk)

