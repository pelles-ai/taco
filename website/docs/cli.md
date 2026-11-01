---
sidebar_position: 7
title: CLI Reference
description: The `taco` command — discover agents, inspect capabilities, send tasks, list tasks, and check health straight from the terminal.
---

# CLI Reference

The `taco` command-line tool lets you interact with TACO agents from the terminal — discover capabilities, send tasks, list tasks, and check health.

## Installation

The CLI is included with the TACO SDK:

```bash
pip install "taco-agent[client]"
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

Output: the full `/.well-known/agent-card.json` response, pretty-printed. If the agent answers that path with a 404, the CLI falls back to the legacy `/.well-known/agent.json`.

This is useful for debugging — you see exactly what the agent advertises, including `x-construction` extensions, skills, capabilities and security schemes.

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

Security:
  Scheme bearer: http
  Requires bearer: taco:task:estimate

Skills (1):
  - Generate Cost Estimate
    Generates detailed cost estimates from BOM data
    Task Type: estimate
    Input: bom-v1
    Output: estimate-v1
```

The `Security` section lists the card's `securitySchemes` and its `security` requirements; it is left out when the card declares none. Use this to quickly verify an agent is running and advertising the right capabilities.

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
- **json_file** (optional) — Path to a JSON file with input data. If omitted, reads from stdin. If stdin is a terminal or empty (as in many scripts and CI jobs), sends an empty object `{}`.

The input JSON is wrapped in a `DataPart` and sent as a `message/send` JSON-RPC call, with a fresh `messageId` and request id each time. The full response is printed as formatted JSON.

`taco send` exits with status 1 when the task ends `failed`, `rejected` or `canceled`, or when the agent returns a JSON-RPC error, so scripts can rely on the exit code. The response is still printed.

### `taco list-tasks`

List the tasks the agent holds for you, newest first, using the A2A v1 `ListTasks` method.

```bash
taco list-tasks http://localhost:8080
taco list-tasks http://localhost:8080 --limit 20 --context-id ctx-123
taco list-tasks http://localhost:8080 --limit 20 --cursor <cursor from the previous page>
taco list-tasks http://localhost:8080 --json
```

| Option | Description |
|--------|-------------|
| `--limit` | Page size (the server may apply its own cap) |
| `--cursor` | Continue from the `Next page cursor` the previous call printed |
| `--context-id` | Only tasks in this conversation context |
| `--json` | Print the raw JSON-RPC result instead of a table |

Example output:

```
2 task(s):
  - 4c493b05-3184-4f43-83f0-9ea2582e7032  state=TASK_STATE_COMPLETED  context=f6fc06b7-ff19-4c2f-a8b1-9ac6b9459444
  - b3e01296-c5ce-4978-9b72-93e2f1dde874  state=TASK_STATE_FAILED  context=ee77061e-81e8-4689-90f7-7fdfda69a7d6

Next page cursor: eyJ0cyI6bnVsbCwiaWQiOiJiM2UwMTI5Ni1jNWNlLTQ5NzgtOWI3Mi05M2UyZjFkZGU4NzQifQ
```

`ListTasks` is an A2A v1 method, so states print in the v1 form (`TASK_STATE_COMPLETED`). On an agent that requires a token, each caller sees only the tasks it created.

### `taco health`

Check an agent's health endpoint.

```bash
taco health http://localhost:8080
```

Example output:

```
Status: ok
Agent: My Mechanical Estimating Agent
Version: 0.3.21
Uptime: 142.5s
Handlers: echo, estimate
```

Use this to verify an agent is running and see which handlers are registered.

## Global options

Global options go before the command name.

| Option | Default | Description |
|--------|---------|-------------|
| `--timeout` | `30` | HTTP timeout in seconds |
| `--token` | — | Bearer token sent as `Authorization: Bearer <token>` by `send` and `list-tasks`, for agents that require auth |
| `--version` | — | Print the taco-agent version and exit |

```bash
# Use a longer timeout for slow agents
taco --timeout 60 send http://localhost:8080 estimate bom.json

# Call an agent that requires a token
taco --token "$TACO_TOKEN" send https://estimator.example.com estimate bom.json
taco --token "$TACO_TOKEN" list-tasks https://estimator.example.com
```

The agent card and `/health` are public, so `discover`, `inspect` and `health` send no token.

## Exit codes and errors

| Exit code | When |
|-----------|------|
| `0` | Success. For `send`, the task did not end `failed`, `rejected` or `canceled`. |
| `1` | `send`: the task ended `failed`, `rejected` or `canceled`, or the agent returned a JSON-RPC error. Any command: the agent answered with an HTTP error status, or could not be reached. `list-tasks`: the agent returned a JSON-RPC error. |

The CLI prints clean error messages for common failures:

```bash
# Agent not running
$ taco health http://localhost:9999
Error: could not connect to server — ...

# Agent requires a token and none (or a bad one) was sent
$ taco send https://estimator.example.com estimate bom.json
Error: HTTP 401 from server
```

An unknown task type is not an HTTP error. The agent returns HTTP 200 with a task in the `failed` state, and its status message says `No handler for task type: <type>`. `taco send` prints that response and exits 1:

```bash
$ taco send http://localhost:8080 unknown-task
{
  "id": "...",
  "jsonrpc": "2.0",
  "result": {
    ...
    "status": {
      "message": {
        "kind": "message",
        "parts": [{"kind": "text", "text": "No handler for task type: unknown-task"}],
        "role": "agent",
        ...
      },
      "state": "failed"
    }
  }
}
$ echo $?
1
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

**Fail a CI step when a task fails:**

```bash
taco send http://localhost:8001 estimate fixtures/bom.json > result.json || {
  echo "estimate task failed"; jq '.result.status' result.json; exit 1;
}
```

**Check all sandbox demo agents:**

```bash
for port in 8001 8002 8003; do
  echo "=== Port $port ==="
  taco inspect http://localhost:$port
  echo
done
```
