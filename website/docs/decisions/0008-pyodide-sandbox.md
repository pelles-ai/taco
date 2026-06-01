---
title: ADR-0008 — Pyodide for the in-browser sandbox
description: Why /sandbox runs real CPython in the browser via Pyodide instead of a server-side execution backend or a JavaScript-simulated REPL.
sidebar_position: 8
---

# ADR-0008 — Pyodide for the in-browser sandbox

**Status:** Accepted
**Date:** 2026-05-18

## Context

The TACO website has a `/sandbox` page where visitors can write Python and see typed TACO output without installing anything. The question is *how* the Python runs.

Three realistic implementations:

1. **Server-side execution.** User submits code, we run it on our infrastructure, return output. Requires a backend, sandboxing infrastructure, rate limiting, and ongoing operational cost.

2. **JavaScript-simulated Python.** Build a small interpreter (or use a library) that handles a Python-shaped subset on the client. No real CPython, just a convincing illusion.

3. **Pyodide.** Load a WebAssembly build of CPython into the browser. Run real Python entirely client-side.

Pyodide is ~10 MB compressed, which would have been a non-starter as a homepage dep. As a `/sandbox` page that's lazy-loaded on demand, the tradeoff changes.

## Decision

Use **Pyodide**. Lazy-load the runtime when the user first clicks Run; cache aggressively (browser HTTP cache handles this — the runtime is content-addressed by version). Ship a small `taco_browser.py` shim that mirrors the SDK's public surface but returns canned, schema-shaped responses instead of making real network calls.

The shim lives at `/static/sandbox/taco_browser.py` and is fetched into Pyodide's virtual filesystem after the runtime initializes. User code imports it as `from taco_browser import …`.

## Alternatives considered

### Server-side execution

Pros: any Python version, any dependencies, no client-bundle weight.

Cons:
- Permanent backend cost. The sandbox would need a sandboxed code-execution service (gVisor, Firecracker, or a hosted equivalent). Hosting bill grows with usage.
- Rate limiting, abuse mitigation, and security review become ongoing concerns. Code-execution endpoints are top-of-the-list targets for resource exhaustion attacks.
- Latency: every Run becomes a network round-trip plus container startup. Pyodide's first-run cost is ~3-5 seconds; subsequent runs are sub-100ms.
- The sandbox stops working if our hosting goes down — which means the docs site has a server-dependency it doesn't otherwise need.

### JavaScript-simulated Python

Pros: tiny — could fit in a few hundred KB.

Cons:
- Pretending to be CPython is a lot of work. Subset coverage decisions become permanent technical debt; users who try features outside the subset get cryptic errors.
- The illusion is the wrong thing for an audience evaluating "is TACO real?" The whole point of `/sandbox` is to feel like you're using the actual SDK. A simulation undermines that goal.
- Pydantic — central to TACO's typed model — would not work in a JS-faked Python.

### Don't ship a sandbox; just link to Colab / Replit

Pros: zero implementation cost.

Cons:
- External dependency. Both have outages, rate limits, and require sign-in for non-trivial use.
- Visitors don't follow links out of docs reliably. "Try in browser" needs to mean *in this browser*, not "go log in to Google Colab."

## Consequences

### Positive

- First-load is one-time. After the initial Pyodide download, subsequent visits read from browser cache; Run is instant.
- The shim API surface matches the real SDK. Users learn the actual API, not a sandbox dialect.
- Zero ongoing operational cost. The sandbox is a static asset bundle.
- Works offline once cached. The docs site is fully usable on a plane.
- Privacy: no code leaves the user's browser. For visitors evaluating TACO in a regulated environment, this matters.

### Negative

- ~10 MB initial download. Mitigated by lazy-loading (the page does this in `requestIdleCallback` after the rest of the page renders), but it's the bottom of the Lighthouse score for this single page.
- Limited dependency set. Pyodide ships a curated subset of Python packages. We can't `pip install taco-agent` because `a2a-sdk` depends on protobuf (no Pyodide wheel) and a few other natives. The shim is the workaround; users hit its boundaries when they try to import the real SDK.
- The shim drifts from the real SDK if maintainers update one and forget the other. Mitigated by keeping the shim surface deliberately narrow.
- Pyodide is a substantial dependency we don't control. If it stagnates or breaks against a future browser, we have a problem.

### Reversibility

Replacing Pyodide is a substantial swap but bounded. The `/sandbox` page is the only consumer; the rest of the site doesn't depend on it. If we ever need to switch (to a smaller WASM runtime, to a server-side mode, to a third-party platform), the impact is local.

## References

- [Pyodide project](https://pyodide.org/)
- [`/sandbox`](/sandbox) — the deployed page
- [`/static/sandbox/taco_browser.py`](https://github.com/pelles-ai/taco/blob/main/website/static/sandbox/taco_browser.py) — the shim source
