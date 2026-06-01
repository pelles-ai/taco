---
slug: schema-versioning-in-practice
title: Schema versioning in practice — why bom-v1 will outlive your contract
authors:
  - name: Pelles + TACO contributors
    url: https://github.com/pelles-ai
tags: [schemas, versioning, design]
---

When we wrote [ADR-0006](/docs/decisions/schema-versioning), we committed to a strict policy: `bom-v1` means what it means today, forever. New fields can be added optionally; nothing else can change. A breaking change mints `bom-v2`.

Three months in, the policy is being tested. This post is the field report.

<!-- truncate -->

## The pressure to break the rule

Within the first month of `bom-v1` being widely used, we got three serious requests to "just refine" the schema:

1. A takeoff vendor wanted `quantity` to be either a number or a `{value, unit}` object (for cases where the takeoff produces a measurement with explicit units). "It's still a number — we're just adding more context."

2. A GC wanted to rename `csiDivision` to `csiSection` because their internal taxonomy uses "section" for the same concept. "It's a one-word change. Everybody already calls it sections."

3. An estimator wanted to make `material` required (instead of optional) because their downstream pricing model breaks without it. "Every line item has a material; nobody emits BOMs without one."

Each request was well-reasoned. Each one was breaking. We rejected all three.

## Why we rejected them — concretely

### The `quantity` union request

The proposal: change `quantity` from `number` to `number | object`.

The cost: every existing consumer that does `lineItem.quantity * 2` now has to handle the object case. *Every* consumer, retroactively. The takeoff vendor would have gotten what they wanted; the dozen other agents reading BOMs would silently start mishandling some inputs.

The right answer: add an optional `quantityWithUnit` field. Existing consumers ignore it; the takeoff vendor populates it when they have the richer measurement; advanced consumers can use the new field when present. Nothing breaks.

The vendor's first reaction was "but then existing consumers won't get the benefit." That's true — and it's the correct outcome. They're not ready for it; they don't need to handle it. When they upgrade, they upgrade *opt-in*, not because the wire changed under them.

### The `csiDivision` rename

The proposal: rename `csiDivision` to `csiSection`.

The cost: every existing producer emits `csiDivision`. Every existing consumer reads `csiDivision`. The rename forces a coordinated, simultaneous update across every TACO agent in the world. That's the kind of coordination that doesn't happen in real ecosystems — it just produces a long tail of broken integrations.

The right answer: don't rename. The field name shipped; it shipped widely; it's now part of the contract. Internal documentation can call it "section" if that's what teams prefer. The wire format doesn't have to match anyone's internal vocabulary.

This is the harder lesson: **vocabulary debates that happen after a field is shipped should not move the wire.** Mint `bom-v2` if there's enough other reason to. Don't mint a v2 just to rename one field.

### The required `material` field

The proposal: make `material` required in `bom-v1.lineItems[].material`.

The cost: every existing producer that doesn't always emit `material` (which is approximately all of them — the field was optional from day one) is now non-compliant. Their BOMs would fail strict validation; their integrations with downstream agents would break.

The right answer: the estimator's downstream pricing model should handle missing `material` gracefully (a default category, a request for clarification, a typed rejection artifact — pick one). Their requirement is real but isn't a *protocol* requirement; it's *their* requirement. The protocol doesn't centralize requirements from individual consumers.

If `material` becomes truly universal in practice, we can revisit it for `bom-v2`. Not now.

## What "additive only" looks like in motion

Three real additions we've shipped to `bom-v1` since v0.3:

1. **`metadata.confidence`** — float 0-1, optional. Lets a takeoff agent express uncertainty in its output. Existing consumers ignore it; agents that care about confidence can use it.

2. **`metadata.flaggedItems[]`** — list of `{lineItemId, reason, severity}`. Lets agents surface items needing human review. Old consumers see an empty list; new consumers can route to a review queue.

3. **`lineItems[].alternates[]`** — list of acceptable equivalents. Lets a designer say "any of these manufacturers is OK." Old consumers ignore it; new consumers can use it for substitution decisions.

None of these required coordination. Every existing agent kept working. New agents could start producing the new fields immediately.

That's the test of an additive change: **shipping it requires zero changes to anyone else.**

## When `bom-v2` will land

Honest answer: we don't have a target date.

The bar is high because we've internalized what `bom-v2` would cost: every agent in the ecosystem at v2-flip time has to decide whether to support v1, v2, or both. Producers that emit v2 lose interop with consumers that only read v1. The "advertise multiple skills" workaround (`generate-bom-v1`, `generate-bom-v2`) helps but doubles the surface area.

What would trigger it:

- A field's *semantic identity* changes. Not its name, its *meaning*. (E.g. `quantity` becoming "total including waste" instead of "net" — that's a v2 change even if the name stays the same.)
- An industry standard forces a wire-level change (e.g. CSI MasterFormat 2030 reorganizing division numbers materially).
- Three or more independent agents request the same breaking change for the same reason. (Single requests don't move it; convergent requests across an ecosystem do.)

None of these have happened. We expect `bom-v1` to be the canonical BOM schema through 2030 at minimum.

## The discipline this requires

Schema versioning policy is one of those decisions that pays for itself months and years after you make it. The temptation to "just fix this one thing" is constant. The discipline to say "no, we ship a v2 for that, and only if there's enough other reason" — that's what makes a protocol *protocol-grade* instead of *library-grade*.

We resist breaking changes because breaking changes are expensive for *every* user, not just the one asking. The cost is paid by people who weren't in the conversation.

## What this means for you

If you're consuming TACO schemas:

- Code defensively against the *current* schema. Treat optional fields as optional. Don't assume new fields will appear on existing producers.
- When new fields land in v0.x SDK releases, you can adopt them when ready. They won't break you if you don't.
- When `*-v2` schemas land (eventually), you'll have a clear migration window. We won't deprecate v1 fast.

If you're producing TACO schemas:

- Validate strictly against the canonical JSON Schema. The conformance runner catches drift.
- Use the optional fields when you have something meaningful to put in them. Skipping them is fine; populating them adds value to advanced consumers.
- If you'd like a new field, propose it as additive. We'll add it; that's the easy case.

## See also

- [ADR-0006 — Schema versioning](/docs/decisions/schema-versioning) — the formal decision record
- [Data Schemas](/docs/schemas/) — the canonical schemas with their interactive explorer
- [Best Practices on schema evolution](/docs/best-practices#schema-evolution)
