---
title: "Helpers"
description: "Convenience constructors and extractors for messages, parts, and artifacts. Use these instead of constructing A2A types directly."
sidebar_position: 8
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Helpers

Convenience constructors and extractors for messages, parts, and artifacts. Use these instead of constructing A2A types directly.

## `make_message()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L41)

```python
make_message(role: 'str', parts: 'list[Part]', *, message_id: 'str | None' = None, reference_task_ids: 'list[str] | None' = None, context_id: 'str | None' = None) -> 'Message'
```

Create an A2A Message with auto-generated message_id.

``reference_task_ids`` lists prior tasks this message logically
follows up on (A2A v1 spec). TACO uses it to thread RFI responses
back to the originating RFI task, change-order approvals back to
the proposal task, etc.

``context_id`` puts the message in an existing conversation. A2A
carries it on the message itself, not on the request params.

## `make_text_part()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L31)

```python
make_text_part(text: 'str') -> 'Part'
```

Create a Part containing text.

## `make_data_part()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L36)

```python
make_data_part(data: 'dict[str, Any]') -> 'Part'
```

Create a Part containing structured data.

## `make_artifact()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L71)

```python
make_artifact(parts: 'list[Part]', *, name: 'str | None' = None, description: 'str | None' = None, artifact_id: 'str | None' = None, metadata: 'dict[str, Any] | None' = None) -> 'Artifact'
```

Create an A2A Artifact with auto-generated artifact_id.

## `extract_text()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L89)

```python
extract_text(part: 'Part') -> 'str | None'
```

Extract text from a Part, returning None if not a TextPart.

## `extract_structured_data()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L113)

```python
extract_structured_data(part: 'Part') -> 'dict[str, Any] | None'
```

Extract structured data from a Part, returning None if not a DataPart.

Whole-number values come back as ``int`` (see :func:`restore_integers`).

## `restore_integers()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L96)

```python
restore_integers(value: 'Any') -> 'Any'
```

Turn whole-number floats back into ints, recursively.

A2A v1 carries ``DataPart`` payloads as protobuf ``Struct`` values, which
store every number as a double, so ``{"count": 3}`` arrives as
``{"count": 3.0}``. JSON makes no int/float distinction, so restoring
ints loses nothing and lets handlers write ``range(data["count"])``.

## `get_text_parts()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L130)

```python
get_text_parts(parts: 'list[Part]') -> 'list[str]'
```

Return the text payloads of every ``TextPart`` in ``parts``.

## `get_data_parts()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L135)

```python
get_data_parts(parts: 'list[Part]') -> 'list[dict[str, Any]]'
```

Return the data payloads of every ``DataPart`` in ``parts``.

Whole-number values come back as ``int`` (see :func:`restore_integers`).

## `get_file_parts()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L143)

```python
get_file_parts(parts: 'list[Part]') -> 'list[FilePart]'
```

Return every ``FilePart`` in ``parts``.

## `get_message_text()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L148)

```python
get_message_text(message: 'Message', separator: 'str' = '\n') -> 'str'
```

Concatenate the text of every ``TextPart`` in ``message.parts``.

## `new_text_artifact()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L167)

```python
new_text_artifact(*, name: 'str', text: 'str', description: 'str | None' = None) -> 'Artifact'
```

Create an ``Artifact`` containing a single ``TextPart``.

## `new_data_artifact()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L181)

```python
new_data_artifact(*, name: 'str', data: 'dict[str, Any]', description: 'str | None' = None) -> 'Artifact'
```

Create an ``Artifact`` containing a single ``DataPart``.

## `new_agent_text_message()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L153)

```python
new_agent_text_message(text: 'str', *, message_id: 'str | None' = None) -> 'Message'
```

Create an agent-role ``Message`` with a single ``TextPart``.

## `new_agent_parts_message()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L158)

```python
new_agent_parts_message(parts: 'list[Part]', *, message_id: 'str | None' = None) -> 'Message'
```

Create an agent-role ``Message`` with the given parts.

## See also

- [Build a Custom Agent](/docs/getting-started/build-agent)
- [SDK Guide](/docs/sdk)
- [Cookbook: Change-order impact](/docs/cookbook/change-order-impact)

