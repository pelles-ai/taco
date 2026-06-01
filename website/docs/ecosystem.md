---
sidebar_position: 2
title: Ecosystem
description: Who is building with TACO and how to join the early ecosystem of construction agents, platforms, and tools.
---

# Ecosystem

TACO is in its early days. This page is the honest snapshot of who is building with it today and how to add your project to the list.

## Who is shipping TACO

### Initiators and contributors
- **[Pelles](https://pelles.ai)** — initiated TACO, maintains the SDK and reference implementations.

### Foundations and standards
- **[A2A Protocol](https://a2a-protocol.org)** (Linux Foundation) — the transport layer TACO is built on.
- **[Model Context Protocol](https://modelcontextprotocol.io)** — the tool-access protocol TACO agents commonly use vertically. See [A2A, MCP, and TACO](/docs/protocol-stack).

> Building a TACO agent or wrapping a platform? [Open a PR adding your project here.](https://github.com/pelles-ai/taco/edit/main/website/docs/ecosystem.md)

## Where TACO fits in the broader stack

| Layer | Examples |
|------|---------|
| **Construction platforms** | Procore, Autodesk Construction Cloud, Bluebeam, PlanGrid, Trimble Connect |
| **Estimating / takeoff tools** | Togal, Beam, Trade-specific takeoff suites |
| **BIM / drawings** | Revit, Navisworks, IFC, BIM 360 |
| **Scheduling** | P6, Microsoft Project, Smartsheet |
| **Agent runtimes** | LangChain, LlamaIndex, OpenAI Agents SDK, custom Python/Node agents |
| **TACO** | A thin layer that lets any of the above expose itself, or wrap itself, as an interoperable construction agent |

Any of the platforms above can be made TACO-compatible with a sidecar — see [Integrate Your Platform](/docs/getting-started/integrate-platform). The point is that adoption is not "rip and replace"; it is additive.

## Reference implementations

All Apache 2.0, all in the [main repo](https://github.com/pelles-ai/taco):

- **[`examples/`](https://github.com/pelles-ai/taco/tree/main/examples)** — a sandbox demo with three LLM-powered agents and an orchestrator dashboard. Runs locally, no API key required for the basics.
- **[`sdk/`](https://github.com/pelles-ai/taco/tree/main/sdk)** — the Python SDK itself, with `taco-agent` published to PyPI.
- **CLI** — `pip install taco-agent` ships the `taco` command for discovering and calling any TACO agent. See the [CLI Reference](/docs/cli).

## How to be listed here

1. Ship something — an agent, a sidecar, a tool, a reference implementation.
2. Open a PR against `website/docs/ecosystem.md` adding a one-liner about your project.
3. Or start an [Ecosystem discussion](https://github.com/pelles-ai/taco/discussions/categories/show-and-tell) and we will fold it in.

## Why we are not faking the list

A long ecosystem page with logos that do not actually use the protocol is a tell. TACO is new and we want the list here to mean something. If you are reading this and considering adopting, you are early — that is the point.

## Get involved

- **Build an agent.** [Quick Start](/docs/getting-started/quick-start) — two minutes.
- **Integrate your platform.** [Sidecar guide](/docs/getting-started/integrate-platform).
- **Shape the spec.** [GitHub Discussions](https://github.com/pelles-ai/taco/discussions) for proposals, [Issues](https://github.com/pelles-ai/taco/issues) for concrete asks.
- **Contribute.** [Contributing guide](https://github.com/pelles-ai/taco/blob/main/CONTRIBUTING.md).
