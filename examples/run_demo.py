#!/usr/bin/env python3
"""Launch all CAIP demo services locally.

Starts 3 agents + 1 orchestrator on ports 8001-8003 and 8000.
Press Ctrl+C to stop all services.
"""

from __future__ import annotations

import signal
import subprocess
import sys
import time

SERVICES = [
    ("Estimating Agent  :8001", [sys.executable, "-m", "uvicorn", "agents.estimating_agent:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]),
    ("Supplier Agent    :8002", [sys.executable, "-m", "uvicorn", "agents.supplier_quote_agent:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]),
    ("RFI Agent         :8003", [sys.executable, "-m", "uvicorn", "agents.rfi_generation_agent:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]),
    ("Orchestrator      :8000", [sys.executable, "-m", "uvicorn", "orchestrator.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]),
]


def main() -> None:
    processes: list[tuple[str, subprocess.Popen]] = []

    for name, cmd in SERVICES:
        print(f"  Starting {name}")
        proc = subprocess.Popen(cmd)
        processes.append((name, proc))
        time.sleep(0.5)

    print()
    print("=" * 60)
    print("  CAIP Sandbox Demo — all services running")
    print("=" * 60)
    print()
    print("  Dashboard:        http://localhost:8000")
    print("  Estimating Agent: http://localhost:8001/.well-known/agent.json")
    print("  Supplier Agent:   http://localhost:8002/.well-known/agent.json")
    print("  RFI Agent:        http://localhost:8003/.well-known/agent.json")
    print()
    print("  Press Ctrl+C to stop all services.")
    print()

    def shutdown(sig, frame):
        print("\nShutting down...")
        for name, proc in processes:
            proc.terminate()
        for name, proc in processes:
            proc.wait(timeout=5)
        print("All services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        for name, proc in processes:
            if proc.poll() is not None:
                print(f"  {name} exited (code {proc.returncode})")
        time.sleep(1)


if __name__ == "__main__":
    main()
