# Changelog

All notable changes to the TACO SDK are documented in this file.

Versions are auto-published to PyPI on every push to `main`.

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
