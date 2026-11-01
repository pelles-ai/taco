"""TACO Orchestrator — agent discovery, task dispatch, and web dashboard.

Port 8000 | Discovers agents, sends tasks, serves the dashboard UI.

The orchestrator only contacts the agent URLs listed in ``AGENT_URLS``.
Requests that name any other URL are rejected with 400, so the API cannot be
used to make this server fetch arbitrary addresses. It listens on 127.0.0.1
unless ``ORCHESTRATOR_HOST`` says otherwise. The dashboard is served from the
same origin as the API, so no CORS headers are sent, and every POST must be
``Content-Type: application/json``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from taco.client import RpcError, TacoClient

from common.sample_data import SAMPLE_BOM

logger = logging.getLogger("orchestrator")


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


# The agents this orchestrator may talk to (the allowlist). Nothing else is
# ever fetched.
AGENT_URLS: list[str] = list(
    dict.fromkeys(
        url
        for url in map(
            _normalize_url,
            os.getenv(
                "AGENT_URLS",
                "http://localhost:8001,http://localhost:8002,http://localhost:8003",
            ).split(","),
        )
        if url
    )
)

DISCOVERY_TIMEOUT = httpx.Timeout(10.0)
# LLM-backed tasks can take minutes; the estimator may also wait on the supplier.
TASK_TIMEOUT = httpx.Timeout(300.0, connect=5.0)
ADMIN_TIMEOUT = 10.0
MAX_LOG_ENTRIES = 200
MAX_LOGGED_BODY_BYTES = 256 * 1024
PIPELINE_TASK_TYPES = ("estimate", "material-procurement", "rfi-generation")
FAILED_TASK_STATES = frozenset({"failed", "rejected", "canceled"})

# In-memory state
discovered_agents: dict[str, dict] = {}
message_log: deque[dict] = deque(maxlen=MAX_LOG_ENTRIES)


class ApiError(Exception):
    """Returned to the dashboard as ``{"error": message}`` with ``status_code``."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


# ------------------------------------------------------------------
# Message log
# ------------------------------------------------------------------


def _log(
    direction: str,
    url: str,
    method: str,
    payload: Any,
    response: Any,
    status: int | None = None,
) -> None:
    message_log.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "direction": direction,
            "url": url,
            "method": method,
            "status": status,
            "payload": payload,
            "response": response,
        }
    )


def _decode_body(content: bytes) -> Any:
    if not content:
        return {}
    if len(content) > MAX_LOGGED_BODY_BYTES:
        return {"note": f"body not logged ({len(content)} bytes)"}
    try:
        return json.loads(content)
    except ValueError:
        return {"text": content[:2000].decode("utf-8", "replace")}


async def _log_exchange(response: httpx.Response) -> None:
    """httpx response hook: record each agent call for the dashboard's log."""
    await response.aread()
    request = response.request
    payload = _decode_body(request.content)
    if request.method == "GET":
        direction, method = "discovery", f"GET {request.url.path}"
    elif isinstance(payload, dict) and "jsonrpc" in payload:
        params = payload.get("params") or {}
        task_type = (params.get("metadata") or {}).get("taskType")
        rpc_method = str(payload.get("method"))
        direction = "outbound"
        method = f"{rpc_method} ({task_type})" if task_type else rpc_method
    else:
        direction, method = "outbound", f"{request.method} {request.url.path}"
    origin = f"{request.url.scheme}://{request.url.netloc.decode('ascii')}"
    _log(
        direction,
        origin,
        method,
        payload,
        _decode_body(response.content),
        response.status_code,
    )


# ------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    hooks = {"response": [_log_exchange]}
    async with (
        httpx.AsyncClient(timeout=DISCOVERY_TIMEOUT, event_hooks=hooks) as discovery,
        httpx.AsyncClient(timeout=TASK_TIMEOUT, event_hooks=hooks) as tasks,
    ):
        app.state.discovery_client = discovery
        app.state.task_client = tasks
        yield


app = FastAPI(title="TACO Orchestrator", lifespan=lifespan)


@app.exception_handler(ApiError)
async def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse({"error": exc.message}, status_code=exc.status_code)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


async def _json_body(request: Request) -> dict[str, Any]:
    """Parse a JSON object body, insisting on ``Content-Type: application/json``.

    Requiring the JSON content type means a page on another origin cannot
    trigger these endpoints with a plain form or ``text/plain`` POST.
    """
    content_type = request.headers.get("content-type", "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise ApiError(415, "Content-Type must be application/json")
    try:
        body = await request.json()
    except ValueError:
        raise ApiError(400, "Request body must be valid JSON") from None
    if not isinstance(body, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return body


def _allowed_agent_url(value: Any, field: str = "agentUrl") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, f"{field} must be a non-empty string")
    url = _normalize_url(value)
    if url not in AGENT_URLS:
        raise ApiError(
            400,
            f"{field} is not one of the orchestrator's configured AGENT_URLS",
        )
    return url


def _input_data(body: dict[str, Any]) -> dict[str, Any]:
    input_data = body.get("inputData", SAMPLE_BOM)
    if not isinstance(input_data, dict):
        raise ApiError(400, "inputData must be a JSON object")
    return input_data


def _find_agent_by_task_type(task_type: str) -> str | None:
    """Find the URL of a discovered agent that handles the given task type."""
    for url, card in discovered_agents.items():
        for skill in card.get("skills") or []:
            xc = skill.get("x-construction") or {}
            if xc.get("taskType") == task_type:
                return url
    return None


def _agent_error(
    agent_url: str, method: str, status_code: int, message: str
) -> ApiError:
    """Log a failed agent call and build the error returned to the dashboard."""
    logger.warning("%s %s failed: %s", agent_url, method, message)
    _log("outbound", agent_url, method, {}, {"error": message})
    return ApiError(status_code, message)


async def _discover(url: str) -> tuple[str, dict | None, str | None]:
    """Fetch one agent's card. Returns (url, card, None) or (url, None, error)."""
    client = TacoClient(agent_url=url, http_client=app.state.discovery_client)
    try:
        card = await client.discover()
    except httpx.HTTPStatusError as exc:
        error = f"agent card request returned HTTP {exc.response.status_code}"
    except httpx.TimeoutException:
        error = "agent did not respond in time"
    except httpx.RequestError:
        error = "agent is unreachable"
    except ValueError:  # not JSON, or not a valid agent card
        error = "agent returned an invalid agent card"
    else:
        return url, card.model_dump(mode="json", by_alias=True, exclude_none=True), None
    logger.warning("Discovery of %s failed: %s", url, error)
    _log("discovery", url, "discover agent card", {}, {"error": error})
    return url, None, error


async def _send_task_to_agent(
    agent_url: str, task_type: str, input_data: dict[str, Any]
) -> dict[str, Any]:
    """Send a TACO task with ``message/send`` and return the resulting Task."""
    method = f"message/send ({task_type})"
    client = TacoClient(agent_url=agent_url, http_client=app.state.task_client)
    try:
        task = await client.send_message(task_type, input_data)
    except httpx.TimeoutException:
        raise _agent_error(
            agent_url, method, 504, "Agent did not respond in time"
        ) from None
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise _agent_error(
            agent_url, method, 502, f"Agent returned HTTP {status}"
        ) from None
    except httpx.RequestError:
        raise _agent_error(agent_url, method, 502, "Agent is unreachable") from None
    except RpcError as exc:
        message = f"Agent returned JSON-RPC error {exc.code}: {exc.rpc_message}"[:300]
        raise _agent_error(agent_url, method, 502, message) from None
    except ValueError:  # body was not JSON, or not a Task
        raise _agent_error(
            agent_url, method, 502, "Agent returned an invalid response"
        ) from None
    return task.model_dump(mode="json", by_alias=True, exclude_none=True)


def _status_text(task: dict[str, Any]) -> str:
    message = (task.get("status") or {}).get("message") or {}
    texts = [
        part["text"]
        for part in message.get("parts") or []
        if isinstance(part, dict) and part.get("kind") == "text" and part.get("text")
    ]
    return " ".join(texts)


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    html_path = Path(__file__).parent / "dashboard.html"
    return HTMLResponse(html_path.read_text())


@app.get("/assets/{filename}", response_model=None)
async def serve_asset(filename: str) -> FileResponse | JSONResponse:
    """Serve static assets (logo, etc.)."""
    if ".." in filename or "/" in filename or "\\" in filename:
        return JSONResponse({"error": "Invalid filename"}, status_code=400)
    for base in [Path(__file__).parents[2] / "assets", Path("/app/assets")]:
        path = base / filename
        if path.is_file():
            return FileResponse(path)
    return JSONResponse({"error": "Asset not found"}, status_code=404)


# ------------------------------------------------------------------
# API endpoints
# ------------------------------------------------------------------


@app.get("/api/discover")
async def discover_agents() -> dict:
    """Fetch the Agent Card of every configured agent URL."""
    results = await asyncio.gather(*(_discover(url) for url in AGENT_URLS))
    discovered_agents.clear()
    errors: dict[str, str] = {}
    for url, card, error in results:
        if card is not None:
            discovered_agents[url] = card
        else:
            errors[url] = error or "discovery failed"
    return {"agents": discovered_agents, "errors": errors}


@app.post("/api/send-task")
async def send_task(request: Request) -> dict:
    """Send a TACO task to one configured agent via A2A JSON-RPC."""
    body = await _json_body(request)
    agent_url = _allowed_agent_url(body.get("agentUrl"))
    task_type = body.get("taskType")
    if not isinstance(task_type, str) or not task_type:
        raise ApiError(400, "taskType must be a non-empty string")
    task = await _send_task_to_agent(agent_url, task_type, _input_data(body))
    return {"result": task}


@app.post("/api/run-pipeline")
async def run_pipeline(request: Request) -> dict:
    """Run a full pipeline: Estimate + Quote + RFI in parallel."""
    body = await _json_body(request)
    input_data = _input_data(body)

    if not discovered_agents:
        await discover_agents()
    agent_map = {
        tt: url for tt in PIPELINE_TASK_TYPES if (url := _find_agent_by_task_type(tt))
    }
    if not agent_map:
        raise ApiError(400, "No agents found. Run discovery first.")

    async def run_step(task_type: str) -> dict[str, Any]:
        url = agent_map.get(task_type)
        if url is None:
            return {
                "step": task_type,
                "status": "skipped",
                "reason": f"No agent found for task type '{task_type}'",
            }
        try:
            task = await _send_task_to_agent(url, task_type, input_data)
        except ApiError as exc:
            return {
                "step": task_type,
                "agentUrl": url,
                "status": "failed",
                "error": exc.message,
            }
        # The HTTP call succeeding says nothing about the task: check its state.
        state = (task.get("status") or {}).get("state")
        step: dict[str, Any] = {
            "step": task_type,
            "agentUrl": url,
            "state": state,
            "result": {"result": task},
        }
        if state == "completed":
            step["status"] = "completed"
        elif state in FAILED_TASK_STATES:
            step["status"] = "failed"
            step["error"] = _status_text(task) or f"Task {state}"
        else:
            step["status"] = state or "unknown"
        return step

    steps = await asyncio.gather(*(run_step(tt) for tt in PIPELINE_TASK_TYPES))
    return {"pipeline": list(steps)}


@app.get("/api/sample-bom")
async def get_sample_bom() -> dict:
    return SAMPLE_BOM


@app.get("/api/message-log")
async def get_message_log() -> dict:
    return {"log": list(message_log)}


@app.get("/api/agents")
async def list_agent_urls() -> dict:
    """The configured agent URLs (the only ones this orchestrator contacts)."""
    return {"agents": AGENT_URLS}


@app.post("/api/agents")
async def add_agent_url(request: Request) -> dict:
    """Confirm an agent URL is allowed. New agents are added via AGENT_URLS."""
    body = await _json_body(request)
    _allowed_agent_url(body.get("url"), field="url")
    return {"status": "ok", "agents": AGENT_URLS}


@app.post("/api/admin/add-skill")
async def add_skill_to_agent(request: Request) -> dict:
    """Proxy skill registration to a configured agent's admin endpoint."""
    body = await _json_body(request)
    agent_url = _allowed_agent_url(body.get("agentUrl"))
    skill = body.get("skill")
    if not isinstance(skill, dict):
        raise ApiError(400, "skill must be a JSON object")

    method = "POST /admin/skills"
    try:
        resp = await app.state.task_client.post(
            f"{agent_url}/admin/skills", json=skill, timeout=ADMIN_TIMEOUT
        )
    except httpx.TimeoutException:
        raise _agent_error(
            agent_url, method, 504, "Agent did not respond in time"
        ) from None
    except httpx.RequestError:
        raise _agent_error(agent_url, method, 502, "Agent is unreachable") from None
    if resp.is_error:
        raise ApiError(502, f"Agent rejected the skill (HTTP {resp.status_code})")
    try:
        data = resp.json()
    except ValueError:
        raise ApiError(502, "Agent returned an invalid response") from None
    skill_id = data.get("skillId") if isinstance(data, dict) else None
    return {"status": "ok", "skillId": skill_id}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "orchestrator.app:app",
        host=os.getenv("ORCHESTRATOR_HOST", "127.0.0.1"),
        port=int(os.getenv("ORCHESTRATOR_PORT", "8000")),
        reload=os.getenv("ORCHESTRATOR_RELOAD", "").lower() in {"1", "true", "yes"},
    )


if __name__ == "__main__":
    main()
