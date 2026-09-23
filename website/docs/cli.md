---
sidebar_position: 7
title: CLI Reference
description: The `taco` command — discover agents, inspect capabilities, send tasks, and check health straight from the terminal.
---

# CLI Reference

The `taco` command-line tool lets you interact with TACO agents from the terminal — discover capabilities, send tasks, and check health.

## Installation

The CLI is included with the TACO SDK:

```bash
pip install taco-agent[client]
```

Verify it's installed:

```bash
taco --version
```

## Commands

### `taco discover`

Fetch and print the raw Agent Card JSON from an agent.

```bash
taco discover http://localhost:8080
```

Output: the full `/.well-known/agent.json` response, pretty-printed.

This is useful for debugging — you see exactly what the agent advertises, including `x-construction` extensions, skills, and capabilities.

### `taco inspect`

Pretty-print an agent's details in a human-readable format.

```bash
taco inspect http://localhost:8080
```

Example output:

```
Agent: My Mechanical Estimating Agent
Description: Generates cost estimates from BOMs
URL: http://localhost:8080
Version: 1.0.0

Construction Extension:
  Trade: mechanical
  CSI Divisions: 22, 23

Skills (1):
  - Generate Cost Estimate
    Generates detailed cost estimates from BOM data
    Task Type: estimate
    Input: bom-v1
    Output: estimate-v1
```

Use this to quickly verify an agent is running and advertising the right capabilities.

### `taco send`

Send a task to an agent and print the JSON-RPC response.

```bash
# Send with a JSON file
taco send http://localhost:8080 estimate bom.json

# Send with data piped from stdin
echo '{"projectId": "PRJ-001", "lineItems": []}' | taco send http://localhost:8080 estimate

# Send with no input data (empty object)
taco send http://localhost:8080 echo
```

Arguments:
- **url** — Agent base URL
- **task_type** — The task type to send (must match a registered handler)
- **json_file** (optional) — Path to a JSON file with input data. If omitted, reads from stdin. If stdin is a terminal, sends an empty object `{}`.

The input JSON is wrapped in a `DataPart` and sent as a `message/send` JSON-RPC call. The full response is printed as formatted JSON.

### `taco health`

Check an agent's health endpoint.

```bash
taco health http://localhost:8080
```

Example output:

```
Status: ok
Agent: My Mechanical Estimating Agent
Version: 0.2.7
Uptime: 142.5s
Handlers: echo, estimate
```

Use this to verify an agent is running and see which handlers are registered.

## Global options

| Option | Default | Description |
|--------|---------|-------------|
| `--timeout` | `30` | HTTP timeout in seconds |
| `--version` | — | Print the taco-agent version and exit |

```bash
# Use a longer timeout for slow agents
taco --timeout 60 send http://localhost:8080 estimate bom.json
```

## Error handling

The CLI prints clean error messages for common failures:

```bash
# Agent not running
$ taco health http://localhost:9999
Error: could not connect to server — ...

# Server returned an error
$ taco send http://localhost:8080 unknown-task
Error: HTTP 400 from server
```

## Examples

**Verify an agent after starting it:**

```bash
python my_agent.py &
taco health http://localhost:8080
taco inspect http://localhost:8080
```

**Send a task and pipe the result to jq:**

```bash
taco send http://localhost:8001 estimate bom.json | jq '.result.artifacts[0]'
```

**Check all sandbox demo agents:**

```bash
for port in 8001 8002 8003; do
  echo "=== Port $port ==="
  taco inspect http://localhost:$port
  echo
done
```
