---
title: ADR-0009 — Construction extension URI naming
description: Why TACO declares its A2A extension under `https://taco.construction/extensions/x-construction/v1` and what the URI structure commits us to.
sidebar_position: 9
---

# ADR-0009 — Construction extension URI naming

**Status:** Accepted
**Date:** 2026-05-20

## Context

A2A v1 added a formal extension declaration mechanism: agents list the extensions they implement under `capabilities.extensions[]`, where each entry has a URI identifying the extension. This is how v1-aware clients can negotiate which non-core features an agent supports.

TACO's `x-construction` field is exactly such an extension. We needed a permanent URI for it — one that:

1. Identifies TACO unambiguously across the ecosystem
2. Supports versioning of the extension over time
3. Doesn't tie us to any single hosting decision
4. Reads sensibly to humans browsing an agent card

## Decision

The TACO construction extension is identified by:

```
https://taco.construction/extensions/x-construction/v1
```

The URI structure is:

- `https://taco.construction/` — the protocol's stable identity authority (this is a domain we own; we commit to keeping the URI resolvable)
- `extensions/` — namespace for TACO-defined extensions (future extensions go here)
- `x-construction/` — the extension name (matches the field name on the Agent Card)
- `v1` — the version

The constant is exposed in the SDK as `taco.X_CONSTRUCTION_EXTENSION_URI` so applications never hardcode the string. `ConstructionAgentCard.to_a2a()` declares the URI under `capabilities.extensions[]` automatically; agents built outside the factory can call `apply_construction_extension_declaration(card)` to add it.

The URI resolves to a documentation page describing the extension's contract — what fields it adds, what the version commitment is, where the source schema lives.

## Alternatives considered

### Use the documentation URL as the identifier

Pros: every URL is one fewer dependency to remember.

Cons: documentation moves. Pages get restructured. A URI that's *only* meaningful as a doc reference breaks when someone restructures the docs site. Identifier URIs should be stable artifacts, not navigation aids.

### Use a GitHub raw URL

Pros: free, version-controlled, easy to maintain.

Cons:
- Ties the extension's identity to GitHub. If we ever move the repo or the org renames, every deployed agent card has a now-broken extension URI.
- Reads badly to humans browsing the card. `https://raw.githubusercontent.com/pelles-ai/taco/main/spec/extensions/x-construction.json` is not a name; it's a path.

### Use a URN scheme

Pros: URNs (`urn:taco:x-construction:v1`) are intended for exactly this — naming things without implying a location.

Cons:
- URN registration is heavyweight (IANA). The benefit is negligible since URIs already work fine.
- Tooling support for URNs in modern web stacks is patchy.

### Use a non-`https` URL scheme (e.g. `taco://`)

Pros: makes it clear the URI is an identifier, not a fetchable resource.

Cons: browsers and tooling treat non-`http(s)` schemes as suspicious. The "is this URL clickable?" affordance is lost.

## Consequences

### Positive

- A2A v1 capability negotiation works: a v1-aware client can check whether an agent declares `https://taco.construction/extensions/x-construction/v1` and route accordingly.
- The URI is human-readable. A construction professional auditing an agent card sees "this agent supports the TACO construction extension v1" and can act on it.
- Versioning is built into the URI itself. When we ship v2 (we won't anytime soon, see [ADR-0006](./schema-versioning) on our versioning conservatism), it'll be `.../x-construction/v2`. Agents supporting both can declare both URIs.
- The namespace is extensible: `https://taco.construction/extensions/{name}/v{N}` is a pattern for future TACO extensions beyond `x-construction`.

### Negative

- We're now committed to keeping `https://taco.construction/` resolvable. Domain ownership is a quasi-permanent obligation; if the project ever stops being actively maintained, the URI becomes a broken dependency for every deployed agent.
- Cool URIs don't change. Once we ship v1, the v1 URI is permanent — we can't fix it later if we discover a problem with the structure.
- The URI authority (`taco.construction`) is implicitly tied to a single owner. If TACO ever needs to fork governance (Linux Foundation takeover, e.g.), the URI either follows the project (good) or stays with the original owner (awkward). We accept this.

### Reversibility

Changing the URI breaks every deployed agent that declares it. Adding a new URI (e.g. forwarding to a foundation-owned domain) is feasible: a card can declare *both* the legacy URI and the new one during a migration window. Removing the legacy URI is the destructive step that has to wait for adoption to complete.

## What this URI does NOT commit us to

- The URI does not require the documentation at that path to stay identical. We can revise the page that describes the extension as long as we don't break the contract.
- The URI does not require that fetching it returns the JSON Schema. It's an identifier, not a fetchable schema document. (The JSON Schema for the inline `x-construction` object lives at `/schemas/x-construction.json` — separately, identifiable by name.)
- The URI does not require any specific deserialization behavior. v1-aware clients use it for capability detection; the actual on-the-wire shape is still determined by the agent card itself.

## References

- [`X_CONSTRUCTION_EXTENSION_URI`](/docs/sdk-reference/agent-cards) — the SDK constant
- [`apply_construction_extension_declaration`](/docs/sdk-reference/agent-cards) — helper for adding the declaration to a card built outside the factory
- [Agent Card Extensions doc](../agent-card-extensions)
- W3C "[Cool URIs don't change](https://www.w3.org/Provider/Style/URI)"
