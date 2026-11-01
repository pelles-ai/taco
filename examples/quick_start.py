#!/usr/bin/env python3
"""Minimal TACO agent — a single-file starting point.

Run:
    pip install "taco-agent[all]"     # or, from this repo: pip install -e "../sdk[all]"
    python quick_start.py

Then:
    curl http://localhost:8080/.well-known/agent-card.json
    curl http://localhost:8080/monitor        # live tracing UI

    # Send it a task (A2A JSON-RPC; every message needs a messageId)
    curl -X POST http://localhost:8080/ \\
      -H "Content-Type: application/json" \\
      -d '{
        "jsonrpc": "2.0", "id": "1", "method": "message/send",
        "params": {
          "message": {"role": "user", "messageId": "msg-1",
                      "parts": [{"kind": "data", "data": {"hello": "TACO"}}]},
          "metadata": {"taskType": "echo"}
        }
      }'
"""

from taco import (
    A2AServer,
    Artifact,
    ConstructionAgentCard,
    ConstructionSkill,
    Task,
    make_artifact,
    make_data_part,
)


# 1. Define your agent card
card = ConstructionAgentCard(
    name="My First TACO Agent",
    description="A minimal agent that echoes back the input data.",
    url="http://localhost:8080",
    trade="multi-trade",
    csi_divisions=[],
    skills=[
        ConstructionSkill(
            id="echo",
            task_type="echo",
            output_schema="echo-v1",
        ),
    ],
)

# 2. Create the server (with monitor UI at /monitor)
# Tip: pass task_store=JsonFileTaskStore("tasks.json") to persist tasks across restarts
server = A2AServer(card.to_a2a(), enable_monitor=True)


# 3. Register a handler for the "echo" task type
async def handle_echo(task: Task, input_data: dict) -> Artifact:
    """Receives input_data dict, returns it wrapped in an artifact."""
    return make_artifact(
        parts=[make_data_part({"received": input_data, "message": "Hello from TACO!"})],
        name="echo-result",
    )


server.register_handler("echo", handle_echo)

# 4. Expose the ASGI app (for uvicorn) and optional direct run
app = server.app

if __name__ == "__main__":
    import uvicorn

    print("Starting agent on http://localhost:8080")
    print("Agent card: http://localhost:8080/.well-known/agent-card.json")
    print("Monitor UI: http://localhost:8080/monitor")
    uvicorn.run(app, host="0.0.0.0", port=8080)
