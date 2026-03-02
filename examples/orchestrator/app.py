"""CAIP Orchestrator — agent discovery, task dispatch, and web dashboard.

Port 8000 | Discovers agents, sends tasks, serves the dashboard UI.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from common.sample_data import SAMPLE_BOM

logger = logging.getLogger("orchestrator")

AGENT_URLS: list[str] = os.getenv(
    "AGENT_URLS",
    "http://localhost:8001,http://localhost:8002,http://localhost:8003",
).split(",")

app = FastAPI(title="CAIP Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state
discovered_agents: dict[str, dict] = {}
message_log: list[dict] = []


def _log(direction: str, url: str, method: str, payload: dict, response: dict) -> None:
    message_log.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction": direction,
        "url": url,
        "method": method,
        "payload": payload,
        "response": response,
    })


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    html_path = Path(__file__).parent / "dashboard.html"
    return HTMLResponse(html_path.read_text())


@app.get("/assets/{filename}")
async def serve_asset(filename: str):
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
    """Fetch Agent Cards from all known agent URLs."""
    discovered_agents.clear()
    async with httpx.AsyncClient(timeout=10) as client:
        for url in AGENT_URLS:
            url = url.strip()
            if not url:
                continue
            try:
                resp = await client.get(f"{url}/.well-known/agent.json")
                card = resp.json()
                discovered_agents[url] = card
                _log("discovery", url, "GET /.well-known/agent.json", {}, card)
            except Exception as exc:
                logger.warning("Failed to discover %s: %s", url, exc)
    return {"agents": discovered_agents}


@app.post("/api/send-task")
async def send_task(request: Request) -> dict:
    """Send a CAIP task to a specific agent via A2A JSON-RPC."""
    body = await request.json()
    agent_url: str = body["agentUrl"]
    task_type: str = body["taskType"]
    input_data: dict = body.get("inputData", SAMPLE_BOM)

    rpc_payload = {
        "jsonrpc": "2.0",
        "id": f"orch-{datetime.now(timezone.utc).timestamp()}",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"structuredData": input_data}],
            },
            "metadata": {"taskType": task_type},
        },
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{agent_url}/", json=rpc_payload)
        result = resp.json()
        _log("outbound", agent_url, f"message/send ({task_type})", rpc_payload, result)

    return result


@app.get("/api/sample-bom")
async def get_sample_bom() -> dict:
    return SAMPLE_BOM


@app.get("/api/message-log")
async def get_message_log() -> dict:
    return {"log": message_log}


@app.post("/api/agents")
async def add_agent_url(request: Request) -> dict:
    """Register a new agent URL for discovery."""
    body = await request.json()
    url: str = body["url"].strip()
    if url and url not in AGENT_URLS:
        AGENT_URLS.append(url)
    return {"status": "ok", "agents": AGENT_URLS}


@app.post("/api/admin/add-skill")
async def add_skill_to_agent(request: Request) -> dict:
    """Proxy skill registration to an agent's admin endpoint."""
    body = await request.json()
    agent_url: str = body["agentUrl"]
    skill_data: dict = body["skill"]
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{agent_url}/admin/skills", json=skill_data)
    return resp.json()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("orchestrator.app:app", host="0.0.0.0", port=8000, reload=False)
