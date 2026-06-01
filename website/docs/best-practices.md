---
title: Best Practices
description: Opinionated guidance for shipping TACO agents to production — agent design, error handling, observability, schema evolution, security, deployment, and testing.
sidebar_position: 4
---

# Best Practices

This is the opinionated guide. The other docs explain *how* TACO works; this one explains *how to use it well in production* — agent design, error handling, observability, schema evolution, security, deployment topology, and testing.

If you disagree with anything here, [open an issue](https://github.com/pelles-ai/taco/issues) — these are working positions, not gospel.

## Agent design

### One skill, one task type

An agent should expose one **logical capability** per skill, not a grab-bag. A skill that handles both `takeoff` and `estimate` is a hint that you actually have two agents wearing one hat — split them.

Why it matters: the registry filter (`registry.find(task_type="estimate")`) returns agents by skill. An agent that does ten different things is harder for other agents to discover correctly than ten focused agents that each do one.

### Make the agent's name testable

`"name": "Mech Estimator Pro"` is OK. `"name": "buildright.io / Mech Estimator Pro / 2026-Q2"` is better. The name should let an operator looking at a trace know *exactly* which agent in their deployment produced an output.

### Don't put logic in the Agent Card

The Agent Card is a declaration. The handler is where logic lives. Agents that try to encode capability nuances into card fields end up with a card no one can validate against. If the agent makes a decision about whether to handle a task, that's the handler's job.

### Keep the trade scope honest

`trade: "multi-trade"` is the construction equivalent of `Any` — it makes registry filters less useful. Use a specific trade unless you genuinely cover several. Orchestrators that want a generalist can still find you (`find(trade=None)`); orchestrators that want a specialist will skip you if you over-claim.

## Error handling

### Distinguish *the task failed* from *I failed to do the task*

A task that completes successfully with `state: "completed"` and an artifact that says "no rooftop unit was specified, please clarify" is a **task that succeeded**. The user got a typed, actionable answer.

A task that goes to `state: "failed"` is a **systems failure**: the handler crashed, the database was unreachable, the LLM timed out. Reserve failed state for these.

Why it matters: failed tasks should page someone; completed-with-a-useful-error-artifact should not.

### Return structured errors as data, not exceptions

```python
async def handle_estimate(task: Task, bom: dict) -> Artifact:
    if not bom.get("lineItems"):
        # Don't raise — return a typed validation result
        return make_artifact(
            parts=[make_data_part({
                "status": "rejected",
                "reason": "bom-v1 requires non-empty lineItems",
                "field": "lineItems",
            })],
            name="estimate-rejection",
        )
    # ... normal path
```

Exceptions in the handler become `state: failed` and the caller loses the structured context. A typed rejection artifact is debuggable from the caller's side and inspectable in the Monitor UI.

### Don't pass exception messages to the caller verbatim

Internal stack traces leak deployment detail, library versions, and sometimes credentials embedded in URLs. Translate exceptions into the project's error vocabulary before sending them out.

## Observability

### Log the task ID, the context ID, and the agent name on every log line

A multi-agent chain produces logs in many places. The two TACO-issued correlation handles are:

- `task.id` — uniquely identifies this single request
- `task.context_id` — groups related tasks into a conversation (A2A SDK manages this)

Tag every log line with both, plus the agent's name from the card. Tracing across three agents becomes a one-grep operation.

### Send `OpenTelemetry` spans, not just logs

The A2A request lifecycle (received → working → completed) maps cleanly onto OpenTelemetry spans. A handler that emits a span per significant phase (`input validation`, `LLM call`, `database query`, `output validation`) lets you produce flame graphs across an entire multi-agent chain.

There's no built-in helper for this in `taco-agent` yet (tracking issue: roadmap). Until there is, instrument your handler manually with `opentelemetry-api`.

### The Monitor UI is for development, not production

`A2AServer(enable_monitor=True)` ships a live tracing dashboard at `/monitor`. It's invaluable while building. Turn it off in production deployments unless you've gated it behind your real auth — by default it exposes every task that flows through the agent.

## Schema evolution

### Treat schema names as immutable

`bom-v1` means what it means today, forever. See [ADR-0006](./decisions/schema-versioning). When you need a different shape, mint `bom-v2`; don't change `bom-v1` semantics under existing producers.

### Add optional fields freely; never add required ones

Within `*-v1`, optional fields are safe — old producers don't emit them, old consumers ignore them. Required-field additions break every existing producer; they're a `v2` change.

### Validate at the boundary, trust the inside

Validate input the moment it arrives in your handler:

```python
async def handle_estimate(task: Task, payload: dict) -> Artifact:
    try:
        bom = BOMV1.model_validate(payload)
    except ValidationError as exc:
        return make_artifact(
            parts=[make_data_part({"status": "rejected", "errors": exc.errors()})],
            name="estimate-rejection",
        )
    # From here on, treat `bom` as definitionally valid.
    # Don't re-validate at every internal call site.
```

Re-validating the same artifact at every internal layer is expensive and gives a false sense of robustness.

## Security in production

### Don't pass tokens downstream — exchange them

A2A's authentication model assumes each hop holds its own narrowed authority. If the GC orchestrator passes its `taco:trade:mechanical taco:project:PRJ-0042:write` token to the supplier agent verbatim, the supplier now has more authority than it should — and if the supplier is later compromised, the blast radius is the entire project's mechanical scope.

The discipline: every hop performs a [RFC 8693 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693) to narrow the token before calling downstream. See [ADR-0003](./decisions/construction-shaped-scopes).

### Bind project-scoped tokens to the project ID in the payload

A token holding `taco:project:PRJ-0042:write` should be rejected if it arrives with a task whose payload references `PRJ-0099`. The token says one thing; the payload says another; the handler should refuse rather than guess.

```python
async def handle_estimate(task: Task, payload: dict) -> Artifact:
    token_project = get_token_project_scope(task.metadata.get("auth_token"))
    payload_project = payload.get("projectId")
    if token_project and token_project != payload_project:
        raise PermissionError(f"Token scoped to {token_project}, payload says {payload_project}")
```

### Rotate sidecar credentials, not just user tokens

Platform sidecars (see [ADR-0004](./decisions/sidecar-pattern)) hold long-lived credentials to the underlying platform. These are far higher-value than any single user token and easier to forget. Rotate on a schedule; log every use.

### Treat the Agent Card as public

Anything in `/.well-known/agent-card.json` is, by definition, public. Don't put hostnames you don't want enumerated, internal organizational hints, or anything that wouldn't survive being in your README.

## Deployment topology

### One agent per process

A single Python process per agent (managed by uvicorn, gunicorn, or your container orchestrator) is the right default. Multi-agent-per-process exists in the SDK (`TacoAgent` bundles a server + client pool) but should be reserved for *paired* agents (e.g. an orchestrator that needs to call out) — not unrelated agents sharing memory.

### Don't share `TacoClient` across requests carelessly

`TacoClient` holds an `httpx.AsyncClient` pool. Sharing one client across all incoming requests is fine; sharing one client across all outgoing destinations might not be — `httpx.AsyncClient` connection pools are per-instance. Profile if you're seeing high outbound latency.

### Run the registry where it's queried

The in-process `AgentRegistry` lives next to the orchestrator that uses it. Don't try to run it as a separate service — that's what a hosted registry will be, and it's on the [roadmap](./roadmap). Until then, every orchestrator that needs discovery instantiates its own registry and `register()`s the peers it needs.

### Health endpoints are cheap; serve one

`GET /health` should be a fast, no-auth, no-side-effects endpoint that returns 200 if the process is alive. Container orchestrators and load balancers expect this. `A2AServer` exposes it automatically since v0.3.

## Testing

### Test the handler, not the HTTP layer

The handler is a function (`async def handle_estimate(task, payload) -> Artifact`). Test it like one:

```python
async def test_estimate_handler():
    bom = {"projectId": "PRJ", "trade": "mechanical", "lineItems": [...]}
    artifact = await handle_estimate(Task(id="t1", ...), bom)
    estimate = extract_structured_data(artifact.parts[0])
    assert estimate["summary"]["total"] > 0
```

You don't need a running server for this. The A2A wire format is implementation detail; the handler's input/output contract is what your callers see.

### Use the conformance runner before every release

Point [`/conformance`](/conformance) at your staging deployment. A green report doesn't mean every claim is true, but a red report means something is broken in your Agent Card or its declarations. Fix red before you ship.

### Mock peer agents, don't run real ones

When testing an orchestrator that calls a supplier agent, mock the supplier's response. Running a real supplier in test creates flakiness, ties test runs to network conditions, and tests the wrong thing (you're not testing the supplier; you're testing your orchestration logic).

A small `TacoClient` test double that returns canned `Task` objects is the right shape.

### Round-trip your schemas in tests

For every schema you produce or consume, add a test that:

1. Constructs a Pydantic model with all required fields
2. Serializes it with `.model_dump(by_alias=True, exclude_none=True)`
3. Validates the result against the canonical JSON Schema at `/spec/schemas/{name}.json` (via `ajv` or `jsonschema`)

This catches drift between the Pydantic model and the schema source of truth (see [ADR-0002](./decisions/json-schema-source-of-truth)).

## When you'll want to break these rules

These are defaults that serve most production deployments. Specific reasons to deviate:

- **One handler that legitimately handles two task types** — fine if the underlying logic is shared and splitting would force ugly duplication. But name it carefully.
- **Failing tasks for structured reasons** — sometimes the *handler itself* failing IS the typed signal you want callers to react to (e.g. an unreachable backing system). Document it explicitly.
- **Sharing an `httpx.AsyncClient` across destinations** — fine if you've measured and it's not the bottleneck, especially for fan-out patterns like [BOM-to-Quote Marketplace](./cookbook/bom-to-quote-marketplace).
- **Wider tokens** — fine inside a single trusted boundary (one company, one VPC) where Token Exchange overhead isn't worth the audit benefit.

Document the deviation in code comments or a README. Future-you will thank present-you.

## See also

- [Architecture Decision Records](./decisions/) — the why behind several of these defaults
- [Security model](./security) — auth, scopes, trust tiers
- [Cookbook](./cookbook/) — these patterns in working form
