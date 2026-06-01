---
title: "Enums"
description: "Construction-domain enumerations used across the schemas, agent cards, and task types."
sidebar_position: 10
---

:::info Generated
This page is generated from the SDK source by [`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).
Edit the source docstrings (or this script) and re-run; do not edit
this MDX by hand.
:::

# Enums

Construction-domain enumerations used across the schemas, agent cards, and task types.

## `Trade`

*Type alias.*

```python
Trade = Literal['mechanical', 'electrical', 'plumbing', 'structural', 'civil', 'architectural', 'fire-protection', 'general', 'multi-trade']
```

## `ProjectType`

*Type alias.*

```python
ProjectType = Literal['commercial', 'residential', 'healthcare', 'education', 'industrial', 'infrastructure', 'mixed-use']
```

## `Integration`

*Type alias.*

```python
Integration = Literal['procore', 'acc', 'bluebeam', 'plangrid', 'p6', 'ms-project', 'sage', 'viewpoint']
```

## `Certification`

*Type alias.*

```python
Certification = Literal['SOC2', 'ISO27001', 'FedRAMP']
```

## `Availability`

*Type alias.*

```python
Availability = Literal['in-stock', 'made-to-order', 'backordered']
```

## `BOMUnit`

*Type alias.*

```python
BOMUnit = Literal['EA', 'LF', 'SF', 'CF', 'CY', 'TON', 'LB', 'GAL', 'LS']
```

## `FlagSeverity`

*Type alias.*

```python
FlagSeverity = Literal['info', 'warning', 'error']
```

## `RFICategory`

*Type alias.*

```python
RFICategory = Literal['design-conflict', 'missing-information', 'clarification', 'substitution', 'coordination', 'code-compliance']
```

## `RFIPriority`

*Type alias.*

```python
RFIPriority = Literal['low', 'medium', 'high', 'critical']
```

## See also

- [Agent Card Extensions concept](/docs/agent-card-extensions)
- [Standards alignment](/docs/standards)
- [Cookbook: GC → Estimator → Supplier chain](/docs/cookbook/gc-estimator-supplier-chain)

