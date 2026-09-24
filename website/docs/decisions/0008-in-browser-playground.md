---
title: ADR-0008 — Run the real SDK in the browser for the playground
description: Why the /playground page runs the published taco-agent package in the visitor's browser with Pyodide, instead of a server-side runner, a simulated SDK or a link to a hosted notebook.
sidebar_position: 8
---

# ADR-0008 — Run the real SDK in the browser for the playground

**Status:** Accepted
**Date:** 2026-09-23

## Context

The site has a [playground](/playground) where a visitor can edit Python that uses the TACO SDK and see its output without installing anything. The examples define an Agent Card, serve it with `A2AServer`, send it a typed task with `TacoClient`, discover agents with `AgentRegistry` and validate a payload against a schema model.

Someone evaluating TACO is asking whether the SDK is real and how much work it is to use. So the playground has to run the code they would run themselves. A convincing imitation isn't enough.

We considered four ways to run the code:

1. **A server-side runner.** The page sends the code to a service that runs it and returns the output.
2. **A simulated SDK.** A small Python module that mirrors the SDK's public names but returns canned, schema-shaped responses. An earlier draft of this ADR chose this, as a `taco_browser` shim, because `a2a-sdk` then had no path to a WebAssembly build.
3. **A link out** to Colab, Replit or a similar hosted notebook.
4. **The real package in the browser.** Load [Pyodide](https://pyodide.org) (CPython compiled to WebAssembly) and install `taco-agent` from PyPI with micropip.

## Decision

Run the real package in the browser (option 4).

- The page loads Pyodide from its CDN only when the visitor first presses Run. It installs `taco-agent[server,client]` from PyPI, pinned to the release the site was built from (read from the latest git tag at build time). If that release is not on PyPI yet, it installs the latest release and says so under the editor.
- `taco-agent` requires `protobuf<6`, but Pyodide bundles a newer protobuf, and micropip does not backtrack. The page therefore pins protobuf and the Google packages that depend on it to versions that accept protobuf 5. The pins live next to the examples in `website/src/data/playground-presets.js`.
- Python runs in a Web Worker. The page stays responsive while a run is in progress, and Stop can end a run that never returns by ending the worker.
- The server examples use the real `A2AServer` and `TacoClient`, with an in-memory transport (`httpx.ASGITransport`) standing in for the network. A browser tab cannot listen on a port, and every other part of the request path is the code a deployed agent runs.
- CI runs every example in Pyodide against a wheel built from the SDK in the same commit, using `website/scripts/check-playground.mjs`. A change to the SDK that breaks an example fails its pull request.

## Alternatives considered

### Server-side runner

**For:**
- Any Python version and any dependency.
- Nothing heavy for the browser to download.

**Against:**
- A running cost that grows with use.
- A sandboxed execution service that needs abuse controls.
- A network round trip on every run.
- The site now has no backend. This would add one, and an outage would take the page down with it.

### Simulated SDK

**For:**
- Small and fast to load.
- It avoided the dependency problem the earlier draft faced.

**Against:**
- A simulation drifts from the SDK every time the SDK changes.
- It stops at the edge of the surface it copies. A visitor who tries anything outside it hits an error that says nothing about TACO.
- A page that exists to show the SDK is real should not be running a stand-in.

### Link to a hosted notebook

**For:**
- No work to build.

**Against:**
- It sends the visitor off the site, often through a sign-in.
- It adds an outside dependency with its own outages and limits.

## Consequences

### Positive

- The code on the page is the code a visitor would run. Anything that works in the playground works after `pip install taco-agent`.
- The examples cannot quietly go stale: CI runs them against every SDK change.
- No server and no running cost. The page is static files, like the rest of the site.
- The visitor's code never leaves their browser.

### Negative

- The first run downloads about 25 MB: the Pyodide runtime and the SDK's dependencies. The browser caches it for later visits. Nothing loads until the visitor presses Run, so the rest of the site is not affected.
- The page depends on two outside services at run time: the Pyodide CDN (cdn.jsdelivr.net) and PyPI. A network that blocks either blocks the playground, and the page says so.
- The protobuf pins must be kept in step with the SDK's own protobuf requirement. CI catches a mismatch, but someone still has to update the pins.
- Pyodide is a large dependency we don't control. The Pyodide version is pinned, and moving to a new one is a deliberate change that CI checks.

### Reversibility

High. The playground is one page and one component. Nothing else on the site depends on it. The page could switch to a server-side runner, or be removed, without touching anything else.

## References

- [Playground](/playground)
- [`website/src/components/Playground.js`](https://github.com/pelles-ai/taco/blob/main/website/src/components/Playground.js): the page component and the Web Worker
- [`website/src/data/playground-presets.js`](https://github.com/pelles-ai/taco/blob/main/website/src/data/playground-presets.js): the examples, the Pyodide version and the pins
- [`website/scripts/check-playground.mjs`](https://github.com/pelles-ai/taco/blob/main/website/scripts/check-playground.mjs): the CI check
- [Pyodide](https://pyodide.org)
