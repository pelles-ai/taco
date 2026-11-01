"""Fixtures that run the demo services for the example smoke tests.

Everything runs offline: ``fake_anthropic.py`` stands in for the Claude API,
so CI needs no API key. The demo uses fixed ports (8000-8003 for the
sandbox, 8080 for the quick start, 9000/9001 for the peer example).
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = TESTS_DIR.parent
sys.path.insert(0, str(EXAMPLES_DIR))

ADMIN_TOKEN = "smoke-test-admin-token"
ORCHESTRATOR = "http://127.0.0.1:8000"
UNREACHABLE_AGENT = "http://localhost:8009"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def port_open(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@contextmanager
def running(args: list[str], *, ports: list[int], env: dict | None = None) -> Iterator[None]:
    """Run a demo process until its ports accept connections; stop it after."""
    with tempfile.TemporaryFile() as log:
        proc = subprocess.Popen(
            [sys.executable, *args],
            cwd=EXAMPLES_DIR,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 90
            while not all(port_open(p) for p in ports):
                if proc.poll() is not None or time.monotonic() > deadline:
                    log.seek(0)
                    output = log.read().decode(errors="replace")[-4000:]
                    pytest.fail(f"{' '.join(args)} did not start (exit {proc.poll()}):\n{output}")
                time.sleep(0.3)
            time.sleep(1.0)  # let startup hooks (peer discovery) settle
            yield
        finally:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    proc.kill()


@pytest.fixture(scope="session")
def fake_llm() -> Iterator[str]:
    port = free_port()
    with running([str(TESTS_DIR / "fake_anthropic.py"), str(port)], ports=[port]):
        yield f"http://127.0.0.1:{port}"


@pytest.fixture(scope="session")
def demo(fake_llm: str) -> Iterator[str]:
    """The sandbox: three agents and the orchestrator, via run_demo.py."""
    env = {
        **os.environ,
        "ANTHROPIC_API_KEY": "sk-ant-test",
        "ANTHROPIC_BASE_URL": fake_llm,
        "LLM_PROVIDER": "anthropic",
        "SUPPLIER_AGENT_URL": "http://localhost:8002",
        "TACO_ADMIN_TOKEN": ADMIN_TOKEN,
        "AGENT_URLS": "http://localhost:8001,http://localhost:8002,http://localhost:8003,"
        + UNREACHABLE_AGENT,
    }
    env.pop("ANTHROPIC_MODEL", None)
    with running(["run_demo.py"], ports=[8001, 8002, 8003, 8000], env=env):
        yield ORCHESTRATOR


@pytest.fixture(scope="session")
def quick_start() -> Iterator[str]:
    with running(["quick_start.py"], ports=[8080]):
        yield "http://localhost:8080"


@pytest.fixture(scope="session")
def peer_example() -> Iterator[str]:
    with (
        running(["peer_communication.py", "data"], ports=[9001]),
        running(["peer_communication.py", "orchestrator"], ports=[9000]),
    ):
        yield "http://localhost:9000"
