---
sidebar_position: 8
title: Examples
---

# Example Agents

The TACO repository includes three reference agents that demonstrate real construction workflows. Each is a fully functional A2A-compatible agent you can run locally or via Docker Compose.

## Estimating Agent

A mechanical estimating agent that generates cost estimates from bills of materials.

| Property | Value |
|----------|-------|
| **Trade** | multi-trade |
| **Task Type** | `estimate` |
| **Input Schema** | `bom-v1` |
| **Output Schema** | `estimate-v1` |

**Source:** [`examples/agents/estimating_agent.py`](https://github.com/pelles-ai/taco/blob/main/examples/agents/estimating_agent.py)

## RFI Generation Agent

Generates Requests for Information (RFIs) from bills of materials, flagging potential design conflicts and missing information.

| Property | Value |
|----------|-------|
| **Trade** | Mechanical |
| **Task Type** | `rfi-generation` |
| **Input Schema** | `bom-v1` |
| **Output Schema** | `rfi-v1` |

**Source:** [`examples/agents/rfi_generation_agent.py`](https://github.com/pelles-ai/taco/blob/main/examples/agents/rfi_generation_agent.py)

## Supplier Quote Agent

Generates supplier quotes from material requirements, returning pricing and availability.

| Property | Value |
|----------|-------|
| **Trade** | Mechanical |
| **Task Type** | `material-procurement` |
| **Input Schema** | `bom-v1` |
| **Output Schema** | `quote-v1` |

**Source:** [`examples/agents/supplier_quote_agent.py`](https://github.com/pelles-ai/taco/blob/main/examples/agents/supplier_quote_agent.py)

## Running with Docker Compose

All three agents can be started together using Docker Compose:

```bash
cd examples
docker compose up
```

This starts:
- **Estimating agent** on port 8001
- **Supplier quote agent** on port 8002
- **RFI generation agent** on port 8003

You can then discover and interact with them using the TACO CLI:

```bash
# Discover agents
taco discover http://localhost:8001

# Inspect an agent's capabilities
taco inspect http://localhost:8001

# Send a task
taco send http://localhost:8001 estimate

# Check health
taco health http://localhost:8001
```

**Docker Compose file:** [`examples/docker-compose.yml`](https://github.com/pelles-ai/taco/blob/main/examples/docker-compose.yml)

## Building Your Own

Ready to build a custom agent? See the [Build Your First Agent](/docs/getting-started/build-agent) guide for a step-by-step walkthrough.
