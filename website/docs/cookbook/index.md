---
sidebar_position: 0
title: Cookbook
description: Multi-agent recipes for real construction workflows — typed end-to-end, copy-paste runnable, sequence diagrams included.
---

import RecipeCard from '@site/src/components/RecipeCard';

# Cookbook

A growing library of multi-agent workflows you can lift directly into a project. Every recipe has a sequence diagram, the full Python that runs against `taco-agent`, and shows the typed data that flows between agents.

These are the patterns we keep watching teams reimplement from scratch. The point of TACO is that you shouldn't have to.

## Multi-trade chains

<div className="recipe-grid">

<RecipeCard
  slug="gc-estimator-supplier-chain"
  title="GC → Estimator → Supplier"
  blurb="The canonical three-hop chain. A GC orchestrator generates a takeoff, hands it to a mechanical estimator for cost, then to a supplier agent for live pricing."
  agents="3"
  schemas={['bom-v1', 'estimate-v1', 'quote-v1']}
  taskTypes={['takeoff', 'estimate', 'material-procurement']}
  complexity="intermediate"
  readTime="8 min"
/>

<RecipeCard
  slug="bom-to-quote-marketplace"
  title="BOM-to-Quote Marketplace"
  blurb="Fan a single BOM out to multiple supplier agents in parallel, then level the quotes. Shows asyncio.gather with TACO clients and best-quote selection."
  agents="3+"
  schemas={['bom-v1', 'quote-v1']}
  taskTypes={['material-procurement']}
  complexity="intermediate"
  readTime="6 min"
/>

</div>

## Document workflows

<div className="recipe-grid">

<RecipeCard
  slug="rfi-round-trip"
  title="RFI Round-trip"
  blurb="A drawing-audit agent flags a design conflict, generates an RFI, and routes it to a design-side agent that drafts a typed response — all without leaving the protocol."
  agents="2"
  schemas={['rfi-v1']}
  taskTypes={['rfi-generation', 'rfi-response']}
  complexity="beginner"
  readTime="5 min"
/>

</div>

## Cross-schema reasoning

<div className="recipe-grid">

<RecipeCard
  slug="change-order-impact"
  title="Change Order Impact"
  blurb="When scope shifts mid-project, a change-order agent reads the current estimate AND schedule together and emits a typed delta covering cost and timeline."
  agents="3"
  schemas={['estimate-v1', 'schedule-v1', 'change-order-v1']}
  taskTypes={['change-order-analysis']}
  complexity="advanced"
  readTime="9 min"
/>

<RecipeCard
  slug="schedule-aware-procurement"
  title="Schedule-Aware Procurement"
  blurb="Procurement that respects sequencing. The supplier agent quotes lead times that get cross-checked against the project schedule before any PO is committed."
  agents="3"
  schemas={['bom-v1', 'schedule-v1', 'quote-v1']}
  taskTypes={['material-procurement', 'schedule-coordination']}
  complexity="advanced"
  readTime="9 min"
/>

</div>

## Contributing a recipe

Have a multi-agent pattern that took you a while to figure out? [Open a PR adding a recipe](https://github.com/pelles-ai/taco/edit/main/website/docs/cookbook/index.md). The format is enforced by example — each recipe page should have:

1. **Goal** — one sentence
2. **Agents involved** — names, trades, skills they advertise
3. **Sequence diagram** — `<SequenceDiagram />` from `@site/src/components/SequenceDiagram`
4. **Full Python** — copy-paste runnable against `taco-agent`
5. **Sample data** — the typed artifacts that flow through
6. **Variations** — what to change for adjacent use cases
