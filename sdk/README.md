# taco-agent

The Python SDK for **TACO — The A2A Construction Open-standard**: an open
vocabulary that lets construction AI agents hand work to each other. TACO
adds typed task types, typed data schemas and discovery by trade and CSI
division on top of the [A2A protocol](https://a2a-protocol.org) (Linux
Foundation). Every TACO agent is a standard A2A agent.

```bash
pip install "taco-agent[all]"
```

The quotes keep shells such as zsh from expanding the brackets. `[all]` brings the server (with `uvicorn`), the client and the `taco` CLI; `[server]` and `[client]` install one side.

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

To handle tasks as well, run an `A2AServer` instead of `card.serve()`:

```python
import uvicorn
from taco import A2AServer, make_artifact, make_data_part

server = A2AServer(card)  # token_verifier=... to require bearer tokens


async def takeoff(task, input_data):
    bom = build_bom(input_data)  # your takeoff logic, returning a bom-v1 dict
    return make_artifact(parts=[make_data_part(bom)], name="bom")


server.register_handler("takeoff", takeoff)
uvicorn.run(server.app, host="0.0.0.0", port=8080)
```

## Discover and call agents

```python
from taco import TacoClient, AgentRegistry, extract_structured_data

registry = AgentRegistry()
await registry.register("http://estimator:8001")
agents = registry.find(trade="mechanical", task_type="estimate")

# Call the URL the agent was registered at, not the url its card declares
url = next(url for url, card in registry.entries() if card is agents[0])
async with TacoClient(agent_url=url) as client:
    task = await client.send_message("estimate", bom_data)
    estimate = extract_structured_data(task.artifacts[0].parts[0])
```

## Learn more

- Documentation: https://taco-protocol.com
- Specification, schemas and task types: https://github.com/pelles-ai/taco/tree/main/spec
- Source and issues: https://github.com/pelles-ai/taco
- Changelog: https://github.com/pelles-ai/taco/blob/main/CHANGELOG.md

Apache 2.0. Initiated by [Pelles](https://pelles.ai).
