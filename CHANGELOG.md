# Changelog

All notable changes to the TACO SDK are documented in this file.

Versions are auto-published to PyPI on every push to `main`.

## [Unreleased]

### Added
- **Task persistence** — `A2AServer` and `TacoAgent` accept an optional `task_store` parameter for pluggable task persistence (defaults to `InMemoryTaskStore`)
- **`JsonFileTaskStore`** — lightweight JSON-file-backed `TaskStore` implementation with atomic writes, suitable for single-process agents that need persistence without a database
- **`TaskStore` re-export** — available via `from taco import TaskStore`
- **Multi push notification configs** — A2A v1 lets a task carry multiple push subscribers (each with `configId` + `createdAt`). New `TacoClient` methods: `create_push_config(task_id, url, *, token=None, authentication=None, config_id=None)`, `list_push_configs(task_id)`, `get_push_config(task_id, config_id)`, `delete_push_config(task_id, config_id)`. `A2AServer` accepts an optional `push_config_store` parameter (auto-defaulted to `InMemoryPushNotificationConfigStore` when the card advertises `capabilities.push_notifications=true`). Also re-exports `PushNotificationConfig`, `TaskPushNotificationConfig`, `PushNotificationAuthenticationInfo`.
- **Canonical `x-construction` extension URI** — `taco.X_CONSTRUCTION_EXTENSION_URI` (`https://taco.construction/extensions/x-construction/v1`). `ConstructionAgentCard.to_a2a()` now declares the URI under `capabilities.extensions[]` (A2A v1's formal extension-declaration mechanism) in addition to the inline `x-construction` field, so v1-aware clients can discover support via capability negotiation. The inline field is preserved for back-compat with pre-v1 readers. Use `taco.apply_construction_extension_declaration(card)` (idempotent) to apply the declaration to a card built outside the factory.
- **`reference_task_ids`** — A2A v1's task-linking field is now plumbed through `TacoClient.send_message()`, `stream_message()`, `run_task()`, `TacoAgent.send_to_peer()`, `stream_from_peer()`, and the `make_message()` helper. Natural fit for construction workflows: an RFI response references its originating RFI task, a change-order approval references the proposal task. Serializes as `referenceTaskIds` on the wire.
- **`return_immediately`** — new optional `bool` parameter on `TacoClient.send_message`, `run_task`, and `TacoAgent.send_to_peer`. When `True`, the server returns the Task as soon as it accepts the message (in `submitted` / `working` state) rather than waiting for the terminal state. Useful for fire-and-forget workflows where progress is observed via `get_task` / `list_tasks`, push notifications, or the Monitor UI. Maps to A2A v1's `returnImmediately` flag; on the v0.3 wire we emit `configuration.blocking: false`.
- **`A2A-Version` request header** — `TacoClient`, `AgentRegistry`, and the CLI now send `A2A-Version: 0.3` on every request so v1 peers can negotiate. Constant exposed as `taco.client.A2A_PROTOCOL_VERSION`. Caller-supplied headers override the default.
- **`TacoClient.list_tasks()`** — wraps the v1 `ListTasks` RPC with cursor-based pagination. Returns `(tasks, next_cursor)`; pass the cursor back to fetch the next page. Sends `A2A-Version: 1.0` since `ListTasks` is v1-only.
- **`taco list-tasks <url>`** — new CLI subcommand with `--cursor`, `--limit`, `--context-id`, and `--json` flags. Prints a one-line-per-task table or raw JSON-RPC result.

### Changed
- **Bumped `a2a-sdk` to `>=1.0.2,<2`** — adopt the v1 SDK via the v0.3 compat layer. `taco.types` re-exports from `a2a.compat.v0_3.types` (Pydantic) and `taco.server.A2AServer` now wraps `LegacyRequestHandler` plus `create_jsonrpc_routes(enable_v0_3_compat=True)` instead of the removed `A2AFastAPIApplication`. On-the-wire JSON for the agent card, `message/send`, `message/stream`, `tasks/get`, and `tasks/cancel` is byte-identical to TACO 0.3.x — existing clients require no changes.
- **`JsonFileTaskStore`** now implements the v1 `TaskStore` interface (added `list()`, `context` parameter on save/get/delete). It accepts both protobuf `Task` (the runtime path) and Pydantic v0.3 `Task` (for application code) on `save()`, and persists in the existing v0.3 Pydantic on-disk format so previously-stored data keeps loading.
- **Agent card discovery** — `TacoClient.discover()`, `AgentRegistry.register()`, and the `taco discover` / `taco inspect` CLI commands now fetch `/.well-known/agent-card.json` first (the A2A v0.3+ standard path) and fall back to the legacy `/.well-known/agent.json` on 404. The server already serves both paths, so this is a no-op against TACO peers.

### Internal
- `taco._compat` no longer re-exports from `a2a.utils.message`/`parts`/`artifact` (gone in v1). The previously-exported helper names (`get_text_parts`, `new_agent_text_message`, `new_text_artifact`, etc.) are now reimplemented locally on top of `a2a.compat.v0_3.types` so the public `taco.*` surface is unchanged.
- `taco.server._TacoAgentExecutor` now translates between protobuf (the v1 SDK runtime types) and Pydantic v0_3 (the type shape registered TACO handlers see) at the executor boundary, so user-facing `TaskHandler` signatures keep working.
- Added explicit `fastapi>=0.115` to the `server` / `test` / `dev` / `all` extras — `a2a-sdk[http-server]` 1.0+ ships only `starlette` + `sse-starlette`, but `taco/server.py` imports FastAPI directly.
- Pinned `protobuf>=5.29.5,<6` to work around an upstream bug where `a2a-sdk` 1.0.2 calls `FieldDescriptor.label`, which was removed in protobuf 7.x.

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
