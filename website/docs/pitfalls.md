---
title: Common Pitfalls
description: The issues most likely to trip up a first TACO agent — what each looks like, why it happens, and how to fix it. Diagnostic-style, not lecture-style.
sidebar_position: 5
---

# Common Pitfalls

The issues most likely to trip up a first TACO agent. Each entry is structured the same way: **what it looks like**, **why it happens**, **how to fix**.

If you hit one of these and it isn't documented here, [open an issue](https://github.com/pelles-ai/taco/issues) — this list grows as new patterns come up.

---

## 1. Agent card 404s in production but works locally

**What it looks like.** Locally, `curl localhost:8080/.well-known/agent-card.json` returns a JSON document. In production, it returns 404 — but the agent's `/health` endpoint works fine.

**Why it happens.** The most common cause is a reverse proxy or load balancer that doesn't route `/.well-known/` paths to the backend. Nginx and Cloudflare both have configurations that intercept well-known paths for things like ACME challenges; if those rules aren't relaxed for your TACO routes, the agent card never reaches your agent.

**How to fix.** Test the production URL with `curl -v` — if the 404 comes from your proxy (visible in the `Server:` header), update the proxy to forward `/.well-known/agent-card.json` to the backend. If it comes from your agent, you have a server-side routing issue; check that you're using `A2AServer(card.to_a2a())` correctly and not overriding the well-known route.

---

## 2. Skill is registered but not discoverable

**What it looks like.** `card.skills` includes a skill with `id: "estimate"`, the agent serves correctly, but `registry.find(task_type="estimate")` returns an empty list.

**Why it happens.** Almost always the skill's `task_type` field is missing or misspelled. The registry filters on `task_type`; `id` is the human label, `task_type` is the machine-readable thing it dispatches on.

**How to fix.** Open the agent card at `/.well-known/agent-card.json`. Check each skill has `taskType` inside its `x-construction` object (camelCase on the wire; `task_type` in Python). If your agent card has `id` and not `taskType`, fix it on the SDK side — `ConstructionSkill(id="...", task_type="...")`. `taco inspect <url>` shows each skill's fields so you can catch this before deploy.

`TacoAgent.send_to_peer()` is more forgiving: it also matches a skill's `id` or `tags`, so a peer can be reachable through `send_to_peer` and still be invisible to `registry.find(task_type=...)`.

---

## 3. Pydantic model and JSON Schema drift apart

**What it looks like.** Your agent validates a payload as a Pydantic model and produces an artifact that the validator on the receiving end rejects. The schema in `/spec/schemas/bom-v1.json` looks fine; the Pydantic class looks fine; somehow they disagree.

**Why it happens.** The JSON Schema is the source of truth ([ADR-0002](./decisions/json-schema-source-of-truth)), and the Pydantic models mirror it. Within the SDK, a parity test (`sdk/tests/test_schema_parity.py`) fails the build when a model and its schema disagree. Drift still happens in your own code: a copy of a model in another service, a hand-written payload, or `taco-agent` 0.3.20 or earlier, whose models invented defaults (`EstimateV1` filled in `pricingRegion="US-National"` and change-order line items `scheduleImpactDays=0` even when the producer sent nothing).

**How to fix.** Upgrade to a `taco-agent` newer than 0.3.20, then round-trip in your tests: construct the Pydantic model, dump it with `by_alias=True, exclude_none=True`, then validate the dump against the canonical `/spec/schemas/{name}.json` using `ajv` or `jsonschema`. `taco.get_schema_model("bom-v1")` gives you the model for a schema name. If they disagree, the schema wins.

---

## 4. Tasks complete but the artifact is empty

**What it looks like.** Caller receives `state: "completed"` but `task.artifacts` is `[]` or contains parts with no data. No error anywhere.

**Why it happens.** The handler returned a valid `Artifact`, but with nothing useful in it. Two ways this happens:
- The request carried no `DataPart`, so the handler's `payload` was `{}` and it wrapped that empty dict in an artifact. The SDK logs `Message has no DataPart; handler receives empty input` when this happens.
- A streaming handler yielded no parts. The task completes with no artifacts at all.

Returning `None` or a raw dict is a different failure: the SDK can't build the artifact event, so the task ends `failed`. The caller only sees `Task handler failed for type 'estimate' (error id 3f9c2a1b7d4e)`; the Pydantic validation error (`1 validation error for TaskArtifactUpdateEvent`) is in the agent's log under that error id.

**How to fix.** Check the caller sends its input as a `DataPart`, and have the handler reject an empty payload rather than returning an empty result. Every handler should `return make_artifact(parts=[make_data_part(payload)], name="...")`. Add a type annotation on the handler signature (`async def handle_estimate(task: Task, payload: dict) -> Artifact:`) and run mypy — it catches this in CI.

---

## 5. Streaming events fire but the caller never sees them

**What it looks like.** The agent uses `register_streaming_handler` and yields `Part`s, which the SDK wraps in `TaskArtifactUpdateEvent`s. Logs on the agent side show chunks being produced. The caller's `async for event in client.stream_message(...)` loop receives nothing until the final completion event.

**Why it happens.** Streaming is over SSE. Common breakage points:
- The agent is behind a proxy that buffers responses (nginx default `proxy_buffering on`)
- The handler does its slow work before the first `yield` (or collects everything into a list and yields at the end), so there is nothing to send until it finishes
- `taco-agent` 0.3.20 or earlier. There, calling `register_streaming_handler` after constructing `A2AServer` (the documented order) did not reach the card the request handler checks, so every `message/stream` request failed with JSON-RPC error `-32603` ("Streaming is not supported by the agent"); and with `enable_monitor=True` the monitor's middleware drained the response, so over a real server the caller got only the first chunk. Both are fixed in later releases.

Handlers never touch the `EventQueue` directly; the SDK enqueues an event for each `Part` you yield.

**How to fix.** Upgrade from 0.3.20 or earlier first. Then check the proxy: `proxy_buffering off` for SSE routes. Then check the handler yields each chunk as soon as it is ready. If all of that looks right, call the agent directly with `curl -N` against the `message/stream` method, bypassing the proxy, to see whether chunks arrive incrementally.

---

## 6. Auth works in dev (no auth) but breaks in prod (OAuth)

**What it looks like.** Dev calls work. Prod calls return 401. The token is valid (decoded via jwt.io); the scope looks correct.

**Why it happens.** The agent card's `securitySchemes` doesn't actually match what the agent checks, the token lacks the `taco:task:<taskType>` scope the agent requires, OR the project-scoped token doesn't match the `projectId` in the payload (see [Best Practices on auth](./best-practices#security-in-production)).

**How to fix.** The SDK's auth hook is `A2AServer(card, token_verifier=verify)`: your `verify(token)` returns a `taco.AuthContext` or `None`. Then check:
1. The status code. A 401 means the token was missing or `verify` returned `None` (or raised; the exception is logged on `taco.auth`). A 403 means the token is valid but lacks `taco:task:<taskType>` for the requested task; the JSON-RPC error message names the missing scope.
2. `verify` validates against the same auth server that issued the token, and puts the token's scopes into `AuthContext.scopes`.
3. The agent card's `security` array references a `securitySchemes` key that exists (`ConstructionAgentCard(security_schemes=..., security=...)`; `taco inspect <url>` shows both; [SPEC-005](/docs/spec/SPEC-005-conformance) lists this as a conformance check, and the [conformance check](/conformance) runs it)
4. If the agent is project-scoped, the token's `taco:project:PRJ-0042` (or `:write` / `:admin`) matches `payload["projectId"]`; a `:read` project scope does not allow task submission. The 403 message names the missing scope. See [Security: project-scoped agents](./security#project-scoped-agents).

---

## 7. CORS blocks a browser-based client

**What it looks like.** A browser-based client or dashboard fails to load the agent card with a CORS error in the console. `curl` from your laptop works fine.

**Why it happens.** Browsers enforce CORS for cross-origin requests. Your agent's CORS configuration probably allows your own UI's origin but not the origin of the page making the request.

**How to fix.** Two options:
1. Add the calling page's origin to your agent's `cors_origins` list — `A2AServer(card, cors_origins=["https://dashboard.example.com"])`
2. Check from outside the browser with `curl` or `taco inspect <url>`, which aren't subject to CORS

Note that `cors_origins` applies to the whole app, not just the well-known path: `cors_origins=["*"]` also lets any origin call your task endpoints from a browser. The agent card is intentionally public, but if you want it readable from anywhere without opening the task endpoints, add a CORS rule for `/.well-known/` at your reverse proxy instead.

---

## 8. Multiple agents return contradictory data

**What it looks like.** Two estimator agents on the same project, given the same BOM, return totals that differ by 30%. Neither is "wrong" by their own logic; their internal pricing models just diverge.

**Why it happens.** TACO standardizes the *shape* of an estimate, not the *math*. Each estimator agent has its own pricing model — labor rates, material markups, regional adjustments. This is a feature (estimators *should* differ), not a bug.

**How to fix.** Don't try to make estimators agree. Use [`bid-leveling`](./task-types) to normalize their outputs into an apples-to-apples comparison. The bid-leveling agent's job is exactly this reconciliation. Treat your estimators as fundamentally independent sources of opinion; let the leveling step produce the comparable view.

---

## 9. Agent registry returns stale URLs

**What it looks like.** `registry.find()` returns an agent, the orchestrator tries to call it, gets `ConnectError: Connection refused`. The agent hasn't moved — but it also redeployed on a different port last Tuesday and the registry is still pointing at the old port.

**Why it happens.** The in-memory `AgentRegistry` doesn't poll; it caches what you `register()` and serves it forever. Deploys that change the URL silently break the registry's view of reality.

**How to fix.** Three options:
1. Re-register on every orchestrator startup with the current URL set
2. Background task in the orchestrator that re-`register()`s every known URL on a schedule (5 minutes is a good default; surfaces 404s as visible errors)
3. A hosted registry with push updates is possible future work ([see the roadmap](./roadmap)), not something to plan around yet

---

## 10. Task `context_id` doesn't match what the client sent

**What it looks like.** Client calls `send_message(..., context_id="ctx-123")`. The server returns a task with `context_id = "some-other-uuid"`. Multi-turn workflows that assumed context_id round-trips break.

**Why it happens.** In A2A, the context id travels on the message itself (`params.message.contextId`). In `taco-agent` 0.3.20 and earlier, `TacoClient` (and so `TacoAgent.send_to_peer`) put it somewhere the server never read, so the server started a new context for every message. It was a TACO client bug, not A2A behaviour.

**How to fix.** Upgrade to a later `taco-agent`: `send_message`, `stream_message` and `send_to_peer` now set `context_id` on the message, and the returned task carries it. If you hand-build JSON-RPC requests, put `contextId` inside `params.message`, not next to it. Leave `context_id` unset to start a new conversation; the server generates one, and you pass `task.context_id` on the follow-up calls. To link a follow-up to an earlier task as well, use [`reference_task_ids`](./sdk-reference/client) (A2A v1).

---

## 11. The Monitor UI shows traffic; the logs don't

**What it looks like.** `/monitor` shows tasks flowing through the agent in real time. Your logging pipeline (Datadog, Honeycomb, etc.) shows nothing for the same time window.

**Why it happens.** The Monitor UI reads from the in-process event queue; your structured logger needs explicit calls in the handler. The two are independent channels — the Monitor is for development trace inspection, your logging is for production observability.

**How to fix.** Don't rely on the Monitor for production observability (and don't leave it open: it shows every payload to anyone who can reach the port, so set `monitor_auth_token` or turn it off). Add structured logging in your handlers — at minimum, log the task ID, context ID, agent name, task type, and outcome (success/failure with error class). Better yet, instrument with OpenTelemetry so the spans show up in your existing trace pipeline. See [Best Practices on observability](./best-practices#observability).

---

## 12. Schema validator passes; production breaks anyway

**What it looks like.** Your own schema checks pass. Pydantic models validate the payload. Production downstream consumers still reject it.

**Why it happens.** Usually a format or an assumption the producer's check didn't cover. Some JSON Schema validators skip `format` checks unless told otherwise, so a `generatedAt` without a timezone offset passes in one place and fails in a stricter validator downstream (the SDK models reject it). Or a field is technically optional but the consumer treats it as required ("we always have a `metadata.confidence`..."). Or the consumer rejects extra properties the canonical schemas allow, such as `metadata.vendorExtensions`.

**How to fix.** Validate sample payloads against the canonical schema, with format checking turned on (`ajv-formats`, or `jsonschema` with a format checker), in the test suites of both your producer AND consumer agents. The SDK models enforce the schema's date and date-time formats and keep unknown properties, so a model round trip is a good second check. If a consumer treats an optional field as required, file it as a schema bug: either the field should be required in `v2`, or the consumer should gracefully handle its absence.

---

## 13. Whole numbers arrive as floats

**What it looks like.** A caller sends `{"count": 3}`. The handler's `range(input_data["count"])` fails with `TypeError: 'float' object cannot be interpreted as an integer`, or a comparison like `quantity == 120` looks fine but a type check (`isinstance(x, int)`) fails.

**Why it happens.** A2A v1 carries `DataPart` payloads as protobuf `Struct` values, and a `Struct` stores every number as a double. JSON makes no int/float distinction, so nothing is lost, but Python sees `3.0`.

**How to fix.** Upgrade: after `taco-agent` 0.3.20, TACO servers send whole numbers as JSON integers in their responses and stream events, handler `input_data` gets `int`s, and `TacoClient` restores integers in what it receives (including `list_tasks`, whose protobuf round trip brings the floats back). From a non-TACO A2A v1 agent, or a protobuf object you converted yourself, you may still see floats; pass those through `taco.restore_integers()`. Schema validators are not affected: JSON Schema treats `120.0` as an integer.

---

## See also

- [Best Practices](./best-practices) — the prescriptive companion to this page
- [SPEC-005 Conformance](/docs/spec/SPEC-005-conformance) — the checks that catch several of these before deploy
- [Cookbook recipes](./cookbook/) — each recipe now includes its own per-pattern pitfalls
