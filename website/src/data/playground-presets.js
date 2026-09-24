/**
 * Playground presets. Each one is real Python against the real taco-agent
 * package, run in the browser with Pyodide. Top-level `await` works.
 * Every preset is executed in Pyodide before it ships; keep them runnable.
 */

const DEFINE = `from taco import ConstructionAgentCard, ConstructionSkill

card = ConstructionAgentCard(
    name="Mechanical Estimator",
    description="Prices mechanical bills of materials for Divisions 22 and 23.",
    url="https://estimator.example.com",
    trade="mechanical",
    csi_divisions=["22", "23"],
    project_types=["healthcare"],
    skills=[
        ConstructionSkill(
            id="estimate-mech",
            name="Estimate mechanical BOM",
            description="Turns a bom-v1 into a priced estimate-v1.",
            task_type="estimate",
            input_schema="bom-v1",
            output_schema="estimate-v1",
        ),
    ],
).to_a2a()

# This is the JSON other agents fetch from /.well-known/agent-card.json
print(card.model_dump_json(by_alias=True, exclude_none=True, indent=2))
`;

const SERVE = `# A real A2AServer and a real TacoClient, talking over an in-memory
# transport instead of the network.
import httpx
from taco import (
    A2AServer, ConstructionAgentCard, ConstructionSkill, EstimateV1,
    TacoClient, extract_structured_data, make_artifact, make_data_part,
)

card = ConstructionAgentCard(
    name="Mechanical Estimator",
    url="http://estimator",
    trade="mechanical",
    csi_divisions=["23"],
    skills=[ConstructionSkill(id="estimate-mech", task_type="estimate",
                              input_schema="bom-v1", output_schema="estimate-v1")],
).to_a2a()

UNIT_COST = {"EA": 38500, "LF": 18.40}   # material, per unit
LABOR_HOURS = {"EA": 16, "LF": 0.2}      # per unit
RATE = 95                                # dollars per labor hour

async def estimate(task, bom):
    items = []
    for li in bom["lineItems"]:
        material = round(li["quantity"] * UNIT_COST[li["unit"]], 2)
        hours = round(li["quantity"] * LABOR_HOURS[li["unit"]], 2)
        labor = round(hours * RATE, 2)
        items.append({
            "bomItemId": li["id"], "description": li["description"],
            "quantity": li["quantity"], "unit": li["unit"],
            "materialUnitCost": UNIT_COST[li["unit"]], "materialTotal": material,
            "laborHours": hours, "laborRate": RATE, "laborTotal": labor,
            "subtotal": round(material + labor, 2),
        })
    subtotal = round(sum(i["subtotal"] for i in items), 2)
    overhead, profit = round(subtotal * 0.12, 2), round(subtotal * 0.10, 2)
    result = EstimateV1.model_validate({
        "projectId": bom["projectId"], "trade": bom["trade"], "csiDivision": bom["csiDivision"],
        "lineItems": items,
        "summary": {
            "totalMaterial": round(sum(i["materialTotal"] for i in items), 2),
            "totalLabor": round(sum(i["laborTotal"] for i in items), 2),
            "totalEquipment": 0, "subtotal": subtotal,
            "overheadPercentage": 12, "overheadAmount": overhead,
            "profitPercentage": 10, "profitAmount": profit,
            "grandTotal": round(subtotal + overhead + profit, 2),
        },
        "metadata": {"generatedBy": "playground-estimator", "generatedAt": "2026-09-23T12:00:00Z",
                     "confidence": 0.8, "pricingDate": "2026-09-01"},
    })
    return make_artifact(parts=[make_data_part(result.model_dump(by_alias=True, exclude_none=True))])

server = A2AServer(card)
server.register_handler("estimate", estimate)

bom = {
    "projectId": "PRJ-2026-OAKRIDGE-MEDICAL", "trade": "mechanical", "csiDivision": "23",
    "lineItems": [
        {"id": "LI-001", "description": "Rooftop unit, 25-ton", "quantity": 2, "unit": "EA"},
        {"id": "LI-002", "description": "Copper pipe, Type L, 2 inch", "quantity": 850, "unit": "LF"},
    ],
    "metadata": {"generatedBy": "playground", "generatedAt": "2026-09-23T12:00:00Z"},
}

transport = httpx.ASGITransport(app=server.app)
async with httpx.AsyncClient(transport=transport, base_url="http://estimator") as http:
    client = TacoClient(agent_url="http://estimator", http_client=http)
    task = await client.send_message("estimate", bom)

print("Task state:", task.status.state.value)
if task.status.state.value != "completed":
    raise SystemExit(f"The handler failed: {task.status.message}")
estimate_v1 = EstimateV1.model_validate(extract_structured_data(task.artifacts[0].parts[0]))
for li in estimate_v1.line_items:
    print(f"  {li.bom_item_id}  {li.description:<30} {li.subtotal:>12,.2f}")
print(f"Grand total: {estimate_v1.summary.grand_total:,.2f}")
`;

const DISCOVER = `from taco import AgentRegistry, ConstructionAgentCard, ConstructionSkill

def agent(name, trade, divisions, task_type, output_schema):
    return ConstructionAgentCard(
        name=name, url=f"https://{name.lower().replace(' ', '-')}.example.com",
        trade=trade, csi_divisions=divisions,
        skills=[ConstructionSkill(id=task_type, task_type=task_type, output_schema=output_schema)],
    ).to_a2a()

registry = AgentRegistry()
for card in [
    agent("Mech Estimator", "mechanical", ["22", "23"], "estimate", "estimate-v1"),
    agent("Elec Estimator", "electrical", ["26"], "estimate", "estimate-v1"),
    agent("RFI Drafter", "multi-trade", ["23", "26"], "rfi-generation", "rfi-v1"),
    agent("Pipe Supplier", "plumbing", ["22"], "material-procurement", "quote-v1"),
]:
    registry.register_card(card.url, card)

print("Estimators for Division 23:")
for card in registry.find(task_type="estimate", csi_division="23"):
    print(" ", card.name, "->", card.url)

print("Anything electrical:")
for card in registry.find(trade="electrical"):
    print(" ", card.name)
`;

const VALIDATE = `from pydantic import ValidationError
from taco import BOMV1

good = {
    "projectId": "PRJ-0042", "trade": "mechanical", "csiDivision": "23",
    "lineItems": [{"id": "LI-001", "description": "Copper pipe, Type L",
                   "quantity": 850, "unit": "LF", "size": "2 inch"}],
    "metadata": {"generatedBy": "takeoff-agent", "generatedAt": "2026-09-23T12:00:00Z"},
}
bom = BOMV1.model_validate(good)
print("Valid bom-v1 with", len(bom.line_items), "line item")

bad = dict(good, trade="hvac", lineItems=[{"id": "LI-001", "quantity": "lots"}])
try:
    BOMV1.model_validate(bad)
except ValidationError as err:
    print(f"\\nRejected, {err.error_count()} problems:")
    for e in err.errors():
        print("  ", ".".join(str(p) for p in e["loc"]), "-", e["msg"])
`;

export const PRESETS = [
  {
    id: 'define',
    label: 'Define an agent card',
    summary: 'Describe an agent by trade, CSI division and task type, and print the card other agents discover.',
    code: DEFINE,
  },
  {
    id: 'serve',
    label: 'Serve it and send a task',
    summary: 'Run a real A2AServer, send it a bom-v1 with TacoClient, and read back a typed estimate-v1.',
    code: SERVE,
  },
  {
    id: 'discover',
    label: 'Discover agents',
    summary: 'Register four agents and find the right one by task type, CSI division or trade.',
    code: DISCOVER,
  },
  {
    id: 'validate',
    label: 'Validate a schema',
    summary: 'Check a payload against bom-v1 and see exactly which fields a bad one gets wrong.',
    code: VALIDATE,
  },
];

/**
 * Packages installed with micropip before any code runs. taco-agent pins
 * protobuf<6 while Pyodide bundles protobuf 7, and micropip does not
 * backtrack, so the Google protobuf stack is pinned to versions that accept
 * protobuf 5. Re-test every preset when changing these.
 */
const PINS = [
  'protobuf==5.29.6',
  'googleapis-common-protos==1.75.0',
  'google-api-core==2.33.0',
  'proto-plus==1.28.2',
];

/** Pass no version for the latest release on PyPI. */
export function playgroundRequirements(sdkVersion) {
  return [...PINS, sdkVersion ? `taco-agent[server,client]==${sdkVersion}` : 'taco-agent[server,client]'];
}

export const PYODIDE_VERSION = '314.0.7';
