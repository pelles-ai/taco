#!/usr/bin/env python3
"""Minimal TACO agent — a single-file starting point.

Run:
    pip install taco-agent[all]
    python quick_start.py

Then:
    curl http://localhost:8080/.well-known/agent.json
    curl http://localhost:8080/monitor        # live tracing UI
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
    print("Agent card: http://localhost:8080/.well-known/agent.json")
    print("Monitor UI: http://localhost:8080/monitor")
    uvicorn.run(app, host="0.0.0.0", port=8080)
