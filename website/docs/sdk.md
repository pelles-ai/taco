---
sidebar_position: 6
title: SDK Reference
---

# SDK Reference

The TACO Python SDK provides models, a server framework, a client, and an agent registry for building A2A-compatible construction agents.

## Installation

```bash
# Core models and schemas
pip install taco-agent

# With server support (FastAPI-based A2A server)
pip install taco-agent[server]

# With client support (async HTTP client)
pip install taco-agent[client]

# Everything (server + client + CLI)
pip install taco-agent[all]
```

## Modules

| Module | Description |
|--------|-------------|
| `taco.types` | Pydantic v2 models for A2A protocol types (AgentCard, Task, Message, Part, etc.) and construction domain types |
| `taco.schemas` | Construction data schema models (BOMV1, RFIV1, EstimateV1, QuoteV1, ScheduleV1, ChangeOrderV1) |
| `taco.server` | A2AServer — FastAPI-based server with JSON-RPC routing, streaming, and task store |
| `taco.client` | TacoClient — async HTTP client for agent discovery, task submission, and streaming |
| `taco.agent_card` | ConstructionAgentCard and ConstructionSkill convenience classes |
| `taco.registry` | AgentRegistry — in-memory agent discovery with filtering by trade, task type, CSI division |
| `taco.agent` | TacoAgent — bidirectional agent that combines server, client pool, and registry |
| `taco.monitor` | Agent Monitor — opt-in live tracing UI for A2A communications |
| `taco.cli` | Command-line tool for interacting with agents (see [CLI Reference](/docs/cli)) |

## A2AServer

The server handles inbound A2A requests: Agent Card discovery, JSON-RPC dispatch, task lifecycle, health checks, and optional admin/monitor endpoints.

### Constructor

```python
from taco import A2AServer

server = A2AServer(
    agent_card,                     # AgentCard (from card.to_a2a())
    task_store=None,                # TaskStore (default: InMemoryTaskStore)
    cors_origins=["*"],             # CORS allowed origins (default: None = no CORS)
    enable_admin=False,             # Enable /admin/skills endpoints
    admin_auth_token="secret",      # Protect admin endpoints with Bearer token
    enable_monitor=False,           # Enable /monitor live tracing UI
)
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/.well-known/agent.json` | Agent Card (with `x-construction`) |
| `POST` | `/` | JSON-RPC 2.0 dispatch (`message/send`, `message/stream`, `tasks/get`, `tasks/cancel`) |
| `GET` | `/health` | Health check (status, version, uptime, registered handlers) |

### Handler registration

Handlers process incoming tasks. The server routes to the right handler based on `metadata.taskType` in the JSON-RPC request.

```python
from taco import Artifact, Task, make_artifact, make_data_part

async def handle_estimate(task: Task, input_data: dict) -> Artifact:
    result = await do_estimation(input_data)
    return make_artifact(
        parts=[make_data_part(result)],
        name="estimate-result",
    )

server.register_handler("estimate", handle_estimate)
```

**Handler signature:** `async def handler(task: Task, input_data: dict) -> Artifact`

- `task` — the current Task object (includes `id`, `context_id`, `metadata`)
- `input_data` — structured data extracted from the first `DataPart` in the message (empty dict if no DataPart)
- Return an `Artifact` with your results

**What happens on errors:** If your handler raises an exception, the server catches it, logs the traceback, and transitions the task to `failed` with the error message. The server itself does not crash — other requests continue to be processed normally.

### Streaming handlers

For long-running tasks, yield partial results as the handler runs:

```python
from collections.abc import AsyncIterator
from taco import Part, make_text_part, make_data_part

async def stream_estimate(task: Task, input_data: dict) -> AsyncIterator[Part]:
    yield make_text_part("Analyzing BOM...")
    # ... do work ...
    yield make_text_part("Calculating costs...")
    # ... do work ...
    yield make_data_part(final_result)

server.register_streaming_handler("estimate", stream_estimate)
```

Clients receive each yielded part as an SSE event via `message/stream`. After the handler completes, the server sends a final `completed` event with all parts collected into a single artifact.

### CORS configuration

By default, CORS is not enabled. If your agent serves a browser-based dashboard or is called from a frontend, set `cors_origins`:

```python
server = A2AServer(card.to_a2a(), cors_origins=["*"])
# or restrict to specific origins:
server = A2AServer(card.to_a2a(), cors_origins=["http://localhost:3000"])
```

### Admin API

Enable dynamic skill registration at runtime with `enable_admin=True`:

```python
server = A2AServer(
    card.to_a2a(),
    enable_admin=True,
    admin_auth_token="my-secret-token",  # Optional but recommended
)
```

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/skills` | Add a skill (JSON body with skill fields) |
| `DELETE` | `/admin/skills/{skill_id}` | Remove a skill by ID |
| `GET` | `/admin/skills` | List current skills |

If `admin_auth_token` is set, requests must include `Authorization: Bearer <token>`.

```bash
curl -X POST http://localhost:8001/admin/skills \
  -H "Authorization: Bearer my-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "value-engineering",
    "name": "Value Engineering Analysis",
    "description": "Identifies cost reduction opportunities",
    "x-construction": {
      "taskType": "value-engineering",
      "inputSchema": "bom-v1",
      "outputSchema": "ve-suggestions-v1"
    }
  }'
```

### Task persistence

By default, `A2AServer` stores tasks in memory using `InMemoryTaskStore`. Tasks are lost when the process restarts.

For durable storage, pass a `task_store` to the constructor:

```python
from taco import A2AServer, JsonFileTaskStore

store = JsonFileTaskStore("tasks.json")
server = A2AServer(card.to_a2a(), task_store=store, enable_monitor=True)
```

`JsonFileTaskStore` persists all tasks to a local JSON file. Tasks survive restarts and are loaded back automatically on startup.

For multi-process or production deployments, implement the `TaskStore` protocol with your own backend (e.g., PostgreSQL, Redis):

```python
from taco.types import TaskStore

class DatabaseTaskStore(TaskStore):
    async def get(self, task_id: str) -> Task | None: ...
    async def save(self, task: Task) -> None: ...
    async def delete(self, task_id: str) -> None: ...
```

---

## TacoClient

Async HTTP client for sending tasks to TACO agents. Requires `pip install taco-agent[client]`.

### Constructor

```python
from taco import TacoClient

async with TacoClient(agent_url="http://localhost:8001") as client:
    ...
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `agent_url` | (required) | Agent base URL |
| `timeout` | `120.0` | HTTP timeout in seconds |
| `http_client` | `None` | Optional shared `httpx.AsyncClient` |

The client is an async context manager. If you create it without `async with`, call `await client.close()` when done.

### Methods

#### `discover() → AgentCard`

Fetch and cache the agent's Agent Card:

```python
card = await client.discover()
print(card.name, card.x_construction.trade)
```

#### `send_message(task_type, input_data, *, context_id=None, headers=None) → Task`

Send a task and wait for the result:

```python
task = await client.send_message("estimate", {"projectId": "PRJ-001", "lineItems": [...]})
data = extract_structured_data(task.artifacts[0].parts[0])
```

| Parameter | Description |
|-----------|-------------|
| `task_type` | Task type to send (matched to handler on the server) |
| `input_data` | Dict wrapped in a DataPart |
| `context_id` | Optional — group related messages into a conversation |
| `headers` | Optional — custom HTTP headers (e.g., `{"Authorization": "Bearer ..."}`) |

#### `stream_message(task_type, input_data, *, context_id=None, headers=None) → AsyncIterator[dict]`

Send a task and receive streaming SSE events:

```python
async for event in client.stream_message("estimate", bom_data):
    print(event["event"], event["data"])
    # event = {"event": "message", "data": {...}}
```

Each yielded dict has `event` (str) and `data` (parsed JSON).

#### `get_task(task_id) → Task`

Retrieve a task by ID (useful for checking status of long-running tasks):

```python
task = await client.get_task("task-abc-123")
print(task.status.state)  # TaskState.completed, TaskState.working, etc.
```

#### `cancel_task(task_id) → Task`

Cancel a running task:

```python
task = await client.cancel_task("task-abc-123")
print(task.status.state)  # TaskState.canceled
```

---

## TacoAgent

Bidirectional agent that combines `A2AServer` (inbound), `AgentRegistry` (peer discovery), and a `TacoClient` pool (outbound).

### Constructor

```python
from taco import TacoAgent, ConstructionAgentCard

agent = TacoAgent(
    card,                                    # ConstructionAgentCard
    task_store=None,                         # TaskStore (default: InMemoryTaskStore)
    peers=["http://localhost:8101"],          # Peer URLs or path to YAML/JSON file
    peer_retry_attempts=5,                   # Retries per peer at startup (default: 5)
    peer_retry_delay=2.0,                    # Seconds between retries (default: 2.0)
    cors_origins=["*"],                      # CORS allowed origins
    enable_monitor=True,                     # Enable /monitor UI
)
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `app` | FastAPI | The ASGI application (pass to uvicorn) |
| `agent_card` | `ConstructionAgentCard` | This agent's card |
| `server` | `A2AServer` | The underlying server |
| `registry` | `AgentRegistry | None` | Peer registry (None if no peers) |

### Peer communication

#### `send_to_peer(task_type, input_data, *, context_id=None, headers=None) → Task`

Send a task to whichever peer handles the given task type:

```python
async def my_handler(task, input_data):
    peer_task = await agent.send_to_peer("data-query", {"question": "How many items?"})
    peer_data = extract_structured_data(peer_task.artifacts[0].parts[0])
    ...
```

The agent looks up the peer by matching `task_type` against skill IDs in the registry.

Raises `ValueError` if no peers are configured or no peer has a matching skill.

#### `stream_from_peer(task_type, input_data, *, context_id=None, headers=None) → AsyncIterator[dict]`

Stream a task from a peer agent:

```python
async for event in agent.stream_from_peer("estimate", bom_data):
    print(event["event"], event["data"])
```

### Peer configuration

Peers can be specified as a list of URLs or a config file:

```python
# List of URLs
agent = TacoAgent(card, peers=["http://agent1:8001", "http://agent2:8002"])

# YAML file
agent = TacoAgent(card, peers="agents.yaml")

# JSON file
agent = TacoAgent(card, peers="agents.json")
```

**agents.yaml:**

```yaml
agents:
  - url: http://localhost:8101
  - url: http://localhost:8102
```

---

## AgentRegistry

In-memory registry for discovering and filtering agents by construction metadata.

```python
from taco import AgentRegistry

registry = AgentRegistry()
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `timeout` | `10.0` | HTTP timeout for fetching Agent Cards |
| `persistence_path` | `None` | Optional path to a JSON file — saves/loads registered agents across restarts |

### Methods

#### `register(url) → AgentCard`

Fetch an agent's card by URL and add it to the registry:

```python
card = await registry.register("http://localhost:8001")
```

#### `register_card(url, card)`

Register a card directly without fetching (useful for testing):

```python
registry.register_card("http://localhost:8001", my_card)
```

#### `find(trade=None, task_type=None, csi_division=None, project_type=None) → list[AgentCard]`

Find agents matching filters:

```python
agents = registry.find(trade="mechanical", task_type="estimate")
```

All filters are optional. Multiple filters are combined with AND logic.

#### `list_agents() → list[AgentCard]`

Return all registered agents:

```python
all_agents = registry.list_agents()
```

#### `remove(url)`

Remove an agent from the registry:

```python
registry.remove("http://localhost:8001")
```

#### `refresh(url) → AgentCard`

Re-fetch an agent's card (e.g., after it added new skills):

```python
updated_card = await registry.refresh("http://localhost:8001")
```

---

## Error Handling

### Client errors

The `TacoClient` raises specific exceptions depending on the failure type:

```python
from taco.client import TacoClientError, RpcError

try:
    task = await client.send_message("estimate", bom_data)
except RpcError as e:
    # Server returned a JSON-RPC error (e.g., no handler for task type)
    print(f"RPC error {e.code}: {e.rpc_message}")
    print(f"Error data: {e.data}")
except TacoClientError as e:
    # Base class for all TACO client errors
    print(f"Client error: {e}")
```

Additionally, `httpx` exceptions propagate for transport-level failures:

```python
import httpx

try:
    task = await client.send_message("estimate", bom_data)
except httpx.ConnectError:
    print("Could not connect to the agent")
except httpx.HTTPStatusError as e:
    print(f"HTTP error: {e.response.status_code}")
```

### Server-side error handling

When a handler raises an exception:

1. The server catches it and logs the full traceback
2. The task transitions to `failed` state
3. The error message is included in the task's status message
4. The server continues processing other requests normally

```python
async def handle_estimate(task, input_data):
    if "lineItems" not in input_data:
        raise ValueError("BOM must include lineItems")
    # This ValueError becomes a failed task, not a server crash
```

### TacoAgent errors

`send_to_peer` and `stream_from_peer` raise `ValueError` when:

- No peers are configured (`peers` was not passed to the constructor)
- No peer has a skill matching the requested `task_type`

---

## Helper Functions

The SDK exports helper functions for constructing and inspecting A2A types:

### Creating Parts

```python
from taco import make_text_part, make_data_part

text = make_text_part("Processing your request...")
data = make_data_part({"projectId": "PRJ-001", "lineItems": [...]})
```

### Creating Messages and Artifacts

```python
from taco import make_message, make_artifact

message = make_message("user", [data_part])           # Auto-generates message_id
artifact = make_artifact(
    parts=[data_part],
    name="estimate-result",
    description="Cost estimate for PRJ-001",
    metadata={"schema": "estimate-v1"},
)
```

### Extracting data from Parts

```python
from taco import extract_text, extract_structured_data

text = extract_text(part)           # Returns str or None if not a TextPart
data = extract_structured_data(part)  # Returns dict or None if not a DataPart
```

### Inspecting Messages

```python
from taco import get_text_parts, get_data_parts, get_file_parts, get_message_text

# Filter parts by type
text_parts = get_text_parts(message)    # List of TextPart
data_parts = get_data_parts(message)    # List of DataPart
file_parts = get_file_parts(message)    # List of FilePart

# Get concatenated text from all TextParts in a message
full_text = get_message_text(message)
```

### Creating agent response messages

```python
from taco import new_agent_text_message, new_agent_parts_message

# Quick text response
msg = new_agent_text_message("Here is your estimate.")

# Response with multiple parts
msg = new_agent_parts_message([text_part, data_part])
```

### Creating artifacts (shorthand)

```python
from taco import new_text_artifact, new_data_artifact

text_artifact = new_text_artifact("Summary of findings", name="summary")
data_artifact = new_data_artifact({"total": 45000}, name="estimate")
```

---

## Data Schema Models

All schemas use Pydantic v2 with snake_case Python attributes and camelCase JSON serialization:

```python
from taco import BOMV1, RFIV1, EstimateV1, QuoteV1, ScheduleV1, ChangeOrderV1

# Parse incoming JSON
bom = BOMV1.model_validate(json_payload)

# Access fields
print(bom.project_id)
print(bom.line_items[0].description)
print(bom.metadata.confidence)

# Serialize to JSON
json_output = bom.model_dump(by_alias=True, exclude_none=True)
```

---

## Agent Monitor

The monitor is an opt-in live tracing UI that shows all A2A traffic flowing through an agent. Enable it with one flag:

```python
# Via A2AServer
server = A2AServer(card.to_a2a(), enable_monitor=True)

# Via TacoAgent
agent = TacoAgent(card, enable_monitor=True)
```

The monitor UI is mounted at `/monitor` on the agent's existing port — no extra servers or ports needed. It includes:

- **Live dashboard** at `/monitor/` with real-time event timeline
- **WebSocket** at `/monitor/ws` for live event streaming
- **REST API** at `/monitor/api/events`, `/monitor/api/info`, `/monitor/api/clear`

Events are tagged with labels like `RECEIVED`, `REPLIED`, `CALLING`, `GOT REPLY`, `PROCESSING`, `COMPLETED`, `FAILED`, and `DISCOVERY` for clear traceability.

For explicit control, use the `enable_monitor()` function:

```python
from taco.monitor import enable_monitor

enable_monitor(server=server, client=client, registry=registry)
```

---

## Status

The SDK is in early development. The API surface is subject to change. Current capabilities:

- Full A2A protocol support (message/send, message/stream, tasks/get, tasks/cancel)
- Agent Card discovery at `/.well-known/agent.json`
- Multi-turn conversations via context IDs
- Pluggable task store (in-memory default, JSON file, or database-backed)
- Pydantic v2 models with full validation

See the [GitHub repository](https://github.com/pelles-ai/taco) for the latest.
