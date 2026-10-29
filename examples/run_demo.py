#!/usr/bin/env python3
"""Launch all TACO demo services locally.

Starts 3 agents + 1 orchestrator on ports 8001-8003 and 8000, listening on
127.0.0.1 only (set AGENT_BIND_HOST / ORCHESTRATOR_HOST to change that).
Press Ctrl+C to stop all services. If any service exits, the others are
stopped too.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent
AGENT_BIND_HOST = os.getenv("AGENT_BIND_HOST", "127.0.0.1")
ORCHESTRATOR_HOST = os.getenv("ORCHESTRATOR_HOST", "127.0.0.1")
STOP_TIMEOUT_SECONDS = 5.0


SERVICES: list[tuple[str, str, str, int]] = [
    # (name, ASGI app, bind host, port)
    ("Estimating Agent", "agents.estimating_agent:app", AGENT_BIND_HOST, 8001),
    ("Supplier Agent", "agents.supplier_quote_agent:app", AGENT_BIND_HOST, 8002),
    ("RFI Agent", "agents.rfi_generation_agent:app", AGENT_BIND_HOST, 8003),
    ("Orchestrator", "orchestrator.app:app", ORCHESTRATOR_HOST, 8000),
]


def _raise_keyboard_interrupt(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def _stop_all(processes: list[tuple[str, subprocess.Popen]]) -> None:
    """Terminate every running service, killing any that ignore SIGTERM."""
    for _, proc in processes:
        if proc.poll() is None:
            proc.terminate()
    deadline = time.monotonic() + STOP_TIMEOUT_SECONDS
    for name, proc in processes:
        try:
            proc.wait(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            print(f"  {name} did not stop in time; killing it")
            proc.kill()
            proc.wait()


def _print_banner() -> None:
    print()
    print("=" * 60)
    print("  TACO Sandbox Demo — all services running")
    print("=" * 60)
    print()
    print("  Dashboard:        http://localhost:8000")
    print()
    print("  Estimating Agent: http://localhost:8001/.well-known/agent-card.json")
    print("  Supplier Agent:   http://localhost:8002/.well-known/agent-card.json")
    print("  RFI Agent:        http://localhost:8003/.well-known/agent-card.json")
    print()
    print("  Monitors:")
    print("    Estimating:     http://localhost:8001/monitor")
    print("    Supplier:       http://localhost:8002/monitor")
    print("    RFI:            http://localhost:8003/monitor")
    print()
    print("  Press Ctrl+C to stop all services.")
    print()


def main() -> int:
    processes: list[tuple[str, subprocess.Popen]] = []
    signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)
    try:
        for name, app, host, port in SERVICES:
            print(f"  Starting {name:<17} :{port}")
            cmd = [
                sys.executable, "-m", "uvicorn", app,
                "--host", host, "--port", str(port), "--reload",
            ]  # fmt: skip
            processes.append((name, subprocess.Popen(cmd, cwd=EXAMPLES_DIR)))
            time.sleep(0.5)
        _print_banner()

        # Watch the services; if one dies, report it once and stop the rest.
        while True:
            for name, proc in processes:
                code = proc.poll()
                if code is not None:
                    print(f"\n  {name} exited (code {code}); stopping the others.")
                    return code or 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        return 0
    finally:
        _stop_all(processes)
        print("All services stopped.")


if __name__ == "__main__":
    sys.exit(main())
