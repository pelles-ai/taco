# TACO SDK — A2A Protocol v1.0 Migration Guide

> **Status (2026-11-02, taco-agent 0.6.x):** Phases 1 and 2 are done: TACO
> runs on `a2a-sdk>=1.1.1,<2` through the v0.3 compat layer. Phase 4 has
> shipped except JWS-signed Agent Cards. Phase 3 has not started, so the
> on-the-wire JSON is still v0.3.

## Where things stand

| Step | Status |
|---|---|
| 1. Well-known agent card path | Shipped (#25) |
| 2. This guide | Done |
| 3. Pin `a2a-sdk<1` | Superseded by step 5 |
| 4. `A2A-Version` / `A2A-Extensions` headers | `A2A-Version` shipped in 0.3.6; `A2A-Extensions` (and the v0.3 `X-A2A-Extensions`) in 0.6.3 |
| 5. `a2a-sdk` 1.0 compat-layer port | Shipped in 0.3.7; floor raised to 1.1.1 in 0.6.2 so protobuf 6 and 7 work |
| 6–10. v1 wire format | In progress. [ADR-0010](https://taco-protocol.com/docs/decisions/negotiate-v1-wire-format) (proposed) replaces steps 6–10 with version negotiation. The server answers both versions (since 0.3.7), a parity suite runs every scenario on both, and the card advertises both, with `x-construction` in the extension's `params` (0.7.0). `TacoClient(protocol="0.3" \| "1.0" \| "auto")` speaks either (unreleased). Next: v1 examples in the docs, spec and website |
| 11. `ListTasks` | Shipped in 0.3.8 |
| 12. JWS-signed Agent Cards | Not started |
| 13. `x-construction` extension URI | Shipped in 0.3.9 |
| 14. `referenceTaskIds` | Shipped in 0.3.10 (`send_message`, `send_to_peer`); the sandbox demo's RFI agent uses it for revised RFI sets |
| 15. Multiple push-notification configs | Shipped in 0.3.13; notifications are delivered since 0.5.0 |
| 16. mTLS, PKCE, device code | Shipped in 0.6.1 |
| 17. `returnImmediately` | Shipped in 0.3.11 |

## What v1.0 changed (and why our original "1-line switch" plan no longer fits)

The original draft of this guide assumed the v1 SDK would ship a clean
`a2a.compat.v0_3.types` Pydantic shim, and that swapping two import lines in
`taco/types.py` and `taco/_compat.py` would land a zero-change bump.

The released SDK *does* ship `a2a.compat.v0_3.types` (Pydantic, type-compatible
with our current code), but it also restructured several other modules we
depend on:

| Module TACO used before the port | Status in `a2a-sdk` 1.0.2 |
|---|---|
| `a2a.types` | Now **protobuf** (`a2a_pb2`); Pydantic equivalents live at `a2a.compat.v0_3.types` |
| `a2a.utils.message` (`new_agent_text_message`, `get_message_text`) | **Removed.** Moved to `a2a.helpers.proto_helpers` with renamed APIs (`new_text_message`, etc.) and protobuf-shaped signatures |
| `a2a.utils.parts` (`get_text_parts`, `get_data_parts`, `get_file_parts`) | **Removed.** Replaced by protobuf-shaped helpers in `a2a.helpers.proto_helpers` |
| `a2a.utils.artifact` (`new_text_artifact`, `new_data_artifact`) | **Removed.** Same — moved and reshaped |
| `a2a.server.apps.A2AFastAPIApplication` | **Removed.** Replaced by route builders in `a2a.server.routes`: `create_jsonrpc_routes`, `create_agent_card_routes`, `create_rest_routes` |
| `a2a.server.agent_execution.AgentExecutor` | Still present, but `RequestContext.message`, `.current_task`, etc. are now **protobuf** types (`a2a_pb2.Message`, `a2a_pb2.Task`) |
| `a2a.server.events.EventQueue` | Still present (plus a new `EventQueueLegacy`); enqueued events are protobuf-typed |
| `a2a.server.request_handlers.DefaultRequestHandler` | Aliased to `DefaultRequestHandlerV2`; takes `agent_card: a2a_pb2.AgentCard` (protobuf) |
| `a2a.server.request_handlers.LegacyRequestHandler` | New: keeps the v0.3 Pydantic-style executor wiring, still takes a protobuf agent card |

Concretely, `taco/server.py` imported `A2AFastAPIApplication` and
`taco/_compat.py` re-exported `a2a.utils.message/parts/artifact`; both broke
on the bump, which is why step 5 below was one large PR.

## Wire-format changes (protocol v1.0 vs v0.3)

Even with the Pydantic compat layer doing translation, the *protocol* itself
shifted in ways our codebase will need to handle when we want to speak v1
directly:

- **Part discriminator removed.** `Part(root=TextPart(text="x"))` →
  `Part(text="x")`. `kind` field gone — discrimination is by JSON member.
- **Enums are SCREAMING_SNAKE_CASE with prefixes.** `TaskState.completed` →
  `TaskState.TASK_STATE_COMPLETED`; `Role.user` → `Role.ROLE_USER`.
- **JSON-RPC method names renamed.** `message/send` → `SendMessage`;
  `tasks/get` → `GetTask`; new `ListTasks`, `SubscribeToTask`.
- **Stream events use wrapper-keyed format.** `{"taskStatusUpdate": {…}}`
  instead of `{"kind": "taskStatusUpdate", "final": true, …}`. The `final`
  boolean is gone — stream closure signals completion.
- **AgentCard restructured.** Top-level `url` / `protocolVersion` /
  `preferredTransport` / `additionalInterfaces` consolidated into
  `supportedInterfaces[]`. `supportsAuthenticatedExtendedCard` moved to
  `capabilities.extendedAgentCard`. New optional `signatures[]` field for
  cryptographic identity (JWS, RFC 7515, with RFC 8785 canonicalization).
- **New formal `extensions[]` arrays** on `Message`, `Artifact`, `Task`,
  `AgentCapabilities` — replaces ad-hoc `x-*` extension fields with declared
  extension URIs.
- **Well-known agent card path** moved from `/.well-known/agent.json` to
  `/.well-known/agent-card.json` (we already serve both, and the client falls
  back since #25).
- **HTTP+JSON URL prefix dropped.** `POST /v1/message:send` → `POST /message:send`.
- **Error model.** `application/problem+json` (RFC 9457) →
  `application/json` with `google.rpc.Status` / `google.rpc.ErrorInfo`.
- **OAuth flows.** Implicit + Password removed; Device Code (RFC 8628) added;
  PKCE (`pkce_required`) on AuthorizationCode; mTLS scheme formalized.
- **Cursor-based pagination** for `ListTasks` (cursor / limit / nextCursor)
  replaces the old page/perPage model.
- **Per-interface protocol versioning.** Each `AgentInterface` declares its
  own `protocolBinding` and `protocolVersion`, enabling parallel v0.3 + v1
  support on a single agent.
- **New request headers.** `A2A-Version`, `A2A-Extensions`.
- **Multi-tenancy.** Optional `tenant` field on requests and `AgentInterface`.

## TACO migration plan (one branch per step)

The playbook as planned. Each item is a separate PR; phases gate on each
other. The table under [Where things stand](#where-things-stand) tracks what
has shipped.

### Phase 1 — Pre-bump polish (compatible with `a2a-sdk` 0.3.x)

1. **`fix/well-known-agent-card-path`** *(merged in #25)* — Client/registry/CLI
   prefer `/.well-known/agent-card.json` and fall back to the legacy path.
2. **`docs/update-v1-migration-guide`** *(done)* — Replace the optimistic
   draft with the accurate post-1.0 migration shape.
3. **`chore/pin-a2a-sdk-upper-bound`** *(superseded by step 5)* — Pin
   `a2a-sdk>=0.3.25,<1` to block accidental v1 installs before we are ready.
4. **`feat/send-a2a-version-headers`** *(shipped: `A2A-Version` in 0.3.6, `A2A-Extensions` in 0.6.3)* —
   Emit `A2A-Version` (and optional `A2A-Extensions`) request headers from
   `TacoClient` and the CLI.

### Phase 2 — `a2a-sdk` 1.0 compat-layer port (shipped in 0.3.7)

5. **`feat/a2a-sdk-1.0-compat-layer`** — Single PR, larger than originally
   scoped. It took shape (a) below, with `LegacyRequestHandler` and
   `create_jsonrpc_routes(enable_v0_3_compat=True)`. Touches:
   - `sdk/pyproject.toml`: bump `a2a-sdk` floor to `>=1.0.2`.
   - `taco/types.py`: switch `from a2a.types …` → `from a2a.compat.v0_3.types …`.
   - `taco/_compat.py`: drop the dead `a2a.utils.message/parts/artifact`
     re-exports. Either reimplement those names against `a2a.helpers.proto_helpers`
     (renamed APIs, protobuf-shaped signatures) or remove from the public surface
     entirely.
   - `taco/server.py`: port off `A2AFastAPIApplication`. Two viable shapes:
     - **(a) v0.3 wire-format compat** — wire `a2a.compat.v0_3.JSONRPC03Adapter`
       on top of a v1 `RequestHandler`, keep `_TacoAgentExecutor`'s public
       handler signature (Pydantic `Task` / `Artifact`). Internally translate
       protobuf `RequestContext.message` ↔ Pydantic via
       `a2a.compat.v0_3.conversions`.
     - **(b) Native v1 wire format** — use `a2a.server.routes.create_jsonrpc_routes`
       + `create_agent_card_routes` directly. Cleaner long term but ships v1
       wire format to clients before they are ready.
     Recommend **(a)** for this PR so the externally observable behavior is
     unchanged; (b) lands in Phase 3.
   - Verify: `make check-all` green; on-the-wire JSON for agent card,
     `message/send`, `message/stream` byte-identical to current.

### Phase 3 — Native v1.0 adoption (not started)

Each of these flips one wire-level concern from v0.3 to v1. Phase 2 has
landed, so nothing blocks them.

> **Proposed replacement:** [ADR-0010](https://taco-protocol.com/docs/decisions/negotiate-v1-wire-format)
> found that a TACO server already answers every v1 method, so it proposes
> negotiating the wire version instead of flipping TACO's own types: servers
> advertise both versions in the card, `TacoClient` picks one per agent, and
> the Python API stays as it is.

6. **`feat/v1-native-part-constructors`** — Flatten `Part(root=TextPart(...))`
   to `Part(text=...)` in `_compat.py`; update `extract_*` accessors.
7. **`feat/v1-native-enum-literals`** — `TaskState.completed` →
   `TASK_STATE_COMPLETED`; `Role.user` → `ROLE_USER`. Mostly `taco/server.py`.
8. **`feat/v1-agent-card-supported-interfaces`** — Restructure `AgentCard` to
   use `supportedInterfaces[]` instead of top-level `url`. Touches factories,
   client `discover()`, registry, CLI `inspect`, peer URL lookup in `agent.py`.
9. **`feat/v1-jsonrpc-method-names`** — Switch `message/send` → `SendMessage`,
   etc. in `client.py` and `cli.py`.
10. **`feat/v1-stream-event-wrapper-format`** — Update SSE parser
    (`client.py`) and event emission (`server.py`) for the wrapper-keyed
    event shape; drop `final=True`.

### Phase 4 — New v1.0 features

These are net-new capabilities the v0.3 spec did not have. All shipped
except #12, signed Agent Cards (see the table at the top).

11. **`feat/list-tasks-cli-and-client`** — `ListTasks` with cursor pagination;
    `taco list-tasks` subcommand.
12. **`feat/agent-card-jws-signing`** — `signatures[]` field, sign + verify
    helpers, integration with `SecurityExt.trust_tier`.
13. **`feat/formal-x-construction-extension-uri`** — Mint a canonical URI
    (e.g. `https://taco.construction/extensions/x-construction/v1`); declare
    via `AgentCapabilities.extensions[]`.
14. **`feat/reference-task-ids-for-rfi-flows`** — Surface `referenceTaskIds`
    on `send_message` / `send_to_peer`; use it in RFI/ChangeOrder flows.
15. **`feat/multi-push-notification-configs`** — CRUD on push configs
    (`configId`, `createdAt`); useful for long-running estimates/schedules.
16. **`feat/mtls-pkce-device-code-security`** — Surface mTLS, PKCE-required,
    device-code OAuth in `SecurityExt`.
17. **`feat/return-immediately-flag`** — `returnImmediately` on `SendMessage`
    for fire-and-forget workflows.

## Quick reference: current (v0.3 wire format) → target (v1) mapping

```python
# Part construction (Phase 3, branch #6)
Part(root=TextPart(text="hello"))   # current
Part(text="hello")                   # v1

# Enums (Phase 3, branch #7)
TaskState.completed                  # current
TaskState.TASK_STATE_COMPLETED       # v1

Role.user                            # current
Role.ROLE_USER                       # v1

# AgentCard (Phase 3, branch #8)
AgentCard(url="http://...", ...)                                      # current
AgentCard(supported_interfaces=[AgentInterface(url="http://...")], …) # v1

# JSON-RPC methods (Phase 3, branch #9)
"message/send"   →  "SendMessage"
"message/stream" →  "SendStreamingMessage"
"tasks/get"      →  "GetTask"
"tasks/cancel"   →  "CancelTask"
"tasks/resubscribe" → "SubscribeToTask"
# new in v1:        "ListTasks"
```

## References

- A2A protocol v1.0 announcement: <https://github.com/a2aproject/A2A/blob/main/docs/announcing-1.0.md>
- A2A v1 changes: <https://github.com/a2aproject/A2A/blob/main/docs/whats-new-v1.md>
- `a2a-sdk` releases: <https://github.com/a2aproject/a2a-python/releases>
- `a2a-sdk` on PyPI: <https://pypi.org/project/a2a-sdk/>
