"""PlanCheck RFI Agent — analyzes BOMs and flags issues as RFIs.

Port 8003 | Task type: rfi-generation | bom-v1 → rfi-v1
"""

from __future__ import annotations

import json
import os

import uvicorn

from common.a2a_models import (
    AgentCard,
    AgentConstructionExt,
    AgentSkill,
    Artifact,
    Part,
    SkillConstructionExt,
    Task,
)
from common.a2a_server import A2AServer
from common.llm_provider import LLMProvider

llm = LLMProvider()

SYSTEM_PROMPT = """\
You are a construction document review expert. Given a Bill of Materials (BOM) \
in JSON format, analyze it for issues that would require an RFI (Request for Information).

Look for:
- Design conflicts between line items (e.g., pipe sizes that don't match fittings)
- Missing specifications (e.g., items without spec sections or ambiguous descriptions)
- Code compliance concerns (e.g., healthcare facility requirements)
- Coordination issues between trades
- Flagged items in the BOM metadata that need follow-up
- Ambiguous material descriptions or missing alternates for sole-source items

Generate 2-4 realistic RFIs. Each RFI must include:
- projectId (from the BOM)
- subject (brief subject line)
- question (detailed clarification request)
- category: "design-conflict", "missing-information", "clarification", "substitution", "coordination", or "code-compliance"
- priority: "low", "medium", "high", or "critical"
- references (array with at least one entry containing sheetId from the BOM's sourceSheet fields)
- suggestedResolution (your recommendation)
- relatedBomItems (array of BOM line item IDs this RFI relates to)
- metadata with generatedBy="plancheck-rfi-agent", generatedAt, confidence

Output MUST be valid JSON — an object with a single key "rfis" containing an array of RFI objects:
{
  "rfis": [
    {
      "projectId": "...", "subject": "...", "question": "...",
      "category": "...", "priority": "...",
      "references": [{"sheetId": "..."}],
      "suggestedResolution": "...",
      "relatedBomItems": ["..."],
      "metadata": {"generatedBy": "...", "generatedAt": "...", "confidence": N}
    }
  ]
}

Return ONLY the JSON object, no markdown or explanation."""

HOST = os.getenv("AGENT_HOST", "localhost")

card = AgentCard(
    name="PlanCheck RFI Agent",
    description="Analyzes BOMs and construction documents for issues, generating structured RFIs",
    url=f"http://{HOST}:8003",
    skills=[
        AgentSkill(
            id="generate-rfi",
            name="Generate RFIs",
            description="Analyzes a BOM for potential design conflicts, missing information, and code compliance issues",
            x_construction=SkillConstructionExt(
                task_type="rfi-generation",
                input_schema="bom-v1",
                output_schema="rfi-v1",
            ),
        ),
    ],
    x_construction=AgentConstructionExt(
        trade="mechanical",
        csi_divisions=["22", "23"],
        project_types=["commercial", "healthcare"],
        data_formats={"input": ["bom-json", "pdf"], "output": ["rfi-json"]},
        integrations=["procore", "bluebeam"],
    ),
)

server = A2AServer(card, enable_admin=True)


async def handle_rfi_generation(task: Task, input_data: dict) -> Artifact:
    result = await llm.generate_json(SYSTEM_PROMPT, json.dumps(input_data, indent=2))
    return Artifact(
        name="rfi-set",
        description="AI-generated RFIs from BOM analysis",
        parts=[Part(structured_data=result)],
        metadata={"schema": "rfi-v1"},
    )


server.register_handler("rfi-generation", handle_rfi_generation)
app = server.app

if __name__ == "__main__":
    uvicorn.run("agents.rfi_generation_agent:app", host="0.0.0.0", port=8003, reload=False)
