---
slug: introducing-taco-v0.3
title: Introducing TACO v0.3
authors:
  - name: TACO Team
    url: https://github.com/pelles-ai
tags: [release, a2a, construction]
---

# TACO v0.3: Security, Schemas, and a Real SDK

We're excited to ship TACO v0.3 — the biggest release yet for the construction agent protocol. This release adds production-grade security, two new data schemas, and a health endpoint, all backed by 167 passing tests.

<!-- truncate -->

## What's New

### Admin Authentication

The TACO server now supports admin authentication via `admin_auth_token`. Skill mutations (add, update, remove) are gated by a constant-time comparison using `hmac.compare_digest()`. If you enable admin endpoints without a token, the server logs a warning so you don't accidentally ship an open admin API.

### New Data Schemas

- **ScheduleV1** — model project schedules with activities, dependencies, and milestones. Includes validation for unique activity IDs.
- **ChangeOrderV1** — track scope changes with line items, cost impact, and approval status.

Both schemas follow the same Pydantic-based pattern as our existing bom-v1, rfi-v1, estimate-v1, and quote-v1 schemas.

### Health Endpoint

Every TACO server now exposes `GET /health` out of the box. Use it for load balancer checks, uptime monitoring, or container orchestration readiness probes.

### Improved CORS Handling

CORS middleware is no longer added by default. If you need cross-origin support, pass `cors_origins` explicitly to `A2AServer`. This follows the principle of least surprise for production deployments.

### Registry Improvements

- **Atomic writes** using `tempfile` + `os.replace` — no more corrupt JSON files on crash
- **Corrupt JSON handling** — the registry gracefully recovers from malformed persistence files

### CLI Error Handling

The `taco` CLI now catches `HTTPStatusError` and `ConnectError` exceptions and displays user-friendly error messages instead of raw tracebacks.

## By the Numbers

| Metric | Value |
|--------|-------|
| Tests passing | 167 |
| Task types | 18 |
| Data schemas | 6 |
| CSI divisions supported | 50+ |

## Get Started

```bash
pip install "taco-agent[all]"
```

Check out the [getting started guide](/docs/getting-started/build-agent) to build your first construction agent, or explore the [data schemas](/docs/schemas/) to see what's available.

## What's Next

We're working on the v1.0 migration path aligned with the A2A SDK v1.0 release. See our [migration guide](/docs/sdk) for details on what to expect.

TACO is Apache 2.0. Contributions welcome — [join the discussion](https://github.com/pelles-ai/taco/discussions).
