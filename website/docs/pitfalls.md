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

**How to fix.** Open the agent card at `/.well-known/agent-card.json`. Check each skill has `taskType` (camelCase on the wire; `task_type` in Python). If your agent card has `id` and not `taskType`, fix it on the SDK side — `ConstructionSkill(id="...", task_type="...")`. `taco inspect <url>` shows each skill's fields so you can catch this before deploy.

---

## 3. Pydantic model and JSON Schema drift apart

**What it looks like.** Your agent validates a payload as a Pydantic model and produces an artifact that the validator on the receiving end rejects. The schema in `/spec/schemas/bom-v1.json` looks fine; the Pydantic class looks fine; somehow they disagree.

**Why it happens.** The JSON Schema is the source of truth ([ADR-0002](./decisions/json-schema-source-of-truth)), but updates to the Pydantic mirror require a manual second step. Someone added a field to the schema and didn't update the model (or vice versa). Pydantic's permissive defaults (extra fields ignored, optional vs required ambiguity) make this easy to ship without noticing.

**How to fix.** In tests, round-trip: construct the Pydantic model, dump it with `by_alias=True, exclude_none=True`, then validate the dump against the canonical `/spec/schemas/{name}.json` using `ajv` or `jsonschema`. If they disagree, the schema wins; update the model.

---

## 4. Tasks complete but the artifact is empty

**What it looks like.** Caller receives `state: "completed"` but `task.artifacts` is `[]` or contains parts with no data. No error anywhere.

**Why it happens.** The handler returned a valid `Artifact`, but with nothing useful in it. Two ways this happens:
- The request carried no `DataPart`, so the handler's `payload` was `{}` and it wrapped that empty dict in an artifact. The SDK logs `Message has no DataPart; handler receives empty input` when this happens.
- A streaming handler yielded no parts. The task completes with no artifacts at all.

Returning `None` or a raw dict is a different failure: the SDK can't build the artifact event, so the task ends `failed` and the status message carries the Pydantic validation error (for example `Task handler failed for type 'estimate': 1 validation error for TaskArtifactUpdateEvent`).

**How to fix.** Check the caller sends its input as a `DataPart`, and have the handler reject an empty payload rather than returning an empty result. Every handler should `return make_artifact(parts=[make_data_part(payload)], name="...")`. Add a type annotation on the handler signature (`async def handle_estimate(task: Task, payload: dict) -> Artifact:`) and run mypy — it catches this in CI.

---

## 5. Streaming events fire but the caller never sees them

**What it looks like.** The agent uses `register_streaming_handler` and yields `Part`s, which the SDK wraps in `TaskArtifactUpdateEvent`s. Logs on the agent side show chunks being produced. The caller's `async for event in client.stream_message(...)` loop receives nothing until the final completion event.

**Why it happens.** Streaming is over SSE. Two common breakage points:
- The agent is behind a proxy that buffers responses (nginx default `proxy_buffering on`)
- The handler does its slow work before the first `yield` (or collects everything into a list and yields at the end), so there is nothing to send until it finishes

Handlers never touch the `EventQueue` directly; the SDK enqueues an event for each `Part` you yield.

**How to fix.** Check the proxy first: `proxy_buffering off` for SSE routes. Then check the handler yields each chunk as soon as it is ready. If both look right, call the agent directly with `curl -N` against the `message/stream` method, bypassing the proxy, to see whether chunks arrive incrementally.

---

## 6. Auth works in dev (no auth) but breaks in prod (OAuth)

**What it looks like.** Dev calls work. Prod calls return 401. The token is valid (decoded via jwt.io); the scope looks correct.

**Why it happens.** The agent card's `securitySchemes` doesn't actually match the `Authorization` header the agent is checking, OR the project-scoped token doesn't match the `projectId` in the payload (see [Best Practices on auth](./best-practices#security-in-production)).

**How to fix.** Three checks:
1. The agent card's `security` array references a `securitySchemes` key that exists (`taco inspect <url>` shows both; [SPEC-005](/docs/spec/SPEC-005-conformance) lists this as a conformance check)
2. The agent's handler reads the bearer token from the right header and validates it against the same auth server that issued it
3. If using project scopes, the token's `taco:project:PRJ-0042` matches `payload["projectId"]` — reject mismatches explicitly rather than treating them as "missing scope"

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

**What it looks like.** Client sends `message.context_id = "ctx-123"`. The server returns a task with `context_id = "some-other-uuid"`. Multi-turn workflows that assumed context_id round-trips break.

**Why it happens.** The A2A SDK manages `context_id` internally. Client-provided values aren't passed through unchanged — the SDK generates and tracks its own. This trips up code written assuming context_id is round-trippable.

**How to fix.** Don't pass `context_id` from the client side. Let the server-issued context_id be the canonical one, and use it for subsequent calls in the same conversation. If you need a client-side correlation handle, use `task.metadata` or the [`reference_task_ids`](./sdk-reference/client) field (A2A v1).

---

## 11. The Monitor UI shows traffic; the logs don't

**What it looks like.** `/monitor` shows tasks flowing through the agent in real time. Your logging pipeline (Datadog, Honeycomb, etc.) shows nothing for the same time window.

**Why it happens.** The Monitor UI reads from the in-process event queue; your structured logger needs explicit calls in the handler. The two are independent channels — the Monitor is for development trace inspection, your logging is for production observability.

**How to fix.** Don't rely on the Monitor for production observability. Add structured logging in your handlers — at minimum, log the task ID, context ID, agent name, task type, and outcome (success/failure with error class). Better yet, instrument with OpenTelemetry so the spans show up in your existing trace pipeline. See [Best Practices on observability](./best-practices#observability).

---

## 12. Schema validator passes; production breaks anyway

**What it looks like.** Your own schema checks pass. Pydantic models validate the payload. Production downstream consumers still reject it.

**Why it happens.** Strict schema validation (`additionalProperties: false`) is not the default in older JSON Schema validators. A payload with extra fields validates green against a permissive validator but breaks a strict one downstream. Or — a field is technically optional but the consumer treats it as required ("we always have a `metadata.generatedAt`...").

**How to fix.** Use a strict validator everywhere — set `additionalProperties: false` on your schemas. Validate sample payloads against the canonical schema in the test suites of both your producer AND consumer agents. If a consumer treats an optional field as required, file it as a schema bug: either the field should be required in `v2`, or the consumer should gracefully handle its absence.

---

## See also

- [Best Practices](./best-practices) — the prescriptive companion to this page
- [SPEC-005 Conformance](/docs/spec/SPEC-005-conformance) — the checks that catch several of these before deploy
- [Cookbook recipes](./cookbook/) — each recipe now includes its own per-pattern pitfalls
