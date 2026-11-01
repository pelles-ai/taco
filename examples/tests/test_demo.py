"""Smoke tests for the sandbox demo (run_demo.py), against a fake Claude API."""

from __future__ import annotations

import copy
import json

import httpx
import pytest
from conftest import UNREACHABLE_AGENT

from common.sample_data import SAMPLE_BOM

ESTIMATOR = "http://localhost:8001"
RFI_AGENT = "http://localhost:8003"


def bom(project_id: str) -> dict:
    data = copy.deepcopy(SAMPLE_BOM)
    data["projectId"] = project_id
    return data


@pytest.fixture(scope="module")
def http() -> httpx.Client:
    with httpx.Client(timeout=60) as client:
        yield client


def send(http: httpx.Client, demo: str, agent: str, task_type: str, data: dict | None = None):
    body = {"agentUrl": agent, "taskType": task_type}
    if data is not None:
        body["inputData"] = data
    return http.post(f"{demo}/api/send-task", json=body)


def test_discovers_the_three_agents(demo, http):
    found = http.get(f"{demo}/api/discover").json()
    assert sorted(found["agents"]) == [
        "http://localhost:8001",
        "http://localhost:8002",
        "http://localhost:8003",
    ]
    assert found["errors"][UNREACHABLE_AGENT] == "agent is unreachable"
    card = found["agents"][ESTIMATOR]
    assert card["skills"][0]["x-construction"]["taskType"] == "estimate"


def test_orchestrator_only_contacts_configured_agents(demo, http):
    for url in ("http://169.254.169.254", "http://evil.example"):
        resp = http.post(f"{demo}/api/send-task", json={"agentUrl": url, "taskType": "estimate"})
        assert resp.status_code == 400
    plain = http.post(
        f"{demo}/api/send-task",
        content=json.dumps({"agentUrl": ESTIMATOR, "taskType": "estimate"}),
        headers={"Content-Type": "text/plain"},
    )
    assert plain.status_code == 415
    foreign = http.get(f"{demo}/api/discover", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in foreign.headers
    unreachable = send(http, demo, UNREACHABLE_AGENT, "estimate")
    assert unreachable.status_code == 502


def test_estimate_uses_supplier_pricing(demo, fake_llm, http):
    task = send(http, demo, ESTIMATOR, "estimate", bom("PRJ-SMOKE")).json()["result"]
    assert task["status"]["state"] == "completed"
    artifact = task["artifacts"][0]
    assert "lineItems" in artifact["parts"][0]["data"]
    assert artifact["metadata"]["supplierDataUsed"] is True

    requests = http.get(f"{fake_llm}/_requests").json()
    estimate = [
        r["body"]
        for r in requests
        if "cost estimating expert" in (r["body"].get("system") or "")
        and "PRJ-SMOKE" in json.dumps(r["body"]["messages"])
    ][-1]
    assert [m["role"] for m in estimate["messages"]] == ["user"]  # no assistant prefill
    assert estimate["output_config"]["format"]["type"] == "json_schema"
    assert "ignore all previous" not in estimate["system"]  # peer data stays out of it


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("MODE-REFUSAL", "declined"),
        ("MODE-BADSCHEMA", "did not match the expected schema"),
        ("MODE-401", "LLM request failed"),
    ],
)
def test_llm_failures_fail_the_task_with_a_safe_message(demo, http, mode, expected):
    resp = send(http, demo, RFI_AGENT, "rfi-generation", bom(mode))
    task = resp.json()["result"]
    text = " ".join(p.get("text", "") for p in task["status"]["message"]["parts"])
    assert task["status"]["state"] == "failed"
    assert expected in text
    assert "SECRET-BODY-DETAIL" not in resp.text


def test_pipeline_reports_real_task_states(demo, http):
    ok = http.post(f"{demo}/api/run-pipeline", json={"inputData": bom("PRJ-PIPE")}).json()
    assert [s["status"] for s in ok["pipeline"]] == ["completed"] * 3
    failing = http.post(f"{demo}/api/run-pipeline", json={"inputData": bom("MODE-401")}).json()
    assert [s["status"] for s in failing["pipeline"]] == ["failed"] * 3


def test_dashboard_can_add_a_skill_with_the_admin_token(demo, http):
    skill = {
        "id": "value-engineering",
        "name": "Value Engineering Analysis",
        "description": "Identifies cost reduction opportunities",
        "x-construction": {
            "taskType": "value-engineering",
            "inputSchema": "bom-v1",
            "outputSchema": "ve-suggestions-v1",
        },
    }
    added = http.post(f"{demo}/api/admin/add-skill", json={"agentUrl": ESTIMATOR, "skill": skill})
    assert added.json() == {"status": "ok", "skillId": "value-engineering"}
    without_token = http.post(f"{ESTIMATOR}/admin/skills", json=skill)
    assert without_token.status_code == 401

    task = send(http, demo, ESTIMATOR, "value-engineering").json()["result"]
    assert task["status"]["state"] == "completed"
    assert "suggestions" in task["artifacts"][0]["parts"][0]["data"]
