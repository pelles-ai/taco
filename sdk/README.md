# taco-agent

The Python SDK for **TACO — The A2A Construction Open-standard**: an open
vocabulary that lets construction AI agents hand work to each other. TACO
adds typed task types, typed data schemas and discovery by trade and CSI
division on top of the [A2A protocol](https://a2a-protocol.org) (Linux
Foundation). Every TACO agent is a standard A2A agent.

```bash
pip install taco-agent[all]
```

## Expose an agent

```python
from taco import ConstructionAgentCard, ConstructionSkill

card = ConstructionAgentCard(
    name="My Mechanical Takeoff Agent",
    trade="mechanical",
    csi_divisions=["22", "23"],
    skills=[
        ConstructionSkill(
            id="generate-bom",
            task_type="takeoff",
            output_schema="bom-v1",
        )
    ],
)

# Serve the agent card for discovery
card.serve(host="0.0.0.0", port=8080)
```

## Discover and call agents

```python
from taco import TacoClient, AgentRegistry, extract_structured_data

registry = AgentRegistry()
await registry.register("http://estimator:8001")
agents = registry.find(trade="mechanical", task_type="estimate")

async with TacoClient(agent_url=agents[0].url) as client:
    task = await client.send_message("estimate", bom_data)
    estimate = extract_structured_data(task.artifacts[0].parts[0])
```

## Learn more

- Documentation: https://taco-protocol.com
- Specification, schemas and task types: https://github.com/pelles-ai/taco/tree/main/spec
- Source and issues: https://github.com/pelles-ai/taco
- Changelog: https://github.com/pelles-ai/taco/blob/main/CHANGELOG.md

Apache 2.0. Initiated by [Pelles](https://pelles.ai).
