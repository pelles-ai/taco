---
title: What TACO is and isn't
description: Sharp scoping — what TACO does, what it explicitly doesn't do, what we will keep saying no to, and what we punt to other tools. Read this if you're trying to figure out whether TACO is the right tool for your problem.
sidebar_position: 3
---

# What TACO is and isn't

A protocol that tries to do everything ends up being a worse version of the things it competes with. TACO has a deliberately narrow scope; this page makes that scope explicit so visitors don't have to infer it.

The shortest version: **TACO is a construction-specific ontology layer on top of the [A2A protocol](https://a2a-protocol.org). It defines what construction agents say to each other, not how they're built or how they reach their tools.**

## What TACO is

- **A shared vocabulary for construction agent communication.** 18 named task types, 6 typed JSON schemas, a construction extension on the standard A2A Agent Card.
- **A discovery model for construction agents.** Filter by trade, CSI division, task type, platform integration, trust tier.
- **A security model that respects construction's multi-organization reality.** Trade-, task-, project-, and CSI-scoped OAuth tokens; mandatory Token Exchange between agents from different organizations.
- **A reference Python SDK.** `taco-agent` on PyPI. Server, client, registry, CLI, monitor UI.
- **Apache 2.0, open governance.** Spec lives in [a public repo](https://github.com/pelles-ai/taco). Decisions go through Architecture Decision Records.

## What TACO isn't

- **Not a replacement for A2A.** TACO is built *on* A2A. Every TACO agent is a valid A2A agent. We don't fork or modify A2A.
- **Not an agent runtime.** TACO defines the protocol agents speak, not how they're implemented. Use any agent framework you want behind the TACO interface — LangChain, LlamaIndex, OpenAI Agents SDK, raw HTTP handlers, hard-coded business logic.
- **Not a competitor to MCP.** MCP connects an agent to its tools and data. A2A (and TACO on top) connects agents to each other. They're orthogonal. See [the protocol stack](./protocol-stack).
- **Not a construction platform.** We don't host projects, store documents, or run workflows ourselves. TACO is a wire protocol and a vocabulary; platforms run on top.
- **Not a file format.** TACO doesn't read or write IFC, BIM, DWG, COBie, or any other construction file format. Agents that consume those formats produce TACO-typed artifacts as output.
- **Not a contract-execution platform.** TACO's typed RFI, change order, and submittal artifacts represent workflow state. Whether they have legal force depends on AIA/ConsensusDocs forms and human signatures — TACO doesn't legislate that.
- **Not a managed service.** Today, the SDK is what we ship. A hosted public registry is [on the roadmap](./roadmap); a managed agent runtime is not, and won't be from us.

## What we will keep saying no to

Some asks come up repeatedly. We've thought hard about each and consistently land on "not in scope":

### "Add a `procore-v1` schema."

We don't model vendor APIs. `bom-v1` is the canonical BOM; if Procore (or any platform) shapes BOMs differently, the [sidecar pattern](./getting-started/integrate-platform) maps between the platform's shape and the canonical one. Adding vendor-specific schemas would fork the data model the moment we picked one vendor's idiom over another's.

### "Define how the LLM inside a takeoff agent should be prompted."

That's implementation, not protocol. TACO cares about the input and output shape of a `takeoff` task, not how the agent does the work. Two takeoff agents using completely different LLMs (or no LLM) are equally valid TACO citizens as long as their advertised inputs and outputs typecheck.

### "Add a UI layer / dashboard."

The reference SDK ships a [Monitor UI](./sdk-reference/server) for development tracing. We don't ship operator dashboards, project portals, or front-ends for end users. Those are platform concerns; building them is not TACO's job.

### "Add a $payment_processor / $signing_provider / $ML_platform integration."

Anything that's external to the protocol stack itself. We can model the *output* of that work as a typed TACO artifact, but the integration with the external service is an agent implementation detail.

### "Pick the One True $thing per category."

The One True Agent Framework. The One True Auth Server. The One True LLM. TACO works with whatever you use. Picking favorites would exclude the half of the ecosystem that uses the other thing.

## What TACO punts to other tools

For things TACO explicitly doesn't do, here's where we point people:

| What you need | Use |
|------|---------------------|
| Tool access for LLM agents | [MCP](https://modelcontextprotocol.io) |
| Generic agent runtime | LangChain, LlamaIndex, OpenAI Agents SDK, custom |
| Construction file parsing (IFC, DWG, COBie) | buildingSMART tools, Autodesk Forge, your existing tooling |
| Contract / legal execution | AIA / ConsensusDocs forms, e-signature platforms |
| BIM coordination | Navisworks, Revizto, Solibri |
| Hosted project storage | Procore, ACC, Bluebeam Studio, your existing platform |
| Identity provider | Auth0, Okta, Keycloak, your existing IdP |
| Observability backend | Datadog, Grafana, Honeycomb, OpenTelemetry collectors |

## When TACO is the right answer

You'll get value from TACO if you're doing **at least one** of these:

- Building a new construction agent that other people's tools should be able to discover and call
- Wrapping an existing construction platform so it participates in agent-driven workflows
- Orchestrating multiple agents across organizational boundaries (GC ↔ sub ↔ supplier; owner ↔ GC ↔ designer)
- Producing typed artifacts (BOMs, RFIs, estimates) that need to survive whatever platform you happen to be using this year
- Establishing a vendor-independent project record across a multi-year build

## When TACO is the wrong answer

You probably *don't* need TACO if:

- You're outside the construction / built-environment domain. Use [A2A](https://a2a-protocol.org) directly.
- You have exactly one platform and no plans for multi-vendor interop. Use the vendor's SDK.
- Your "agents" are all in one process and there's no inter-organizational boundary. You don't need a protocol; you need function calls.
- The thing you want to standardize is *human* workflow, not *agent* workflow. That's a project management problem, not a protocol problem.

If any of these are you, save yourself the protocol overhead. TACO is what it is precisely because we said no to a lot of things; that means it's not the right tool for problems it wasn't designed for.

## See also

- [Why TACO?](./why-taco) — the longer-form argument
- [Compare to alternatives](./compare) — vs raw A2A, vs proprietary APIs, vs homegrown
- [Architecture Decision Records](./decisions/) — the *why* behind these scoping choices
