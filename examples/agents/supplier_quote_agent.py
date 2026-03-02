"""BuildSupply Quote Agent — generates supplier quotes from a BOM.

Port 8002 | Task type: material-procurement | bom-v1 → quote-v1
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
You are a construction material supplier quoting system. Given a Bill of Materials (BOM) \
in JSON format, generate a detailed supplier quote.

For each BOM line item, provide:
- unitPrice and extendedPrice (realistic wholesale pricing for commercial HVAC)
- manufacturer (a real manufacturer name for that type of equipment/material)
- partNumber (realistic part number format for that manufacturer)
- leadTimeDays (7-90 days depending on item type — stock items shorter, custom equipment longer)
- availability: "in-stock", "made-to-order", or "backordered"
- notes (optional — any relevant notes about the item)

Then provide:
- summary: subtotal, taxRate (0.08), taxAmount, freight (estimate based on weight/volume), total
- terms: paymentTerms ("Net 30"), deliveryMethod ("Freight — FOB Destination"), \
warranty ("1 year manufacturer standard"), returnPolicy ("30 days, restocking fee may apply")

Include metadata with generatedBy="buildsupply-quote-agent", generatedAt, confidence.

Output MUST be valid JSON matching this structure:
{
  "projectId": "...", "supplierName": "BuildSupply Industrial",
  "quoteNumber": "QT-...", "validUntil": "YYYY-MM-DD",
  "lineItems": [{"bomItemId": "...", "description": "...", "quantity": N, "unit": "...",
    "unitPrice": N, "extendedPrice": N, "manufacturer": "...", "partNumber": "...",
    "leadTimeDays": N, "availability": "...", "notes": "..."}],
  "summary": {"subtotal": N, "taxRate": N, "taxAmount": N, "freight": N, "total": N},
  "terms": {"paymentTerms": "...", "deliveryMethod": "...", "warranty": "...", "returnPolicy": "..."},
  "metadata": {"generatedBy": "...", "generatedAt": "...", "confidence": N}
}

Return ONLY the JSON object, no markdown or explanation."""

HOST = os.getenv("AGENT_HOST", "localhost")

card = AgentCard(
    name="BuildSupply Quote Agent",
    description="Generates supplier quotes with pricing, lead times, and availability from BOMs",
    url=f"http://{HOST}:8002",
    skills=[
        AgentSkill(
            id="generate-quote",
            name="Generate Supplier Quote",
            description="Takes a BOM and produces a supplier quote with unit prices, lead times, and availability",
            x_construction=SkillConstructionExt(
                task_type="material-procurement",
                input_schema="bom-v1",
                output_schema="quote-v1",
            ),
        ),
    ],
    x_construction=AgentConstructionExt(
        trade="mechanical",
        csi_divisions=["22", "23"],
        project_types=["commercial", "industrial"],
        data_formats={"input": ["bom-json"], "output": ["quote-json", "pdf"]},
        integrations=["procore"],
    ),
)

server = A2AServer(card, enable_admin=True)


async def handle_procurement(task: Task, input_data: dict) -> Artifact:
    result = await llm.generate_json(SYSTEM_PROMPT, json.dumps(input_data, indent=2))
    return Artifact(
        name="supplier-quote",
        description="AI-generated supplier quote from BOM",
        parts=[Part(structured_data=result)],
        metadata={"schema": "quote-v1"},
    )


server.register_handler("material-procurement", handle_procurement)
app = server.app

if __name__ == "__main__":
    uvicorn.run("agents.supplier_quote_agent:app", host="0.0.0.0", port=8002, reload=False)
