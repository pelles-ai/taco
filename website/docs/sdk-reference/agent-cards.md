---
title: "Agent Cards"
description: "Construct, validate, and serve the Agent Card a TACO agent advertises at `/.well-known/agent-card.json`."
sidebar_position: 1
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Agent Cards

Construct, validate, and serve the Agent Card a TACO agent advertises at `/.well-known/agent-card.json`.

## `ConstructionAgentCard`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/agent_card.py#L64)

Factory for building an AgentCard with x-construction pre-populated.

Example::

    card = ConstructionAgentCard(
        name="My Estimating Agent",
        description="Estimates mechanical work",
        url="http://localhost:8001",
        trade="mechanical",
        csi_divisions=["22", "23"],
        skills=[skill],
    )
    agent_card = card.to_a2a()
    card.serve(host="0.0.0.0", port=8001)

#### Constructor

```python
ConstructionAgentCard(*, name: 'str', description: 'str' = '', url: 'str' = '', trade: 'Trade', csi_divisions: 'list[str]', project_types: 'list[str] | None' = None, data_formats: 'dict[str, list[str]] | None' = None, integrations: 'list[str] | None' = None, skills: 'list[ConstructionSkill] | None' = None) -> 'None'
```

#### Methods

### `serve()`

```python
def serve(self, *, host: 'str' = '0.0.0.0', port: 'int' = 8080) -> 'None'
```

Start an A2A-compliant server for this agent.

Requires the ``server`` extra: ``pip install taco-agent[server]``

### `to_a2a()`

```python
def to_a2a(self) -> 'AgentCard'
```

Convert to a standard A2A AgentCard with x-construction extension.

Also declares the formal ``x-construction`` extension URI in
``capabilities.extensions[]`` so A2A v1 clients can detect support
via capability negotiation in addition to reading the inline field.


## `ConstructionSkill`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/agent_card.py#L16)

Factory for building an AgentSkill with x-construction pre-populated.

Example::

    skill = ConstructionSkill(
        id="generate-estimate",
        name="Generate Cost Estimate",
        description="Produces an estimate-v1 from a BOM",
        task_type="estimate",
        input_schema="bom-v1",
        output_schema="estimate-v1",
    )
    agent_skill = skill.to_a2a()

#### Constructor

```python
ConstructionSkill(*, id: 'str', name: 'str' = '', description: 'str' = '', task_type: 'str', input_schema: 'str | None' = None, output_schema: 'str') -> 'None'
```

#### Methods

### `to_a2a()`

```python
def to_a2a(self) -> 'AgentSkill'
```

Convert to a standard A2A AgentSkill with x-construction extension.


## `AgentCard`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/types.py#L179)

*Extends:* `A2ABaseModel`

A2A AgentCard with TACO x-construction extension.

Extends the standard agent card with an optional x-construction
field for construction-specific agent metadata (trade, CSI divisions,
project types, etc.).

#### Constructor

```python
AgentCard(*, name: typing.Annotated[str, MinLen(min_length=1)], description: typing.Annotated[str, MinLen(min_length=1)], url: str, version: str = '1.0.0', defaultInputModes: list[str] = <factory>, defaultOutputModes: list[str] = <factory>, capabilities: a2a.compat.v0_3.types.AgentCapabilities = <factory>, skills: list[taco.types.AgentSkill] = <factory>, x_construction: taco.types.AgentConstructionExt | None = None) -> None
```


## `AgentSkill`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/types.py#L159)

*Extends:* `A2ABaseModel`

A2A AgentSkill with TACO x-construction extension.

Extends the standard skill with an optional x-construction field
for construction-specific task routing metadata.

#### Constructor

```python
AgentSkill(*, id: str, name: str, description: str, tags: list[str] = <factory>, inputModes: list[str] | None = None, outputModes: list[str] | None = None, examples: list[str] | None = None, x_construction: taco.types.SkillConstructionExt | None = None) -> None
```


## `AgentCapabilities`

*Extends:* `A2ABaseModel`

Defines optional capabilities supported by an agent.

#### Constructor

```python
AgentCapabilities(*, extensions: list[a2a.compat.v0_3.types.AgentExtension] | None = None, pushNotifications: bool | None = None, stateTransitionHistory: bool | None = None, streaming: bool | None = None) -> None
```


## `AgentExtension`

*Extends:* `A2ABaseModel`

A declaration of a protocol extension supported by an Agent.

#### Constructor

```python
AgentExtension(*, description: str | None = None, params: dict[str, typing.Any] | None = None, required: bool | None = None, uri: str) -> None
```


## `AgentConstructionExt`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/types.py#L139)

*Extends:* `A2ABaseModel`

Top-level x-construction extension on an Agent Card.

#### Constructor

```python
AgentConstructionExt(*, trade: Literal['mechanical', 'electrical', 'plumbing', 'structural', 'civil', 'architectural', 'fire-protection', 'general', 'multi-trade'], csiDivisions: list[str] = <factory>, projectTypes: list[typing.Literal['commercial', 'residential', 'healthcare', 'education', 'industrial', 'infrastructure', 'mixed-use']] = <factory>, certifications: list[typing.Literal['SOC2', 'ISO27001', 'FedRAMP']] = <factory>, dataFormats: dict[str, list[str]] = <factory>, integrations: list[typing.Literal['procore', 'acc', 'bluebeam', 'plangrid', 'p6', 'ms-project', 'sage', 'viewpoint']] = <factory>, security: taco.types.SecurityExt | None = None) -> None
```


## `SkillConstructionExt`


[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/types.py#L121)

*Extends:* `A2ABaseModel`

x-construction extension on a skill.

#### Constructor

```python
SkillConstructionExt(*, taskType: str, inputSchema: str | None = None, outputSchema: str) -> None
```


## `get_construction_ext()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/types.py#L214)

```python
get_construction_ext(card: 'AgentCard') -> 'AgentConstructionExt | None'
```

Extract x-construction extension from a TACO AgentCard.

## `get_skill_construction_ext()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/types.py#L219)

```python
get_skill_construction_ext(skill: 'AgentSkill') -> 'SkillConstructionExt | None'
```

Extract x-construction extension from a TACO AgentSkill.

## `apply_construction_extension_declaration()`

[Source on GitHub](https://github.com/pelles-ai/taco/blob/main/sdk/taco/types.py#L242)

```python
apply_construction_extension_declaration(card: 'AgentCard') -> 'AgentCard'
```

Ensure ``card.capabilities.extensions[]`` advertises ``x-construction``.

Mutates and returns ``card``. No-op if ``card.x_construction`` is ``None``
or if the URI is already declared (idempotent — safe to call repeatedly).

### `X_CONSTRUCTION_EXTENSION_URI`

```python
X_CONSTRUCTION_EXTENSION_URI: str = "https://taco.construction/extensions/x-construction/v1"
```

## See also

- [Build a Custom Agent](/docs/getting-started/build-agent)
- [Agent Card Extensions concept](/docs/agent-card-extensions)
- [Cookbook: GC → Estimator → Supplier chain](/docs/cookbook/gc-estimator-supplier-chain)

