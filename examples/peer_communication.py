#!/usr/bin/env python3
"""Two agents communicating via TACO — demonstrates peer discovery and messaging.

Run:
    pip install "taco-agent[all]"     # or, from this repo: pip install -e "../sdk[all]"

    # Terminal 1: Start the data agent
    python peer_communication.py data

    # Terminal 2: Start the orchestrator agent (discovers the data agent)
    python peer_communication.py orchestrator

Then:
    # Send a question to the orchestrator, which calls the data agent
    curl -X POST http://localhost:9000/ \\
      -H "Content-Type: application/json" \\
      -d '{
        "jsonrpc": "2.0", "id": "1", "method": "message/send",
        "params": {
          "message": {"role": "user", "messageId": "msg-1",
                      "parts": [{"kind": "data", "data": {"question": "How many items?"}}]},
          "metadata": {"taskType": "analyze"}
        }
      }'

    # Check monitors
    # Data agent:        http://localhost:9001/monitor
    # Orchestrator:      http://localhost:9000/monitor
"""

import sys

import uvicorn

from taco import (
    Artifact,
    ConstructionAgentCard,
    ConstructionSkill,
    Task,
    TacoAgent,
    make_artifact,
    make_data_part,
    extract_structured_data,
)


# ── Data Agent (port 9001) ──────────────────────────────────────────

def run_data_agent():
    from taco import A2AServer

    card = ConstructionAgentCard(
        name="Data Agent",
        description="Provides sample construction data.",
        url="http://localhost:9001",
        trade="electrical",
        csi_divisions=["26"],
        skills=[
            ConstructionSkill(id="data-query", task_type="data-query", output_schema="query-result-v1"),
        ],
    )

    server = A2AServer(card.to_a2a(), enable_monitor=True)

    async def handle_query(task: Task, input_data: dict) -> Artifact:
        question = input_data.get("question", "")
        # In a real agent, this would query a database or call an LLM
        return make_artifact(
            parts=[make_data_part({
                "question": question,
                "answer": f"You asked: '{question}'. Here are 42 items.",
                "count": 42,
            })],
            name="query-result",
        )

    server.register_handler("data-query", handle_query)

    print("Data Agent on http://localhost:9001")
    print("Monitor:    http://localhost:9001/monitor")
    uvicorn.run(server.app, host="0.0.0.0", port=9001)


# ── Orchestrator Agent (port 9000) ──────────────────────────────────

def run_orchestrator():
    card = ConstructionAgentCard(
        name="Orchestrator Agent",
        description="Plans queries and calls data agents.",
        url="http://localhost:9000",
        trade="multi-trade",
        csi_divisions=[],
        skills=[
            ConstructionSkill(id="analyze", task_type="analyze", output_schema="analysis-v1"),
        ],
    )

    # TacoAgent handles peer discovery + client pooling automatically
    agent = TacoAgent(
        card,
        peers=["http://localhost:9001"],  # discovers the data agent
        enable_monitor=True,
    )

    async def handle_analyze(task: Task, input_data: dict) -> Artifact:
        question = input_data.get("question", "No question provided")

        # Call the data agent via TACO A2A
        peer_task = await agent.send_to_peer(
            "data-query",
            {"question": question},
        )

        # Extract the result
        peer_data = extract_structured_data(peer_task.artifacts[0].parts[0])

        return make_artifact(
            parts=[make_data_part({
                "answer": f"Analysis complete. Data agent said: {peer_data.get('answer')}",
                "data_source": peer_data,
            })],
            name="analysis-result",
        )

    agent.register_handler("analyze", handle_analyze)

    print("Orchestrator on http://localhost:9000")
    print("Monitor:       http://localhost:9000/monitor")
    uvicorn.run(agent.app, host="0.0.0.0", port=9000)


# ── CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("data", "orchestrator"):
        print("Usage: python peer_communication.py [data|orchestrator]")
        print()
        print("  data          Start the data agent on :9001")
        print("  orchestrator  Start the orchestrator on :9000 (discovers data agent)")
        sys.exit(1)

    if sys.argv[1] == "data":
        run_data_agent()
    else:
        run_orchestrator()
