# Security Recommendations

This document describes known security considerations for the TACO SDK and example orchestrator. These findings were identified during a security review of the `sdk-and-protocol` branch.

---

## SSRF-1: User-Controlled Agent URLs in Orchestrator Endpoints

**Severity:** High
**Category:** Server-Side Request Forgery (SSRF)
**Affected files:** `examples/orchestrator/app.py`

### Description

Three orchestrator endpoints accept a user-controlled URL and make server-side HTTP requests to it with no validation of scheme, host, or port. The attacker fully controls the destination and the response is returned to the caller, enabling data exfiltration from internal services.

- `POST /api/send-task` (line 143): Takes `agentUrl` from the request body and issues `client.post(f"{agent_url}/", ...)`. The full JSON response is returned to the caller.
- `POST /api/admin/add-skill` (line 234): Takes `agentUrl` from the request body and issues `client.post(f"{agent_url}/admin/skills", ...)`. The attacker also controls the JSON body sent to the target.
- Both endpoints have zero URL validation — no scheme check, no host allowlist, no private IP filtering.

### Exploit Scenario

An attacker sends `POST /api/send-task` with:

```json
{
  "agentUrl": "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
  "taskType": "estimate"
}
```

The orchestrator makes an HTTP POST to the AWS metadata service. The JSON response (containing IAM credentials) is returned directly to the attacker. The same pattern works against any internal service reachable from the orchestrator (Redis, Elasticsearch, internal APIs).

### Recommendation

- Validate `agentUrl` against the known `AGENT_URLS` allowlist before making any outbound request. Reject any `agentUrl` not present in the `discovered_agents` dict or the `AGENT_URLS` list.
- Restrict the URL scheme to `http` and `https`.
- Block requests to private and link-local IP ranges (`169.254.x.x`, `10.x.x.x`, `172.16-31.x.x`, `127.x.x.x`).

---

## SSRF-2: Persistent SSRF via Unvalidated Agent URL Registration

**Severity:** High
**Category:** Server-Side Request Forgery (SSRF)
**Affected files:** `examples/orchestrator/app.py`

### Description

The `POST /api/agents` endpoint accepts any URL from the request body and appends it to the `AGENT_URLS` list with no validation. When `GET /api/discover` is subsequently called, the orchestrator makes HTTP GET requests to `{url}/.well-known/agent.json` for every registered URL. The attacker controls the full scheme, host, and port. The response is parsed as JSON and returned to the caller.

Unlike SSRF-1, this variant is **persistent** — the malicious URL remains in `AGENT_URLS` and is fetched on every subsequent discovery call by any user until the server restarts.

### Exploit Scenario

1. Attacker registers a malicious URL:
   ```json
   POST /api/agents
   {"url": "http://internal-elasticsearch:9200"}
   ```
2. When any user clicks "Discover Agents" in the dashboard, the orchestrator fetches `http://internal-elasticsearch:9200/.well-known/agent.json`.
3. If the internal service responds with JSON, the response is stored and returned, leaking internal service information.
4. The malicious URL persists across all future discovery calls.

### Recommendation

- Validate URLs submitted to `POST /api/agents`:
  - Restrict schemes to `http` and `https`.
  - Block private and link-local IP ranges (`169.254.x.x`, `10.x.x.x`, `172.16-31.x.x`, `127.x.x.x`).
  - Resolve the hostname and validate the resolved IP before storing the URL.
- Consider requiring a valid agent card response (with schema validation) before persisting the URL.
- Add authentication to the `/api/agents` endpoint to prevent unauthorized URL registration.

---

## AUTH-1: No Authentication on Server Endpoints

**Severity:** High
**Category:** Missing Authentication
**Affected files:** `sdk/taco/server.py`

### Description

The `A2AServer` exposes all A2A endpoints (`message/send`, `message/stream`, `tasks/get`, `tasks/cancel`) and the agent card discovery endpoint (`/.well-known/agent.json`) with no authentication or authorization middleware. Any network-reachable client can send tasks, retrieve task results, or cancel tasks belonging to other clients.

The server also provides no hook or parameter for users to inject their own auth middleware (e.g., API key validation, OAuth2 bearer token verification).

### Impact

- Unauthorized task submission (resource abuse, cost if LLM-backed)
- Task data leakage — any caller can retrieve any task by ID
- Task cancellation by unauthorized parties

### Recommendation

- Add an optional `auth_middleware` or `dependencies` parameter to `A2AServer.__init__()` so users can inject FastAPI dependencies for auth.
- At minimum, support passing custom headers in `TacoClient` for token-based auth:
  ```python
  TacoClient(agent_url="...", headers={"Authorization": "Bearer ..."})
  ```
- Document that production deployments must add authentication.

---

## AUTH-2: Unprotected Admin Endpoints

**Severity:** High
**Category:** Missing Authentication / Privilege Escalation
**Affected files:** `sdk/taco/server.py` (lines 384–410)

### Description

When `enable_admin=True`, the server exposes three admin endpoints with no authentication:

- `POST /admin/skills` — Add a new skill to the agent card at runtime
- `DELETE /admin/skills/{skill_id}` — Remove a skill from the agent card
- `GET /admin/skills` — List all skills

These endpoints mutate the agent's capabilities in-place. An attacker can:

1. Add fake skills to make the agent appear to support task types it doesn't handle, causing errors for legitimate callers.
2. Remove real skills, effectively disabling the agent's advertised capabilities.
3. Enumerate all agent skills for reconnaissance.

Additionally, removing a skill via the admin endpoint does not clean up the corresponding handler in `_handlers` or `_streaming_handlers`, leaving orphaned handlers.

### Recommendation

- Add authentication to admin endpoints (API key, mTLS, or same auth as main endpoints).
- Consider removing admin endpoints from the SDK entirely and treating agent card mutations as a deployment concern.
- If kept, clean up handler registrations when skills are removed.

---

## SSRF-3: Server-Side Request Forgery in AgentRegistry

**Severity:** High
**Category:** Server-Side Request Forgery (SSRF)
**Affected files:** `sdk/taco/registry.py` (lines 22–30)

### Description

`AgentRegistry.register()` accepts an arbitrary URL string and immediately makes an HTTP GET request to `{url}/.well-known/agent.json` with no validation of scheme, host, or IP range. The response is parsed as JSON and stored.

This is in the SDK itself (not just the examples), so any application using `AgentRegistry` inherits this vulnerability.

### Exploit Scenario

```python
registry = AgentRegistry()
# Attacker-controlled input:
await registry.register("http://169.254.169.254/latest/meta-data")
# SDK makes GET to http://169.254.169.254/latest/meta-data/.well-known/agent.json
```

If deployed on AWS/GCP/Azure, this can reach cloud metadata endpoints. Even if the response isn't valid JSON, the HTTP request itself leaks that the internal service is reachable.

### Recommendation

- Validate URLs before making requests: restrict to `http`/`https` schemes, block private/link-local IP ranges.
- Resolve hostnames and check resolved IPs before connecting.
- Consider adding an `allowed_hosts` parameter to `AgentRegistry.__init__()`.

---

## CORS-1: Wildcard CORS Origin

**Severity:** Medium
**Category:** Misconfiguration
**Affected files:** `sdk/taco/server.py` (line 77), `examples/orchestrator/app.py`

### Description

The `A2AServer` defaults to `cors_origins=["*"]`, allowing any origin to make cross-origin requests to the agent. The orchestrator example also uses `allow_origins=["*"]`.

While acceptable for local development, wildcard CORS in production allows:

- Cross-site request forgery from any website
- Data exfiltration if a user visits a malicious page while on the same network as the agent

### Recommendation

- Change the default to an empty list or `None` and require explicit configuration.
- Log a warning when `"*"` is used: `"CORS allow_origins=['*'] is insecure for production use"`.
- Document recommended CORS configuration for production deployments.

---

## DOS-1: No Rate Limiting on Server

**Severity:** Medium
**Category:** Denial of Service
**Affected files:** `sdk/taco/server.py`

### Description

The server accepts unlimited requests with no rate limiting. An attacker can:

- Exhaust server resources by flooding `message/send` (especially if handlers invoke LLMs)
- Fill the task store to `max_tasks` (10,000 by default), evicting legitimate tasks
- Abuse streaming endpoints to hold connections open indefinitely

### Recommendation

- Document that production deployments should add rate limiting (e.g., via a reverse proxy or FastAPI middleware).
- Consider adding an optional `rate_limit` parameter or middleware hook to `A2AServer`.
- The `max_tasks` limit (default 10,000) provides some protection but each task with large artifacts can still consume significant memory.

---

## SEC-1: No Agent Card Signature Verification

**Severity:** Medium
**Category:** Trust / Integrity
**Affected files:** `sdk/taco/registry.py`, `sdk/taco/client.py`

### Description

Both `AgentRegistry.register()` and `TacoClient.discover()` fetch agent cards over HTTP and trust the response without any signature verification. A man-in-the-middle or a compromised DNS could serve a forged agent card that:

- Redirects task traffic to an attacker-controlled endpoint
- Advertises fake capabilities to intercept specific task types
- Claims to be a trusted agent (spoofing identity)

### Recommendation

- Require HTTPS for production agent URLs.
- Consider supporting signed agent cards (e.g., JWS) for high-trust environments.
- Validate that the agent card's `url` field matches the URL it was fetched from.

---

## SEC-2: Path Traversal in Dashboard Asset Serving

**Severity:** Medium
**Category:** Path Traversal
**Affected files:** `examples/orchestrator/app.py` (lines 104–113)

### Description

The orchestrator serves static assets with a path traversal check using `if ".." in filename`. This is incomplete — it does not handle:

- URL-encoded sequences (`%2e%2e%2f` for `../`)
- Double-encoding (`%252e%252e%252f`)
- Backslash variants on Windows (`..\\`)

### Recommendation

- Use `pathlib.Path.resolve()` and verify the resolved path is within the assets directory.
- Or use FastAPI's `StaticFiles` mount instead of a custom handler.

---

## SEC-3: Client-Side Data Exposure in Dashboard

**Severity:** Low
**Category:** Information Disclosure
**Affected files:** `examples/orchestrator/dashboard.html` (lines 410–412, 513–514)

### Description

The dashboard sends full JSON-RPC request and response payloads to the browser and logs them in the message log. In production scenarios, these payloads may contain:

- Proprietary pricing data from estimates/quotes
- Internal project identifiers
- Trade secrets in BOM specifications

### Recommendation

- Redact or summarize sensitive fields before sending to the browser.
- Add a server-side filter for the message log that strips `structuredData` contents.

---

## SEC-4: No Input Sanitization Before Handler Dispatch

**Severity:** Low
**Category:** Injection
**Affected files:** `sdk/taco/server.py`

### Description

The server extracts `structuredData` from incoming messages and passes it as a raw `dict` to handlers. If handlers log, display, or embed this data in HTML/SQL without sanitization, this creates injection risks (XSS, SQL injection, log injection).

The SDK itself is not vulnerable, but the handler contract does not warn developers about sanitization.

### Recommendation

- Document that handlers must treat `input_data` as untrusted input.
- Consider validating `input_data` against the handler's declared input schema before dispatch.
- Add a note in the `register_handler()` docstring about input sanitization.
