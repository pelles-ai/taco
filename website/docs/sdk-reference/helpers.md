---
title: "Helpers"
description: "Convenience constructors and extractors for messages, parts, and artifacts. Use these instead of constructing A2A types directly."
sidebar_position: 7
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
make_message(role: 'str', parts: 'list[Part]', *, message_id: 'str | None' = None, reference_task_ids: 'list[str] | None' = None) -> 'Message'
```

Create an A2A Message with auto-generated message_id.

``reference_task_ids`` lists prior tasks this message logically
follows up on (A2A v1 spec). TACO uses it to thread RFI responses
back to the originating RFI task, change-order approvals back to
the proposal task, etc.

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

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L65)

```python
make_artifact(parts: 'list[Part]', *, name: 'str | None' = None, description: 'str | None' = None, artifact_id: 'str | None' = None, metadata: 'dict[str, Any] | None' = None) -> 'Artifact'
```

Create an A2A Artifact with auto-generated artifact_id.

## `extract_text()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L83)

```python
extract_text(part: 'Part') -> 'str | None'
```

Extract text from a Part, returning None if not a TextPart.

## `extract_structured_data()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L90)

```python
extract_structured_data(part: 'Part') -> 'dict[str, Any] | None'
```

Extract structured data from a Part, returning None if not a DataPart.

## `get_text_parts()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L104)

```python
get_text_parts(parts: 'list[Part]') -> 'list[str]'
```

Return the text payloads of every ``TextPart`` in ``parts``.

## `get_data_parts()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L109)

```python
get_data_parts(parts: 'list[Part]') -> 'list[dict[str, Any]]'
```

Return the data payloads of every ``DataPart`` in ``parts``.

## `get_file_parts()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L114)

```python
get_file_parts(parts: 'list[Part]') -> 'list[FilePart]'
```

Return every ``FilePart`` in ``parts``.

## `get_message_text()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L119)

```python
get_message_text(message: 'Message', separator: 'str' = '\n') -> 'str'
```

Concatenate the text of every ``TextPart`` in ``message.parts``.

## `new_text_artifact()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L138)

```python
new_text_artifact(*, name: 'str', text: 'str', description: 'str | None' = None) -> 'Artifact'
```

Create an ``Artifact`` containing a single ``TextPart``.

## `new_data_artifact()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L152)

```python
new_data_artifact(*, name: 'str', data: 'dict[str, Any]', description: 'str | None' = None) -> 'Artifact'
```

Create an ``Artifact`` containing a single ``DataPart``.

## `new_agent_text_message()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L124)

```python
new_agent_text_message(text: 'str', *, message_id: 'str | None' = None) -> 'Message'
```

Create an agent-role ``Message`` with a single ``TextPart``.

## `new_agent_parts_message()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/_compat.py#L129)

```python
new_agent_parts_message(parts: 'list[Part]', *, message_id: 'str | None' = None) -> 'Message'
```

Create an agent-role ``Message`` with the given parts.

## See also

- [Build a Custom Agent](/docs/getting-started/build-agent)
- [SDK Guide](/docs/sdk)
- [Cookbook: Change-order impact](/docs/cookbook/change-order-impact)

