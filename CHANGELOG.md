# Changelog

All notable changes to the TACO SDK are documented in this file.

A new version is published to PyPI when a change under `sdk/` is merged to
`main` and the full test suite passes on that commit. New entries go under
**[Unreleased]**; each version section lists what first shipped in it.

## [Unreleased]

### Security
- **Agent Monitor stored XSS** — the monitor UI put the JSON-RPC `method` (copied from any caller's request) into the page unescaped. Every event field is now escaped and inline event handlers are gone.
- **Agent Monitor readable from any website** — the monitor API sent `Access-Control-Allow-Origin: *` and had no auth, so any page a developer visited could read an agent's full traffic log from `localhost`. CORS is removed (the UI is same-origin), the WebSocket rejects cross-site origins, and a new `monitor_auth_token` (on `A2AServer`, `TacoAgent` and `enable_monitor(auth_token=)`) protects the API and WebSocket; open the UI as `/monitor/#token=<token>`.
- **Handler errors leaked to callers** — exception text (connection strings, upstream API errors) was returned verbatim in the failed task's status. Callers now get `Task handler failed for type '<t>' (error id <id>)`; the details are logged under that id. Raise the new `taco.TacoTaskError` for messages the caller should see.
- **Peer calls followed the peer's self-declared URL** — `TacoAgent.send_to_peer` sent requests (and their headers) to whatever `url` a peer's card named. It now uses the URL the peer was discovered at.

### Added
- **Bearer-token auth** — `A2AServer(card, token_verifier=..., require_task_scope=True)` implements the `spec/security.md` checklist: HTTP 401 for a missing or invalid token, 403 when the token lacks `taco:task:<taskType>`. The verifier returns a `taco.AuthContext(subject, scopes, claims)`; each caller's subject becomes the task owner, so callers only see their own tasks. `taco.current_auth()` gives handlers the caller's context; `taco.task_scope()` builds scope names. Card, `/health` and monitor stay public.
- **Security declaration on cards** — `AgentCard` keeps `securitySchemes`, `security` and any other A2A fields TACO doesn't model (they used to be dropped, also from discovered peer cards). `ConstructionAgentCard` accepts `security_schemes`, `security`, `certifications`, `version` and `construction_security` (`x-construction.security`). `taco inspect` shows the security schemes.
- **`TacoClient(headers=...)`** — default headers (e.g. `Authorization`) for every request; `get_task` and `cancel_task` now take `headers=` too. `send_message` raises `MessageReplyError` (with `.reply`) when an A2A agent replies with a Message instead of a Task.
- **Schema registry** — `taco.SCHEMA_MODELS` and `taco.get_schema_model("bom-v1")`.
- **`taco.restore_integers`**, **`AgentRegistry.entries()`** (`(url, card)` pairs) and **`AgentRegistry.find(integration=...)`**.
- **`TacoAgent(peer_startup_wait=2.0)`** — how long startup waits for the first peer-discovery round.
- **`taco send --token` / `taco list-tasks --token`** — send a bearer token.

### Fixed
- **`message/stream` failed on the documented setup** — registering a streaming handler after creating `A2AServer` (as the docs show) left the server's protobuf card at `streaming=False`, so every stream returned -32603 "Streaming is not supported" while the served card advertised streaming. With `enable_monitor=True` the monitor also cut streams off after the first chunk. And when both a regular and a streaming handler were registered (`LangGraphAdapter.register_on(streaming=True)`), the streaming one never ran; `message/stream` now uses it and `message/send` the regular one.
- **`context_id` was ignored** — `TacoClient` sent it outside the message, so every call opened a new conversation (breaking multi-turn threads, the LangGraph thread mapping and `list_tasks(context_id=...)`).
- **`return_immediately` waited for the whole task** — the executor reported nothing until the handler finished. Tasks now report `working` (and carry `metadata.taskType`) before the handler runs.
- **`tasks/cancel` didn't stop anything** — the handler kept running and the task ended `completed` after being reported `canceled`. Cancel now stops the handler.
- **Agents that listed each other as peers never connected** — discovery ran to completion during startup, before either server accepted connections. It now runs concurrently in the background, and a peer still missing is retried when a request needs it. Peers also match on their x-construction `taskType`.
- **Empty card `url`** — a card built without `url` (as the Quick Start does) is served with the address the request reached, so standard A2A clients can connect.
- **Integers arrived as floats** — A2A v1 carries data as protobuf `Struct`, so `{"count": 3}` reached handlers as `3.0`. Handler input, `extract_structured_data` and `get_data_parts` restore whole numbers to `int`.
- **`JsonFileTaskStore` ignored owners, filters and paging** — `list_tasks(context_id=...)` or a page size returned every task. It now matches the a2a-sdk store: per-owner storage, `ListTasks` filters and pagination, copies on read, writes off the event loop with `fsync`.
- **Schema models disagreed with `spec/schemas`** — the SDK rejected spec-valid payloads (negative credit lines, empty `lineItems`/`references`, estimates and quotes without `confidence`/`pricingDate`, free-text trades on schedule activities and change-order lines) and dropped unknown fields such as `metadata.vendorExtensions`. A parity test now compares every model with its JSON Schema.
- **The monitor reported failed tasks as completed.**
- **`A2AServer(ConstructionAgentCard(...))` crashed** — it now converts the factory card itself.
- **`taco send` crashed on an empty, non-terminal stdin** (scripts, CI) and always exited 0.
- **`pip install "taco-agent[all]"` didn't install uvicorn**, so the Quick Start failed on its first run. The `server` and `all` extras now include it.

### Changed
- **Schema models no longer invent values** — optional fields default to `None` (omitted by `exclude_none=True`) instead of `pricingRegion="US-National"`, `scheduleImpactDays=0`, `isCritical=False`, `[]` and so on; check for `None` before iterating optional lists. Fields the spec marks `format: date` / `date-time` are validated as RFC 3339 (date-times need an offset; `date` and aware `datetime` objects are accepted), and `RFIAssignee.role` must be one of the spec's roles.
- **`JsonFileTaskStore` file format version 2** — tasks are grouped by owner. Files written by earlier versions still load (as the anonymous owner); earlier versions can't read the new format.
- **`taco send` exits 1** when the task fails, is rejected or canceled, or the agent returns an RPC error.
- **Logger names** — the server and registry log to `taco.server` and `taco.registry` instead of the a2a-sdk's `a2a` logger.

### CI
- Releases only when `sdk/**` changes, after the full test suite passes on that commit; website-only merges no longer publish a version. The site deploys only after the tests pass.
- Third-party actions are pinned to commit SHAs with per-job permissions.
- Tests run on Python 3.10–3.13 and against the oldest supported a2a-sdk (1.0.2).

## [0.3.15] – [0.3.20] — 2026-09-23 to 2026-09-24

No SDK changes. These versions were published by the old release workflow for website-only merges.

## [0.3.14] — 2026-09-23

### Fixed
- **Streaming handlers on a2a-sdk >= 1.1** — stream chunks now share one artifact id, with the first chunk created via `append=False` and later chunks appended, as the A2A spec requires. a2a-sdk 1.1 started rejecting `append=True` for an unknown artifact id, which made every streaming task fail.
- **Package build on hatchling >= 1.28** — the SDK now ships its own `sdk/README.md` instead of pointing at `../README.md`, which newer hatchling rejects as outside the project directory. This also unblocks the PyPI publish job.

## [0.3.13] — 2026-05-12

### Added
- **Multi push notification configs** — A2A v1 lets a task carry multiple push subscribers (each with `configId` + `createdAt`). New `TacoClient` methods: `create_push_config(task_id, url, *, token=None, authentication=None, config_id=None)`, `list_push_configs(task_id)`, `get_push_config(task_id, config_id)`, `delete_push_config(task_id, config_id)`. `A2AServer` accepts an optional `push_config_store` parameter (auto-defaulted to `InMemoryPushNotificationConfigStore` when the card advertises `capabilities.push_notifications=true`). Also re-exports `PushNotificationConfig`, `TaskPushNotificationConfig`, `PushNotificationAuthenticationInfo`.

## [0.3.11] — 2026-05-12

### Added
- **`return_immediately`** — new optional `bool` parameter on `TacoClient.send_message`, `run_task`, and `TacoAgent.send_to_peer`. When `True`, the server returns the Task as soon as it accepts the message rather than waiting for the terminal state. Maps to A2A v1's `returnImmediately` flag; on the v0.3 wire it is `configuration.blocking: false`. (Until the Unreleased fix above, TACO agents only answered once the handler had finished.)

## [0.3.10] — 2026-05-12

### Added
- **`reference_task_ids`** — A2A v1's task-linking field is plumbed through `TacoClient.send_message()`, `stream_message()`, `run_task()`, `TacoAgent.send_to_peer()`, `stream_from_peer()`, and the `make_message()` helper. Natural fit for construction workflows: an RFI response references its originating RFI task, a change-order approval references the proposal task. Serializes as `referenceTaskIds` on the wire.

## [0.3.9] — 2026-05-11

### Added
- **Canonical `x-construction` extension URI** — `taco.X_CONSTRUCTION_EXTENSION_URI` (`https://taco.construction/extensions/x-construction/v1`). `ConstructionAgentCard.to_a2a()` declares the URI under `capabilities.extensions[]` (A2A v1's formal extension-declaration mechanism) in addition to the inline `x-construction` field, so v1-aware clients can discover support via capability negotiation. Use `taco.apply_construction_extension_declaration(card)` (idempotent) for a card built outside the factory.

## [0.3.8] — 2026-05-11

### Added
- **`TacoClient.list_tasks()`** — wraps the v1 `ListTasks` RPC with cursor-based pagination. Returns `(tasks, next_cursor)`. Sends `A2A-Version: 1.0` since `ListTasks` is v1-only.
- **`taco list-tasks <url>`** — CLI subcommand with `--cursor`, `--limit`, `--context-id`, and `--json` flags.

## [0.3.7] — 2026-05-11

### Changed
- **Bumped `a2a-sdk` to `>=1.0.2,<2`** — adopt the v1 SDK via the v0.3 compat layer. `taco.types` re-exports from `a2a.compat.v0_3.types` (Pydantic) and `taco.server.A2AServer` wraps `LegacyRequestHandler` plus `create_jsonrpc_routes(enable_v0_3_compat=True)` instead of the removed `A2AFastAPIApplication`. On-the-wire JSON for the agent card, `message/send`, `message/stream`, `tasks/get`, and `tasks/cancel` is unchanged from TACO 0.3.x.
- **`JsonFileTaskStore`** implements the v1 `TaskStore` interface (added `list()`, `context` parameter on save/get/delete). It accepts both protobuf `Task` (the runtime path) and Pydantic v0.3 `Task` (for application code) on `save()`.

### Internal
- `taco._compat` no longer re-exports from `a2a.utils.message`/`parts`/`artifact` (gone in v1); the previously exported helper names (`get_text_parts`, `new_agent_text_message`, `new_text_artifact`, etc.) are reimplemented locally on top of `a2a.compat.v0_3.types`.
- `taco.server._TacoAgentExecutor` translates between protobuf (the v1 SDK runtime types) and Pydantic v0_3 (the type shape registered TACO handlers see) at the executor boundary.
- Added explicit `fastapi>=0.115` to the `server` / `test` / `dev` / `all` extras — `a2a-sdk[http-server]` 1.0+ ships only `starlette` + `sse-starlette`.
- Pinned `protobuf>=5.29.5,<6` to work around an upstream bug where `a2a-sdk` 1.0.2 calls `FieldDescriptor.label`, which was removed in protobuf 7.x.

## [0.3.6] — 2026-05-10

### Added
- **`A2A-Version` request header** — `TacoClient`, `AgentRegistry`, and the CLI send `A2A-Version: 0.3` on every request so v1 peers can negotiate. Constant exposed as `taco.client.A2A_PROTOCOL_VERSION`. Caller-supplied headers override the default.

## [0.3.4] — 2026-05-10

### Changed
- **Agent card discovery** — `TacoClient.discover()`, `AgentRegistry.register()`, and the `taco discover` / `taco inspect` CLI commands fetch `/.well-known/agent-card.json` first (the A2A v0.3+ standard path) and fall back to the legacy `/.well-known/agent.json` on 404.

## [0.3.2] — 2026-03-23

### Added
- **Task persistence** — `A2AServer` and `TacoAgent` accept an optional `task_store` parameter for pluggable task persistence (defaults to `InMemoryTaskStore`).
- **`JsonFileTaskStore`** — lightweight JSON-file-backed `TaskStore` with atomic writes, for single-process agents that need persistence without a database.
- **`TaskStore` re-export** — available via `from taco import TaskStore`.

## [0.1.x] — 2026-03-15

### Added
- **TacoAgent** — high-level class combining A2AServer + TacoClient pool + peer discovery from `agents.yaml`
- **Agent Monitor** — opt-in live tracing UI mounted at `/monitor` on any A2AServer (enable with `enable_monitor=True`)
- **Health endpoint** — `GET /health` on every A2AServer
- **Admin endpoints** — opt-in dynamic skill registration (`enable_admin=True`)
- **Streaming handlers** — `register_streaming_handler()` for async generator-based task handlers
- **Change Order schema** — `ChangeOrderV1` data schema
- Security spec: scope taxonomy, trust tiers, token delegation

### Changed
- Migrated to official `a2a-sdk` package (≥0.3.25) — TACO models now wrap upstream types
- `A2AServer` now wraps `A2AFastAPIApplication` from a2a-sdk internally
- Lazy imports for server, client, agent, and monitor modules — `pip install taco-agent` stays lightweight

### Fixed
- CLI exception handling uses proper `isinstance` checks instead of string-based type names
- EventBus `get_history()` pagination semantics (offset/limit)
- Lifespan management uses context manager instead of deprecated `on_event()`
- Peer discovery handles malformed config entries gracefully
- All ruff lint, format, and mypy checks pass in CI

## [0.0.x] — 2026-03-05

### Added
- `TacoClient` — async HTTP client for agent-to-agent communication
- `AgentRegistry` — in-memory agent discovery with trade/task-type filtering
- Full data schemas: `BOMV1`, `EstimateV1`, `QuoteV1`, `RFIV1`, `ScheduleV1`
- Streaming and multi-turn conversation support
- CLI tool (`taco discover`, `taco inspect`, `taco send`, `taco health`)
- CI test workflow with 178+ tests
- Docusaurus documentation website
- Renamed PyPI package from `taco` to `taco-agent`
- Migrated from standalone implementation to `a2a-sdk` dependency
- Renamed project from CAIP to TACO

## [0.0.0] — 2026-03-01

### Added
- Initial TACO specification (task types, agent card extensions, security model)
- JSON Schema definitions for construction data types
- Reference SDK with Pydantic models
- Sandbox demo with 3 LLM-powered agents and orchestrator dashboard
