"""Print the Agent Card a TACO server serves for the conformance page's sample.

The sample card on /conformance is exactly what ``A2AServer`` serves, so it
shows the fields a real agent publishes (``supportedInterfaces``, the
extension's ``params``, ...). Regenerate it after an SDK change to the card:

    python scripts/served-card.py > src/data/sample-agent-card.json

CI runs this against the SDK in the repository and fails if the file is stale.
Needs ``taco-agent[server,client]``.
"""

import asyncio
import json

import httpx
from taco import A2AServer, ConstructionAgentCard, ConstructionSkill

CARD = ConstructionAgentCard(
    name="Mechanical Estimator",
    description="Prices mechanical bills of materials for Divisions 22 and 23.",
    url="https://estimator.example.com",
    trade="mechanical",
    csi_divisions=["22", "23"],
    project_types=["healthcare", "commercial"],
    skills=[
        ConstructionSkill(
            id="estimate-mech",
            name="Estimate mechanical BOM",
            description="Turns a bom-v1 into a priced estimate-v1.",
            task_type="estimate",
            input_schema="bom-v1",
            output_schema="estimate-v1",
        )
    ],
)


async def main() -> None:
    server = A2AServer(CARD.to_a2a())
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://agent") as http:
        card = (await http.get("/.well-known/agent-card.json")).json()
    print(json.dumps(card, indent=2))


asyncio.run(main())
