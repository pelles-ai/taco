---
title: ADR-0010 — Negotiate the A2A v1 wire format
description: How TACO moves to the A2A v1 wire format for 1.0. Servers advertise v0.3 and v1, clients pick per agent, and TACO's Python API does not change.
sidebar_position: 10
---

# ADR-0010 — Negotiate the A2A v1 wire format

**Status:** Accepted
**Date:** 2026-11-02 (proposed), 2026-11-03 (accepted)
**Refines:** [ADR-0007](./v1-wire-cutover), Phase 3

## Context

TACO agents speak the A2A v0.3 wire format: `message/send`, `{"kind": "data", ...}` parts, `"state": "completed"`. Under the hood the SDK has run on `a2a-sdk` 1.x since 0.3.7, through its v0.3 compatibility layer ([ADR-0007](./v1-wire-cutover), Phase 2). ADR-0007 planned Phase 3 as a rewrite of TACO's own types, one concern at a time: part constructors, enum literals, the card's `supportedInterfaces`, method names, stream events.

Before planning that work we probed a TACO server (`taco-agent` 0.6.3, `a2a-sdk` 1.3.0) with v1 requests and with `a2a-sdk`'s own v1 client. Most of Phase 3 turns out to be done already.

### What already works

| Probe | Result |
|---|---|
| `SendMessage`, `SendStreamingMessage`, `GetTask`, `CancelTask`, `ListTasks` and the four push-config methods, with `A2A-Version: 1.0` | All handled by an unchanged TACO server, with v1-shaped responses: `SendMessage` returns `{"task": {...}}`, states are `TASK_STATE_COMPLETED`, roles `ROLE_USER`, parts `{"data": {...}}`, and stream events are wrapped as `task` / `artifactUpdate` / `statusUpdate` |
| The same v1 request without `A2A-Version: 1.0` | Rejected, `-32009 VERSION_NOT_SUPPORTED` |
| A v0.3 method (`message/send`) with `A2A-Version: 1.0` | Rejected, `-32603` |
| `a2a-sdk`'s v1 client, given the card TACO serves today | Reads the card as v0.3 (it has no `protocolVersion` or `supportedInterfaces`) and speaks v0.3. Tasks complete. |
| The same client, given a card that also lists a v1 interface | Switches to `SendMessage` with `A2A-Version: 1.0`. Tasks complete. |

`a2a-sdk` routes each request by method name: v0.3 names go through its compatibility layer, and v1 names go to the native v1 handler. Both reach the same TACO executor, so handlers run unchanged. TACO's own middleware is ready too: bearer auth (`taco/auth.py`) and the monitor's streaming detection (`taco/server.py`) already list the v1 method names, and the whole-number rewriting applies to every JSON response. Push notifications are already sent in the v1 event shape (`taco/push.py` uses `to_stream_response`).

### What does not work

- **The card hides v1.** Without `supportedInterfaces`, every v1 client falls back to v0.3. Nothing a TACO server serves today tells a client it can speak v1.
- **v1 clients lose `x-construction`.** A v1 card parser keeps only the extension declaration's URI and drops the inline `x-construction` blocks on the card and on each skill. A v1 client cannot learn an agent's trade, CSI divisions or the `taskType` of its skills.
- **`TacoClient` only speaks v0.3**, apart from `list_tasks`, which already sends `ListTasks` and converts the v1 result back with `a2a.compat.v0_3.conversions`.
- **The docs and spec show v0.3 JSON only.** 14 files in the docs, spec and website use `message/send` and 6 use `"kind": "data"`, including the website's conformance check. The sandbox demo has 4 more of each.

## Decision

### 1. The wire version is negotiated; the Python API stays

Handler signatures, `make_artifact` / `make_data_part` / `extract_structured_data`, the schema models and the types `TacoClient` returns (`taco.types`, v0.3-shaped) do not change. Conversion between v0.3 and v1 happens at the edges: in `a2a-sdk` on the server, as it does today, and in `TacoClient` with the `a2a.compat.v0_3.conversions` helpers, which cover every request, response and stream event. Where TACO puts `taskType` (`params.metadata.taskType`) is the same in both versions.

ADR-0007's plan to flip TACO's own types (`Part(root=...)` → `Part(text=...)`, `TaskState.completed` → `TASK_STATE_COMPLETED`) is dropped. It would break every agent's handler code and change nothing on the wire.

### 2. Servers advertise both versions

The card keeps every v0.3 field and adds the v1 ones. A v0.3 reader and a v1 reader both parse it; we checked `a2a-sdk`'s v1 parser, its v0.3 Pydantic model and TACO's `AgentCard`. Abridged:

```json
{
  "name": "BuildRight Mechanical Estimating Agent",
  "url": "https://api.buildright.io/a2a",
  "protocolVersion": "0.3.0",
  "supportedInterfaces": [
    {"url": "https://api.buildright.io/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"},
    {"url": "https://api.buildright.io/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "0.3"}
  ],
  "capabilities": {
    "extensions": [{
      "uri": "https://taco.construction/extensions/x-construction/v1",
      "required": false,
      "params": {
        "trade": "mechanical",
        "csiDivisions": ["22", "23"],
        "skills": {"generate-estimate": {"taskType": "estimate", "inputSchema": "bom-v1", "outputSchema": "estimate-v1"}}
      }
    }]
  },
  "x-construction": {"trade": "mechanical", "csiDivisions": ["22", "23"]},
  "skills": [{"id": "generate-estimate", "x-construction": {"taskType": "estimate", "inputSchema": "bom-v1", "outputSchema": "estimate-v1"}}]
}
```

`a2a-sdk` clients pick the `1.0` interface when one is listed.

### 3. `x-construction` moves into the extension's `params` for v1 readers

The `x-construction` extension declaration carries the same object as the inline field in its `params`, plus a `skills` map from skill id to that skill's `x-construction` object. For v1 readers, `params` is the canonical location. The inline fields stay, with identical content, for v0.3 readers. TACO's own readers (`TacoClient.discover`, `AgentRegistry`, `taco inspect`, `TacoAgent` peer discovery) read the inline fields first, then `params`, so they also work with v1-only cards from other implementations.

This is a spec change to `spec/agent-card-extensions.md`. The extension URI ([ADR-0009](./extension-uri-naming)) does not change, and the open question of which domain is canonical is separate.

### 4. `TacoClient` negotiates

`TacoClient(protocol="auto" | "1.0" | "0.3")`, with the same argument on `TacoAgent` and `--protocol` on the CLI.

- `"auto"` reads the agent card (fetched once and cached) and uses v1 when `supportedInterfaces` lists `1.0` for the agent's URL, otherwise v0.3.
- In v1 mode the client sends v1 method names with `A2A-Version: 1.0` and converts every response back to the `taco.types` models it returns today. `stream_message` yields the same event dicts in both modes; v1 stream events are converted to the v0.3 shape.
- If an agent rejects the version anyway (`-32009`, or `-32601` from an agent that has no v1 methods), `TacoClient` raises a `TacoClientError` that says which version it tried. In `"auto"` mode that only happens when the card is wrong.

| v0.3 method | v1 method |
|---|---|
| `message/send` | `SendMessage` |
| `message/stream` | `SendStreamingMessage` |
| `tasks/get` | `GetTask` |
| `tasks/cancel` | `CancelTask` |
| `tasks/resubscribe` | `SubscribeToTask` |
| `tasks/pushNotificationConfig/set` / `get` / `list` / `delete` | `CreateTaskPushNotificationConfig` / `GetTaskPushNotificationConfig` / `ListTaskPushNotificationConfigs` / `DeleteTaskPushNotificationConfig` |
| (none) | `ListTasks` (already v1) |

### 5. Rollout

| Release | Change |
|---|---|
| 0.7 | Servers advertise both versions and fill `params`. TACO readers accept `params`. `TacoClient(protocol=...)` exists, defaulting to `"0.3"`. A parity test suite runs on both versions. |
| 0.8 | `TacoClient` defaults to `"auto"`. Docs show v1 examples next to v0.3. |
| 1.0 | v1 is the documented default and the spec's examples use v1. Servers still accept v0.3, marked deprecated, with a removal date announced in the release notes. |

From 0.7, stock `a2a-sdk` v1 clients will start talking v1 to TACO agents without any change on their side. That is the purpose of advertising it, and the v1 path is the same request handler that the probes above exercised. The parity suite lands before the card change, so the two wire versions are proven equivalent before any client sees the new card.

### 6. Tests

- **Parity:** every end-to-end test (send, stream, cancel, list, push delivery, bearer auth including 401/403 and project scope, monitor tracing, whole-number handling, card serving) runs once per wire version.
- **Interoperability:**
  - `a2a-sdk`'s stock v1 client against a TACO server, with both card forms.
  - `TacoClient` in v1 mode against a plain `a2a-sdk` v1 server with no TACO code.
  - `taco-agent` 0.6.3's client against the new server, to show the v0.3 path is unchanged.
- **Demo and website:** the sandbox demo's smoke tests and the website's conformance check run against a server advertising both versions.

## Alternatives considered

### Flip TACO's own types (ADR-0007's Phase 3 as written)

This would rewrite the handler-facing API, and every agent's code with it, for no change on the wire, since `a2a-sdk` already translates between versions on the server. Rejected.

### Make `a2a-sdk`'s protobuf types TACO's public API

This would remove a translation layer, but every user would have to write protobuf instead of Pydantic models and dicts. It is a large break, and nothing in the v1 move requires it. If it is ever done, it gets its own ADR.

### Switch to v1 only at 1.0, without negotiation

Simpler code, but v0.3 clients, including every `taco-agent` up to 0.6, would stop working against 1.0 agents, and 1.0 clients against older agents. Rejected; negotiation is cheap because `a2a-sdk` does the server side.

### Keep the card v0.3-only until 1.0

The lowest-risk option for 0.7: stock v1 clients keep speaking v0.3, and `TacoClient` can still be forced to v1 for testing. The cost is that the v1 path gets no real traffic before 1.0. Rejected (open question 1): servers advertise v1 from 0.7.0.

## Consequences

### Positive

- Agent authors change nothing; handlers written for 0.6 run unchanged under 1.0.
- Old and new clients and agents keep interoperating throughout the rollout.
- The remaining work is small: the card, the client, the docs and a parity test suite.

### Negative

- Until v0.3 support is removed there are two wire versions to test and to document.
- The card carries `x-construction` twice, inline and in `params`, and the two must stay identical. The card model generates both from one source.
- TACO's public types still come from `a2a.compat.v0_3`. If a future `a2a-sdk` drops that module, TACO will have to own those models (open question 4).

## Open questions

1. Should servers advertise v1 in 0.7, or only from 1.0? **Resolved:** from 0.7. Servers have advertised v1 since 0.7.0.
2. Is the default schedule right: `TacoClient` `"auto"` in 0.8, v1 documented as the default in 1.0?
3. How long after 1.0 do servers keep accepting v0.3? Six months, or until 2.0?
4. Should TACO own its Python wire models (`Task`, `Message`, `Artifact`, `Part`) before 1.0 freezes the API, instead of re-exporting `a2a.compat.v0_3.types`?
5. Should Python 3.10 (end of life since October) be dropped in 1.0, and does schema v2 belong in 1.0 or its own release?

## Work breakdown

Each line is one pull request.

1. A parity test harness that runs the end-to-end suite on both wire versions. No behaviour change. **Done** (#72).
2. Card: `supportedInterfaces`, `protocolVersion` and extension `params`; TACO readers accept `params`; spec update. **Shipped in 0.7.0** (#73).
3. `TacoClient(protocol=...)` with conversion of responses and stream events; `TacoAgent` passthrough; CLI `--protocol`. **Shipped in 0.7.1** (#74).
4. Docs, spec and website: v1 examples, the conformance check and the playground. **Done** (#75).
5. 0.8: default `"auto"`. 1.0: deprecation notice for v0.3 and the release. Not started.
