"""Run every curl command in examples/README.md and the example docstrings."""

from __future__ import annotations

import ast
import json
import os
import subprocess

import pytest
from conftest import ADMIN_TOKEN, EXAMPLES_DIR


def _curls(text: str) -> list[str]:
    """Each curl command, with backslash continuations and quoted bodies joined."""
    commands, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        if lines[i].strip().startswith("curl "):
            command = lines[i]
            while command.rstrip().endswith("\\") or command.count("'") % 2:
                i += 1
                command += "\n" + lines[i]
            commands.append(command.strip())
        i += 1
    return commands


def _documented_curls() -> list[tuple[str, str]]:
    sources = {
        "README.md": (EXAMPLES_DIR / "README.md").read_text(),
        "quick_start.py": ast.get_docstring(
            ast.parse((EXAMPLES_DIR / "quick_start.py").read_text())
        ),
        "peer_communication.py": ast.get_docstring(
            ast.parse((EXAMPLES_DIR / "peer_communication.py").read_text())
        ),
    }
    return [
        (name, cmd)
        for name, text in sources.items()
        for cmd in _curls(text or "")
        if "/monitor" not in cmd  # the monitor UI is HTML
    ]


CURLS = _documented_curls()


def test_docs_contain_curls():
    assert len(CURLS) >= 5


@pytest.mark.parametrize(
    ("source", "command"), CURLS, ids=[c.splitlines()[0][:60] for _, c in CURLS]
)
def test_documented_curl_works(source, command, demo, quick_start, peer_example):
    env = {**os.environ, "TACO_ADMIN_TOKEN": ADMIN_TOKEN}
    result = subprocess.run(
        ["bash", "-c", command.replace("curl ", "curl -sS --fail-with-body ", 1)],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert result.returncode == 0, f"{source}: {command}\n{result.stdout}{result.stderr}"
    data = json.loads(result.stdout)
    if isinstance(data, dict) and "error" in data:
        pytest.fail(f"{source}: JSON-RPC error {data['error']}")
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        # An A2A v1 response wraps the task as {"task": ...}.
        task = data["result"].get("task", data["result"])
        assert task["status"]["state"] in ("completed", "TASK_STATE_COMPLETED"), data
    if isinstance(data, dict) and "pipeline" in data:
        assert [s["status"] for s in data["pipeline"]] == ["completed"] * 3
