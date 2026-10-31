---
sidebar_position: 6
title: SDK Guide
description: How to use the TACO Python SDK — models, A2A server framework, async client, agent registry, and CLI for building construction agents.
---

# SDK Guide

The TACO Python SDK provides models, a server framework, a client, and an agent registry for building A2A-compatible construction agents.

:::tip Looking for per-symbol details?
This page is the high-level guide. For the full signature, docstring, and source link of every public class, method, and function, see the auto-generated [**SDK Reference**](./sdk-reference/).
:::

## Installation

To try the SDK before installing it, use the [playground](/playground), which runs `taco-agent` in your browser.

```bash
# Core models and schemas
pip install taco-agent

# With server support (FastAPI-based A2A server, plus uvicorn to run it)
pip install "taco-agent[server]"

# With client support (async HTTP client and the taco CLI)
pip install "taco-agent[client]"

# Everything (server + client + uvicorn)
pip install "taco-agent[all]"
```

Quote the extras: unquoted brackets are a glob pattern in zsh, which then fails with `no matches found`.

## Modules

| Module | Description |
|--------|-------------|
| `taco.types` | Pydantic v2 models for A2A protocol types (AgentCard, Task, Message, Part, etc.) and construction domain types |
| `taco.schemas` | Construction data schema models (BOMV1, RFIV1, EstimateV1, QuoteV1, ScheduleV1, ChangeOrderV1) and the `SCHEMA_MODELS` lookup |
| `taco.server` | A2AServer — FastAPI-based server with JSON-RPC routing, streaming, and task store |
| `taco.auth` | Bearer-token authentication for the server: `AuthContext`, `current_auth()`, `task_scope()` |
| `taco.client` | TacoClient — async HTTP client for agent discovery, task submission, and streaming |
| `taco.agent_card` | ConstructionAgentCard and ConstructionSkill convenience classes |
| `taco.registry` | AgentRegistry — in-memory agent discovery with filtering by trade, task type, CSI division, project type and integration |
| `taco.agent` | TacoAgent — bidirectional agent that combines server, client pool, and registry |
| `taco.task_store` | JsonFileTaskStore — single-process task persistence in a JSON file |
| `taco.errors` | TacoTaskError — fail a task with a message the caller may see |
| `taco.monitor` | Agent Monitor — opt-in live tracing UI for A2A communications |
| `taco.cli` | Command-line tool for interacting with agents (see [CLI Reference](/docs/cli)) |

## A2AServer

The server handles inbound A2A requests: Agent Card discovery, JSON-RPC dispatch, task lifecycle, health checks, and optional authentication, admin and monitor endpoints.

### Constructor

```python
from taco import A2AServer

server = A2AServer(
    card,                           # ConstructionAgentCard, or the AgentCard from card.to_a2a()
    task_store=None,                # TaskStore (default: InMemoryTaskStore)
    push_config_store=None,         # Push config store (default: in-memory when the card enables push)
    cors_origins=None,              # CORS allowed origins (default: None = no CORS)
    enable_admin=False,             # Enable /admin/skills endpoints
    admin_auth_token=None,          # Protect admin endpoints with a Bearer token
    enable_monitor=False,           # Enable /monitor live tracing UI
    monitor_auth_token=None,        # Token the monitor requires (set it before exposing the port)
    token_verifier=None,            # async (token) -> AuthContext | None; turns on bearer auth
    require_task_scope=True,        # With token_verifier: require taco:task:<taskType>
    require_project_scope=None,     # Require taco:project:<projectId>:write (default: card's projectScoped)
)
```

`A2AServer` accepts a `ConstructionAgentCard` directly and converts it with `to_a2a()`, or an `AgentCard` you built yourself.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/.well-known/agent-card.json` | Agent Card (with `x-construction`) |
| `GET` | `/.well-known/agent.json` | The same card on the legacy path, for older A2A clients |
| `POST` | `/` | JSON-RPC 2.0 dispatch (`message/send`, `message/stream`, `tasks/get`, `tasks/cancel`, `ListTasks`, `tasks/pushNotificationConfig/*`) |
| `GET` | `/health` | Health check (status, version, uptime, registered handlers) |
| `GET` | `/monitor/` | Live tracing UI, when `enable_monitor=True` |
| `GET`, `POST`, `DELETE` | `/admin/skills` | Skill administration, when `enable_admin=True` |

If the card's `url` is empty, the served card uses the address the request reached (for example `http://localhost:8080`), so standard A2A clients can still reach the agent. Set `url` to the agent's public address when it runs behind a proxy.

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

- `task` — the current Task object (includes `id`, `context_id`, and `metadata`, which carries the `taskType`)
- `input_data` — structured data extracted from the first `DataPart` in the message (empty dict if no DataPart). Whole numbers arrive as `int`, so `range(input_data["count"])` works.
- Return an `Artifact` with your results

If `metadata.taskType` is missing and the agent has exactly one handler, that handler runs. A task type with no handler does not raise a JSON-RPC error: the response is HTTP 200 with a task in the `failed` state whose status message reads `No handler for task type: <type>`.

### Task lifecycle

The server reports the task as `working` before your handler runs, then `completed` (with the artifact) or `failed`. Because the `working` event comes first:

- a caller that sends with `return_immediately=True` gets the task back straight away, in the `working` state, and polls with `get_task` (or watches push notifications or the monitor);
- `tasks/cancel` stops a handler that is still running and the task stays `canceled`.

### Errors in handlers

If your handler raises, the task ends `failed` and the server keeps serving other requests. What the caller sees depends on the exception:

- `taco.TacoTaskError("...")` — the caller sees your message as the task's status message. Use it for expected, caller-facing problems.
- Any other exception — the caller sees only `Task handler failed for type '<taskType>' (error id <id>)`. The full traceback is logged on the `taco.server` logger under that error id, so connection strings, file paths and upstream API errors never reach another company's agent.

```python
from taco import TacoTaskError

async def handle_estimate(task, input_data):
    if not input_data.get("lineItems"):
        raise TacoTaskError("bom-v1 input has no lineItems")  # the caller sees this
    rows = await db.fetch_prices(input_data)  # a failure here is logged, not sent
    ...
```

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

Register streaming handlers after constructing the server, as above; registering one sets `capabilities.streaming` on the served card. Clients receive a `working` task event, then an artifact-update event for each part as it is yielded, via `message/stream`. When the handler finishes, the server sends one more artifact-update, an artifact named `<taskType>-stream-result` that holds all the parts, then a `completed` status update.

When a task type has both a regular and a streaming handler, `message/stream` requests use the streaming handler and `message/send` requests use the regular one. With only a streaming handler, `message/send` runs it and returns the finished task; read the parts from its `<taskType>-stream-result` artifact.

If you run the agent behind a proxy, turn off response buffering for it (nginx: `proxy_buffering off`), or events arrive all at once at the end.

### CORS configuration

By default, CORS is not enabled. If your agent serves a browser-based dashboard or is called from a frontend, set `cors_origins`:

```python
server = A2AServer(card.to_a2a(), cors_origins=["http://localhost:3000"])
# or allow any origin (this also lets any web page call your task endpoint):
server = A2AServer(card.to_a2a(), cors_origins=["*"])
```

### Authentication

Pass a `token_verifier` to require a bearer token on the JSON-RPC endpoint. The verifier is an async function that takes the token and returns an `AuthContext`, or `None` to reject it:

```python
from taco import A2AServer, AuthContext

async def verify(token: str) -> AuthContext | None:
    claims = await my_idp.introspect(token)  # your JWT check or introspection call
    if not claims.get("active"):
        return None
    return AuthContext(
        subject=claims["sub"],
        scopes=frozenset(claims["scope"].split()),
        claims=claims,
    )

server = A2AServer(card, token_verifier=verify)
```

Requests without a valid token get HTTP 401; with `require_task_scope=True` (the default), a token without `taco:task:<taskType>` for the requested task gets HTTP 403. The card, `/health` and the monitor stay public (the monitor has its own token). Each caller's `subject` owns the tasks it creates, so callers only see and cancel their own tasks. Inside a handler, `taco.current_auth()` returns the caller's `AuthContext`.

Declare the scheme on the card so callers know to send a token. See [Security: implementing it with the SDK](/docs/security#implementing-it-with-the-sdk) for the full setup, including project-scoped checks.

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

For durable storage on a single process, pass a `JsonFileTaskStore`:

```python
from taco import A2AServer, JsonFileTaskStore

store = JsonFileTaskStore("tasks.json")
server = A2AServer(card.to_a2a(), task_store=store)
```

`JsonFileTaskStore` writes every task to a local JSON file atomically and loads it back on startup. Like the in-memory store, it keeps tasks per owner (the authenticated caller), so one caller cannot read, list or cancel another's, and `ListTasks` honours its context filter, status filter and paging. Files written by earlier releases (a flat map of tasks, before file format version 2) load as belonging to the unauthenticated owner.

For multi-process or production deployments, use the a2a-sdk's `DatabaseTaskStore`, which takes an SQLAlchemy async engine (install `"a2a-sdk[postgresql]"`, `[mysql]` or `[sqlite]`):

```python
from a2a.server.tasks import DatabaseTaskStore
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine("postgresql+asyncpg://taco:secret@db/taco")
server = A2AServer(card, task_store=DatabaseTaskStore(engine))
```

To write your own backend, subclass `taco.TaskStore` (the a2a-sdk's `TaskStore`). Its four methods all take the request's `ServerCallContext`, and tasks arrive as the a2a-sdk's protobuf `Task`, not `taco.Task`:

```python
from a2a.server.context import ServerCallContext
from a2a.types.a2a_pb2 import ListTasksRequest, ListTasksResponse
from a2a.types.a2a_pb2 import Task as TaskPb
from taco import TaskStore


class RedisTaskStore(TaskStore):
    async def save(self, task: TaskPb, context: ServerCallContext) -> None: ...

    async def get(self, task_id: str, context: ServerCallContext) -> TaskPb | None: ...

    async def delete(self, task_id: str, context: ServerCallContext) -> None: ...

    async def list(
        self, params: ListTasksRequest, context: ServerCallContext
    ) -> ListTasksResponse: ...
```

Keep tasks per owner (`a2a.server.owner_resolver.resolve_user_scope(context)`) so callers stay isolated, and apply the `ListTasks` filters and paging. [`JsonFileTaskStore`](https://github.com/pelles-ai/taco/blob/main/sdk/taco/task_store.py) is a short reference implementation.

---

## TacoClient

Async HTTP client for sending tasks to TACO agents. Requires `pip install "taco-agent[client]"`.

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
| `headers` | `None` | Headers sent on every request, for example `{"Authorization": "Bearer ..."}`. Per-call `headers=` are merged on top. |

The client is an async context manager. If you create it without `async with`, call `await client.close()` when done.

### Methods

#### `discover() → AgentCard`

Fetch and cache the agent's Agent Card from `/.well-known/agent-card.json` (falling back to the legacy `/.well-known/agent.json` on a 404):

```python
card = await client.discover()
print(card.name, card.x_construction.trade)
```

#### `send_message(task_type, input_data, *, context_id=None, reference_task_ids=None, return_immediately=False, headers=None) → Task`

Send a task and wait for the result:

```python
task = await client.send_message("estimate", {"projectId": "PRJ-001", "lineItems": [...]})
data = extract_structured_data(task.artifacts[0].parts[0])
```

| Parameter | Description |
|-----------|-------------|
| `task_type` | Task type to send (matched to handler on the server) |
| `input_data` | Dict wrapped in a DataPart |
| `context_id` | Optional — put the task in an existing conversation. It is set on the message, and the returned task carries the same `context_id`. |
| `reference_task_ids` | Optional — earlier tasks this one follows up on (A2A v1), such as the RFI an RFI response answers |
| `return_immediately` | Optional — return as soon as the agent accepts the task (in the `working` state) instead of waiting for it to finish |
| `headers` | Optional — extra HTTP headers for this call |

A task the agent could not handle comes back in the `failed` state rather than as an exception, so check `task.status.state`. If an agent that is not a TACO agent replies with a plain A2A `Message` instead of a `Task`, `send_message` raises `MessageReplyError`; the message is on its `.reply` attribute.

#### `stream_message(task_type, input_data, *, context_id=None, reference_task_ids=None, headers=None) → AsyncIterator[dict]`

Send a task and receive streaming SSE events:

```python
async for event in client.stream_message("estimate", bom_data):
    result = event["data"]["result"]
    print(result["kind"])  # "task", "artifact-update", "status-update"
```

Each yielded dict has `event` (str) and `data` (the parsed JSON-RPC response), with whole numbers restored to `int`.

#### `get_task(task_id, *, headers=None) → Task`

Retrieve a task by ID (useful for checking status of long-running tasks):

```python
task = await client.get_task("task-abc-123")
print(task.status.state)  # TaskState.completed, TaskState.working, etc.
```

#### `cancel_task(task_id, *, headers=None) → Task`

Cancel a running task. The agent stops the handler and the task stays `canceled`:

```python
task = await client.cancel_task("task-abc-123")
print(task.status.state)  # TaskState.canceled
```

#### `list_tasks(*, cursor=None, limit=None, context_id=None, include_artifacts=False, headers=None) → (list[Task], str | None)`

List the tasks this caller can see, newest first, with the A2A v1 `ListTasks` method. Pass the returned cursor back to get the next page; `None` means there are no more. `ListTasks` leaves artifacts out unless you pass `include_artifacts=True`:

```python
tasks, cursor = await client.list_tasks(limit=20, context_id="ctx-123", include_artifacts=True)
```

The client also manages push notification configs (`create_push_config`, `list_push_configs`, `get_push_config`, `delete_push_config`); see the [SDK Reference](/docs/sdk-reference/client).

---

## TacoAgent

Bidirectional agent that combines `A2AServer` (inbound), `AgentRegistry` (peer discovery), and a `TacoClient` pool (outbound).

### Constructor

```python
from taco import TacoAgent, ConstructionAgentCard

agent = TacoAgent(
    card,                                    # ConstructionAgentCard
    task_store=None,                         # TaskStore (default: InMemoryTaskStore)
    peers=["http://localhost:8101"],         # Peer URLs or path to YAML/JSON file
    peer_retry_attempts=5,                   # Background discovery attempts per peer (default: 5)
    peer_retry_delay=2.0,                    # Seconds between attempts (default: 2.0)
    peer_startup_wait=2.0,                   # Max seconds startup waits for discovery (default: 2.0)
    cors_origins=None,                       # CORS allowed origins
    enable_monitor=True,                     # Enable /monitor UI
    monitor_auth_token=None,                 # Token the monitor requires
    token_verifier=None,                     # Require bearer tokens on inbound tasks
    require_task_scope=True,                 # With token_verifier: require taco:task:<taskType>
)
```

`token_verifier` protects inbound requests exactly as on `A2AServer`. Outbound peer calls carry their own credentials (`send_to_peer(..., headers=...)`); never forward the caller's token.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `app` | FastAPI | The ASGI application (pass to uvicorn) |
| `agent_card` | `ConstructionAgentCard` | This agent's card |
| `server` | `A2AServer` | The underlying server |
| `registry` | `AgentRegistry | None` | Peer registry (None if no peers) |

### Peer discovery

When the app starts, `TacoAgent` fetches each peer's Agent Card in the background. Startup waits at most `peer_startup_wait` seconds for the first round and then begins serving, so agents can start in any order, and two agents that list each other as peers do not wait on each other. Each peer that is not reachable yet is retried `peer_retry_attempts` times, `peer_retry_delay` seconds apart; a peer still missing after that is tried once more when `send_to_peer` needs it.

### Peer communication

#### `send_to_peer(task_type, input_data, *, context_id=None, reference_task_ids=None, return_immediately=False, headers=None) → Task`

Send a task to whichever peer handles the given task type:

```python
async def my_handler(task, input_data):
    peer_task = await agent.send_to_peer("data-query", {"question": "How many items?"})
    peer_data = extract_structured_data(peer_task.artifacts[0].parts[0])
    ...
```

The agent picks the first discovered peer with a skill whose `x-construction.taskType`, `id` or `tags` match `task_type`. It sends the request to the URL the peer was discovered at (the one in your `peers` list), never to the `url` the peer's card declares, which may be empty, a container-internal `localhost`, or any host the card's author chooses.

Raises `ValueError` if no peers are configured or no peer has a matching skill.

#### `stream_from_peer(task_type, input_data, *, context_id=None, reference_task_ids=None, headers=None) → AsyncIterator[dict]`

Stream a task from a peer agent:

```python
async for event in agent.stream_from_peer("estimate", bom_data):
    print(event["event"], event["data"])
```

Use `headers` to authenticate to a peer with a token your agent obtained for it. Do not forward the token your own caller sent; see [Token delegation](/docs/security#token-delegation).

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

#### `find(*, trade=None, task_type=None, csi_division=None, project_type=None, integration=None) → list[AgentCard]`

Find agents matching filters:

```python
agents = registry.find(trade="mechanical", task_type="estimate")
procore_agents = registry.find(integration="procore")
```

All filters are optional. Multiple filters are combined with AND logic. `task_type` matches a skill's `x-construction.taskType`.

#### `entries() → list[tuple[str, AgentCard]]`

Return `(url, card)` pairs, where `url` is the address each agent was registered at. Send requests there rather than to the card's self-declared `url`:

```python
matches = registry.find(trade="mechanical", task_type="estimate")
url = next(url for url, card in registry.entries() if card is matches[0])

async with TacoClient(agent_url=url) as client:
    task = await client.send_message("estimate", bom_data)
```

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
from taco import MessageReplyError, RpcError, TacoClientError

try:
    task = await client.send_message("estimate", bom_data)
except RpcError as e:
    # The agent answered with a JSON-RPC error: an invalid request,
    # an unknown method, or a task id it does not know.
    print(f"RPC error {e.code}: {e.rpc_message}")
    print(f"Error data: {e.data}")
except MessageReplyError as e:
    # A non-TACO agent replied with a Message instead of a Task
    print(e.reply)
except TacoClientError as e:
    # Base class for all TACO client errors
    print(f"Client error: {e}")
```

A task the agent ran and could not finish is not an exception. An unknown task type, a handler that raised, or a canceled task all come back as a `Task` whose `status.state` is `failed` or `canceled`, with the reason in `task.status.message`:

```python
from taco import TaskState, get_message_text

task = await client.send_message("estimate", bom_data)
if task.status.state != TaskState.completed:
    reason = get_message_text(task.status.message) if task.status.message else ""
    print(f"Task {task.status.state.value}: {reason}")
```

Additionally, `httpx` exceptions propagate for transport-level failures, including HTTP 401 and 403 from an agent that requires a token:

```python
import httpx

try:
    task = await client.send_message("estimate", bom_data)
except httpx.ConnectError:
    print("Could not connect to the agent")
except httpx.HTTPStatusError as e:
    print(f"HTTP error: {e.response.status_code}")  # 401: no or bad token, 403: missing scope
```

### Server-side error handling

When a handler raises an exception:

1. The server catches it; the other requests carry on normally
2. The task transitions to the `failed` state
3. For a `TacoTaskError`, the status message is the exception's message. For anything else it is `Task handler failed for type '<taskType>' (error id <id>)`, and the traceback is logged under that id.

```python
from taco import TacoTaskError

async def handle_estimate(task, input_data):
    if "lineItems" not in input_data:
        raise TacoTaskError("BOM must include lineItems")
    # A TacoTaskError becomes a failed task with this message, not a server crash
```

### TacoAgent errors

`send_to_peer` and `stream_from_peer` raise `ValueError` when:

- No peers are configured (`peers` was not passed to the constructor)
- No peer has a skill matching the requested `task_type`, even after retrying peers that were not discovered yet

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

A2A v1 carries data parts as protobuf `Struct` values, which store every number as a float. The SDK undoes that everywhere it can: TACO servers send whole numbers as JSON integers, handler `input_data`, `extract_structured_data` and `get_data_parts` return `int`s, and `TacoClient` restores integers in what it receives. `{"count": 3}` reads back as `3`, not `3.0`. For data from elsewhere (a non-TACO A2A v1 agent, a protobuf object you converted yourself), `taco.restore_integers(value)` converts any dict or list the same way.

### Inspecting Messages

These take a list of parts, such as `message.parts` or `artifact.parts`:

```python
from taco import get_text_parts, get_data_parts, get_file_parts, get_message_text

# Filter parts by type
texts = get_text_parts(message.parts)   # list[str], the text of each TextPart
datas = get_data_parts(message.parts)   # list[dict], the data of each DataPart
files = get_file_parts(message.parts)   # list[FilePart]

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

The arguments are keyword-only:

```python
from taco import new_text_artifact, new_data_artifact

text_artifact = new_text_artifact(name="summary", text="Summary of findings")
data_artifact = new_data_artifact(name="estimate", data={"total": 45000})
```

---

## Data Schema Models

All schemas use Pydantic v2 with snake_case Python attributes and camelCase JSON serialization. The JSON Schemas in [`spec/schemas`](https://github.com/pelles-ai/taco/tree/main/spec/schemas) are the source of truth, and a parity test in the SDK keeps the models in step with them.

```python
from taco import BOMV1, RFIV1, EstimateV1, QuoteV1, ScheduleV1, ChangeOrderV1

# Parse incoming JSON
bom = BOMV1.model_validate(json_payload)

# Access fields
print(bom.project_id)
print(bom.line_items[0].description)
print(bom.metadata.confidence)  # None when the producer did not set it

# Serialize to JSON
json_output = bom.model_dump(by_alias=True, exclude_none=True)
```

What the models check, and what they leave alone:

- **Required means required by the schema.** Optional fields default to `None`, and `model_dump(exclude_none=True)` leaves them out; the models never fill in a value the producer did not send.
- **Dates are RFC 3339.** Fields the schema marks `format: date` take `YYYY-MM-DD` (or a `datetime.date`). Fields marked `format: date-time` need a timezone offset: `"2026-05-24T15:00:00Z"` passes, `"2026-05-24T15:00:00"` is rejected, and a naive `datetime` is rejected too. Use `datetime.now(timezone.utc)`.
- **Enums and bounds come from the schema.** For example `RFIAssignee.role` is one of the schema's roles and `confidence` must be between 0 and 1. Values the schema allows are accepted, including negative amounts (credits) and an empty `lineItems` list where the schema permits one.
- **Unknown fields survive.** Properties the model does not declare, such as `metadata.vendorExtensions`, are kept on a `model_validate` / `model_dump` round trip.

To find the model for a schema name, such as the `inputSchema` or `outputSchema` on a skill, use `get_schema_model`:

```python
from taco import SCHEMA_MODELS, get_schema_model

model = get_schema_model("bom-v1")       # BOMV1; raises KeyError for an unknown name
bom = model.model_validate(json_payload)

print(sorted(SCHEMA_MODELS))             # every canonical schema name
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

:::warning The monitor shows every payload
The monitor shows every request and response the agent handles, to anyone who can reach its port. Before you expose the port beyond your own machine, set a token:

```python
server = A2AServer(card, enable_monitor=True, monitor_auth_token=os.environ["TACO_MONITOR_TOKEN"])
```

The REST API and WebSocket then require it (`Authorization: Bearer <token>`), and you open the UI as `/monitor/#token=<token>`. The monitor sends no CORS headers and its WebSocket rejects connections from other sites, but without a token anyone who can reach the port can read the traffic. In production, leave it off unless it sits behind your own auth.
:::

For explicit control, use the `enable_monitor()` function:

```python
from taco.monitor import enable_monitor

enable_monitor(server=server, client=client, registry=registry, auth_token=os.environ["TACO_MONITOR_TOKEN"])
```

---

## Status

The SDK is in early development. The API surface is subject to change. Current capabilities:

- Full A2A protocol support (message/send, message/stream, tasks/get, tasks/cancel, ListTasks)
- Agent Card discovery at `/.well-known/agent-card.json` (and the legacy `/.well-known/agent.json`)
- Bearer-token authentication with per-task-type scopes and per-caller task isolation
- Multi-turn conversations via context IDs
- Pluggable task store (in-memory default, JSON file, or database-backed)
- Pydantic v2 models with full validation

See the [GitHub repository](https://github.com/pelles-ai/taco) for the latest.
