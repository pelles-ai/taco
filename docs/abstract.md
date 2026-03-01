# Construction A2A Interoperability Protocol (CAIP)

**An open standard for AI agent communication in the built environment**

---

## The Problem

Construction runs on fragmented systems. A typical project involves dozens of companies, each with their own tools, formats, and workflows. AI agents are now entering this ecosystem — generating takeoffs, drafting RFIs, coordinating schedules, managing procurement — but they're being built in isolation, just like the tools before them. An electrical takeoff agent can't hand its output to a scheduling agent. A GC's orchestration layer can't discover or delegate to a sub's estimating agent. We are recreating the same fragmentation problem — this time with AI.

## Why Now

Three things have converged to make this the right moment:

1. **AI agents in construction are no longer experimental.** The AI-in-construction market is projected to grow from $4.9B to $22.7B by 2032 (Fortune Business Insights, 2024). Procore, Autodesk, and dozens of startups are shipping agent capabilities today. These agents are already delivering real value — automated document review, smarter scheduling, streamlined procurement — but each one operates in its own silo.

2. **The value ceiling is the silo itself.** Individual agents can optimize a single task. But construction projects aren't single tasks — they're long, interdependent chains of decisions that span companies, trades, and platforms. The next step-change in productivity comes not from better individual agents, but from agents that can hand off work to each other seamlessly.

3. **The industry is demanding interoperability.** Industry surveys consistently rank data integration and system interoperability among the top technology priorities for construction professionals. Fragmented systems remain the single biggest barrier to AI adoption on jobsites. The workforce is ready for connected AI — the connective tissue just doesn't exist yet.

The window is open. Standards are set by those who show up first.

## What CAIP Does

CAIP is a construction-specific extension to the A2A protocol. It defines three things:

**A common vocabulary of agent capabilities.** A typed set of construction task types — takeoff, estimate, rfi-generation, submittal-review, schedule-coordination, material-procurement, clash-detection, and others — organized by project phase. When an agent advertises a skill, every other agent in the ecosystem knows exactly what it means.

**Standardized data schemas for construction artifacts.** Typed JSON schemas for the outputs that agents exchange: bills of materials, RFIs, schedules, estimates, change orders, and more. These schemas include construction-specific fields — CSI divisions, spec sections, sheet references, location codes, trade identifiers — so that the output of one agent is valid, parseable input for the next.

**Construction-aware agent discovery.** Extensions to the A2A Agent Card that let agents describe themselves in terms the industry understands: which trades they serve, which CSI divisions they cover, which project types they support, which file formats they accept, and which platforms they integrate with. A GC's orchestrator can query: "find me a mechanical scheduling agent that covers Division 23 and works with Procore" — and get a machine-readable answer.

## What CAIP Does Not Do

CAIP does not prescribe how agents work internally. It does not require any specific AI model, framework, or platform. An agent built with LangChain, CrewAI, a custom pipeline, or no AI at all can participate — it just needs to speak the protocol. Agents remain opaque to each other, preserving proprietary logic, pricing models, and trade secrets. This is a communication standard, not an implementation standard.

CAIP is an ontology layer, not a protocol fork. It builds on the A2A protocol using its native extension points — every CAIP agent is a standard A2A agent. A generic A2A client can discover and communicate with a CAIP agent without knowing anything about construction; it simply sees a normal Agent Card with some additional fields it can safely ignore. There is zero lock-in. CAIP adds a shared vocabulary for the construction industry on top of infrastructure that already works.

## The Vision

A GC's orchestrator agent receives a set of construction documents. It discovers and delegates to specialized agents across trades: an estimating agent prices the BOM, a supplier's agent returns live quotes, a scheduling agent coordinates timelines with electrical and structural agents already working on the same project. When a document review agent flags a design conflict, it spawns an RFI task that routes to the architect's agent, pauses for human review, and resumes when the response arrives.

Every agent in this chain was built by a different company, runs on different infrastructure, and uses different AI models. They interoperate because they share a common language.

## How to Get Involved

CAIP is an open initiative. The specification, schemas, and SDK are open source. We're looking for construction technology companies, trade contractors, general contractors, and platform vendors who want to help shape the standard.

If your company is building AI capabilities for construction, or if your workflows would benefit from agents that can talk to each other, we'd like to hear from you.

---

*CAIP is initiated by Pelles and built on the A2A protocol (Linux Foundation). The project is open to contributors and governed by the community it serves.*
