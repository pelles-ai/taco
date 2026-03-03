"""ACME Estimating Agent — generates cost estimates from a BOM.

Port 8001 | Task type: estimate | bom-v1 → estimate-v1
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

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

logger = logging.getLogger("estimating-agent")
llm = LLMProvider()

SUPPLIER_AGENT_URL = os.getenv("SUPPLIER_AGENT_URL")

SYSTEM_PROMPT = """\
You are a construction cost estimating expert. Given a Bill of Materials (BOM) \
in JSON format, generate a detailed cost estimate.

For each BOM line item, provide:
- materialUnitCost and materialTotal (realistic US national averages for commercial construction)
- laborHours and laborRate (union mechanical rates, ~$85-$120/hr depending on complexity)
- equipmentCost (if applicable — cranes, lifts, etc.)
- subtotal for each line

Then provide a summary with:
- totalMaterial, totalLabor, totalEquipment
- subtotal
- overheadPercentage (10-15%) and overheadAmount
- profitPercentage (8-12%) and profitAmount
- grandTotal

Include metadata with generatedBy="acme-estimating-agent", generatedAt (current ISO timestamp), \
confidence (0-1), pricingRegion="US-National", pricingDate (today), and any notes.

Output MUST be valid JSON matching this structure:
{
  "projectId": "...", "trade": "...", "csiDivision": "...",
  "lineItems": [{"bomItemId": "...", "description": "...", "quantity": N, "unit": "...",
    "materialUnitCost": N, "materialTotal": N, "laborHours": N, "laborRate": N,
    "laborTotal": N, "equipmentCost": N, "subtotal": N}],
  "summary": {"totalMaterial": N, "totalLabor": N, "totalEquipment": N, "subtotal": N,
    "overheadPercentage": N, "overheadAmount": N, "profitPercentage": N, "profitAmount": N,
    "grandTotal": N},
  "metadata": {"generatedBy": "...", "generatedAt": "...", "confidence": N,
    "pricingRegion": "...", "pricingDate": "...", "notes": []}
}

Return ONLY the JSON object, no markdown or explanation."""

VE_SYSTEM_PROMPT = """\
You are a construction value engineering expert. Given a Bill of Materials (BOM) \
in JSON format, analyze each line item and identify cost reduction opportunities \
without compromising quality, safety, or code compliance.

For each suggestion, provide:
- bomItemId: reference to the BOM line item
- originalDescription: what the BOM specifies
- suggestion: the value engineering recommendation
- estimatedSavingsPercent: expected cost reduction percentage (5-40%)
- estimatedSavingsAmount: approximate dollar savings
- risk: "low", "medium", or "high"
- justification: why this change is safe and effective
- category: one of "material-substitution", "design-optimization", "procurement-strategy", "installation-method", "specification-review"

Then provide a summary with total estimated savings.

Output MUST be valid JSON matching this structure:
{
  "projectId": "...",
  "suggestions": [{"bomItemId": "...", "originalDescription": "...", "suggestion": "...",
    "estimatedSavingsPercent": N, "estimatedSavingsAmount": N, "risk": "...",
    "justification": "...", "category": "..."}],
  "summary": {"totalSuggestions": N, "totalEstimatedSavings": N,
    "averageSavingsPercent": N, "lowRiskCount": N, "mediumRiskCount": N, "highRiskCount": N},
  "metadata": {"generatedBy": "acme-ve-agent", "generatedAt": "...", "confidence": N, "notes": []}
}

Return ONLY the JSON object, no markdown or explanation."""

HOST = os.getenv("AGENT_HOST", "localhost")

card = AgentCard(
    name="ACME Estimating Agent",
    description="Generates construction cost estimates from bills of materials using AI",
    url=f"http://{HOST}:8001",
    skills=[
        AgentSkill(
            id="generate-estimate",
            name="Generate Cost Estimate",
            description="Takes a BOM and produces a detailed cost estimate with labor, material, and equipment costs",
            x_construction=SkillConstructionExt(
                task_type="estimate",
                input_schema="bom-v1",
                output_schema="estimate-v1",
            ),
        ),
    ],
    x_construction=AgentConstructionExt(
        trade="multi-trade",
        csi_divisions=["22", "23", "26"],
        project_types=["commercial", "healthcare", "education"],
        data_formats={"input": ["bom-json"], "output": ["estimate-json", "csv"]},
        integrations=["procore", "sage"],
    ),
)

server = A2AServer(card, enable_admin=True)


async def _fetch_supplier_quotes(input_data: dict) -> dict | None:
    """Attempt to fetch supplier quotes from a remote supplier agent."""
    if not SUPPLIER_AGENT_URL:
        return None
    try:
        from caip.client import CAIPClient
    except ImportError:
        logger.error("caip[client] not installed — cannot fetch supplier quotes")
        return None
    try:
        async with CAIPClient(agent_url=SUPPLIER_AGENT_URL, timeout=30.0) as client:
            task = await client.send_message("quote", input_data)
            if task.artifacts and task.artifacts[0].parts:
                return task.artifacts[0].parts[0].structured_data
    except Exception as exc:
        logger.warning(
            "Failed to fetch supplier quotes from %s: %s: %s",
            SUPPLIER_AGENT_URL, type(exc).__name__, exc,
        )
    return None


def _make_handler(
    system_prompt: str, artifact_name: str, description: str, schema: str,
) -> Any:
    """Create a task handler that calls the LLM with the given prompt."""
    async def handler(task: Task, input_data: dict) -> Artifact:
        enriched_prompt = system_prompt
        supplier_data_used = False
        if schema == "estimate-v1" and SUPPLIER_AGENT_URL:
            supplier_data = await _fetch_supplier_quotes(input_data)
            if supplier_data:
                supplier_data_used = True
                enriched_prompt = (
                    system_prompt
                    + "\n\nIMPORTANT: Use the following real supplier pricing data "
                    "to make your estimate more accurate:\n"
                    + json.dumps(supplier_data, indent=2)
                )

        result = await llm.generate_json(enriched_prompt, json.dumps(input_data, indent=2))

        metadata: dict[str, Any] = {"schema": schema}
        if SUPPLIER_AGENT_URL:
            metadata["supplierDataUsed"] = supplier_data_used

        return Artifact(
            name=artifact_name,
            description=description,
            parts=[Part(structured_data=result)],
            metadata=metadata,
        )
    return handler


server.register_handler("estimate", _make_handler(
    SYSTEM_PROMPT, "cost-estimate", "AI-generated cost estimate from BOM", "estimate-v1",
))
server.register_handler("value-engineering", _make_handler(
    VE_SYSTEM_PROMPT, "ve-suggestions", "AI-generated value engineering suggestions from BOM", "ve-suggestions-v1",
))
app = server.app

if __name__ == "__main__":
    uvicorn.run("agents.estimating_agent:app", host="0.0.0.0", port=8001, reload=False)
