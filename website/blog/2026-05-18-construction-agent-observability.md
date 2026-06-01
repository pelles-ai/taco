---
slug: construction-agent-observability
title: Construction agent observability — trace IDs, OpenTelemetry, and the Monitor UI
authors:
  - name: Pelles + TACO contributors
    url: https://github.com/pelles-ai
tags: [observability, opentelemetry, debugging]
---

When something goes wrong in a multi-agent construction workflow, the question is always the same: *which agent, at what step, with what data?*

The answer should be one query. It usually isn't, because every team starts with logs and grows into traces too late. This post is the prescriptive version: how to instrument a TACO agent so that "which agent, at what step, with what data" really is one query — and how to use the [Monitor UI](/docs/sdk-reference/server) for what it's actually good at (and not for what it isn't).

<!-- truncate -->

## The three things to tag on every log line

A2A gives you two correlation handles per request, plus your agent name. Tag every log line with all three:

```python
import logging

logger = logging.getLogger(__name__)

async def handle_estimate(task: Task, payload: dict) -> Artifact:
    log_ctx = {
        "agent": "stafford-mech-estimator-v2",
        "task_id": task.id,
        "context_id": task.context_id,
        "task_type": "estimate",
    }
    logger.info("received estimate request", extra=log_ctx)
    # ...
    logger.info("estimate complete", extra={**log_ctx, "total": result["total"]})
    return artifact
```

Why each handle matters:

- **`agent`** — which process produced this log line. Critical when you have multiple agents (orchestrator + estimator + supplier) and your aggregator merges all their logs.
- **`task.id`** — uniquely identifies *this single request*. The grep handle when something failed once.
- **`task.context_id`** — A2A's conversation grouping handle. Multi-turn workflows share a context_id; this is how you trace an RFI through generation, response, and follow-up across hours or days.

With those three on every log line, "show me everything that happened to task `abc-123`" is `grep task_id=abc-123` across all your agents' logs. Without them, it's archaeology.

## OpenTelemetry: spans for the request lifecycle

Logs answer "what happened?" Traces answer "in what sequence, and how long did each step take?" For multi-hop agent chains, traces are the artifact that turns "the bid timed out somewhere" into "the supplier's third hop took 47 seconds."

Wire OpenTelemetry into your handler with the standard auto-instrumentation:

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

async def handle_estimate(task: Task, payload: dict) -> Artifact:
    with tracer.start_as_current_span("handle_estimate") as span:
        span.set_attribute("taco.task_id", task.id)
        span.set_attribute("taco.context_id", task.context_id)
        span.set_attribute("taco.task_type", "estimate")
        span.set_attribute("taco.payload.line_items", len(payload.get("lineItems", [])))

        with tracer.start_as_current_span("validate_input"):
            bom = BOMV1.model_validate(payload)

        with tracer.start_as_current_span("price_via_accubid"):
            result = await price_bom(bom)

        with tracer.start_as_current_span("build_artifact"):
            artifact = make_artifact(...)

        span.set_attribute("taco.result.total", result["total"])
        return artifact
```

That gives you, for any single estimate call:

- The total wall time
- The breakdown across input validation, downstream call, artifact construction
- Linked context IDs across all agents in the chain (if they all use the same trace context)

Datadog, Honeycomb, Grafana Tempo, and basically every modern observability backend consume OTLP. The above 20 lines of code is all you need to get production-grade visibility.

## Propagating trace context across A2A calls

When your orchestrator calls a downstream agent via `TacoClient.send_message(...)`, you want the downstream span to be a child of your span. OpenTelemetry handles this via W3C Trace Context headers, which TACO (and A2A) currently pass through transparently — but you need to inject them on the way out and extract them on the way in.

The shape (slightly simplified):

```python
from opentelemetry.propagate import inject

headers = {}
inject(headers)  # adds traceparent + tracestate

async with TacoClient(agent_url=...) as client:
    task = await client.send_message("estimate", payload, headers=headers)
```

On the receiving side, the server-side OpenTelemetry instrumentation extracts the headers and continues the trace. The full chain shows up in your observability backend as one connected trace, with span branches per agent.

This is what makes "the bid timed out somewhere" investigatable in one minute instead of one hour.

## What the Monitor UI is for (and what it isn't)

`A2AServer(card, enable_monitor=True)` exposes `/monitor` — a live tracing dashboard showing every task that flows through that agent.

It's invaluable for:

- **Local development.** Watch a request work end-to-end before committing the change.
- **Debugging a specific request right now.** When a customer says "I just got a weird response," opening `/monitor` shows you the task in real time.
- **Demos.** Showing a stakeholder how the protocol works in motion.

It's **not** for:

- **Production observability.** The Monitor stores events in process memory; it doesn't persist across restarts; it doesn't aggregate across agents. Don't replace your real logging with it.
- **Compliance / audit.** No retention guarantees; no immutability; no access control by default. Don't use it as your audit trail.
- **Exposing externally.** The Monitor reveals every task that flows through the agent. By default it's not auth-gated. **Turn it off in production unless you've put it behind your real authentication layer.**

The pattern we recommend: `enable_monitor=True` in dev/staging, `False` in production. If you need a production-grade equivalent, use your real observability stack (the OpenTelemetry instrumentation above) rather than trying to harden the Monitor for production use.

## A typical debugging session

A real session from the field:

> Customer email: "The estimate we got from your agent at 3:47 PM today looked off — the labor hours were too low."

What we did:

1. Pulled the customer's email timestamp (3:47 PM local time, October 4) and converted to UTC.
2. Searched our log aggregator: `agent=stafford-mech-estimator-v2 AND task_type=estimate AND timestamp:[2026-10-04T19:30Z TO 2026-10-04T20:00Z]`. Found 8 estimate requests in that window.
3. For each, pulled the `task_id` and looked it up in our OpenTelemetry trace view. One of them had a span for `price_via_accubid` that took 0.4 seconds (everything else was 6-12 seconds).
4. That span had attribute `accubid.fallback=true` — meaning Accubid's labor markup rules failed to apply for some reason and we fell back to a flat default. **There was the bug.**
5. Pulled the input payload (logged at receive time): the BOM had a `unit: "MSF"` line item that Accubid's import didn't recognize, triggering the fallback path.
6. Fixed our unit handling; deployed; re-ran the customer's BOM; sent them the corrected estimate.

Total time from email to fix: 23 minutes. With logs alone (no traces), this would have taken hours.

## What's coming

Two observability items are on the SDK roadmap:

- **Built-in OpenTelemetry instrumentation.** Today, instrumentation is "do it yourself." A future SDK release will provide a `A2AServer(card, telemetry=...)` parameter that auto-instruments the full request lifecycle. You'll still need to add the spans for your handler-specific work.
- **Structured failure taxonomy.** A2A's `failed` state is currently opaque (just an error message). We're scoping a typed `failure.reason` enum (`auth-rejected`, `payload-invalid`, `downstream-timeout`, `internal-error`) so failures can be aggregated and alerted on by category.

If you'd like to influence either, [open an issue](https://github.com/pelles-ai/taco/issues).

## TL;DR

1. **Three tags on every log line:** agent name, task ID, context ID.
2. **OpenTelemetry spans for the request lifecycle.** It's 20 lines of code; the payoff is enormous.
3. **Propagate trace context across agent calls** so the full chain shows up as one trace.
4. **The Monitor UI is for development, not production.** Turn it off when you deploy.

## See also

- [Best Practices on observability](/docs/best-practices#observability)
- [SDK Reference: `A2AServer`](/docs/sdk-reference/server)
- [Cookbook: Three-hop chain](/docs/cookbook/gc-estimator-supplier-chain) — a workflow that benefits immediately from trace context
- [Common Pitfalls #11](/docs/pitfalls) — "The Monitor UI shows traffic; the logs don't"
