import {Fragment} from 'react';
import CodeBlock from '@theme/CodeBlock';

const steps = [
  {
    number: '1',
    title: 'Define Your Agent',
    desc: 'Declare your trade, capabilities, and schemas via a Construction Agent Card.',
    code: `card = ConstructionAgentCard(
    name="Mech Takeoff",
    trade="mechanical",
    csi_divisions=["22", "23"],
)`,
  },
  {
    number: '2',
    title: 'Discover Other Agents',
    desc: 'Query the registry by trade, task type, or CSI division to find collaborators.',
    code: `agents = registry.find(
    trade="electrical",
    task_type="estimate",
)`,
  },
  {
    number: '3',
    title: 'Communicate with Shared Schemas',
    desc: 'Send tasks and receive typed results using standard construction data schemas.',
    code: `task = await client.send_message(
    "estimate", bom_data
)
result = task.artifacts[0]`,
  },
];

function ArrowConnector() {
  return (
    <div className="how-it-works__connector">
      <svg viewBox="0 0 32 32">
        <line x1="4" y1="16" x2="26" y2="16" />
        <polyline points="20 10 26 16 20 22" />
      </svg>
    </div>
  );
}

export default function HowItWorks() {
  return (
    <div className="how-it-works">
      {steps.map((step, i) => (
        <Fragment key={step.number}>
          <div className="how-it-works__step">
            <div className="how-it-works__number">{step.number}</div>
            <div className="how-it-works__title">{step.title}</div>
            <div className="how-it-works__desc">{step.desc}</div>
            <div className="how-it-works__code">
              <CodeBlock language="python">{step.code}</CodeBlock>
            </div>
          </div>
          {i < steps.length - 1 && <ArrowConnector />}
        </Fragment>
      ))}
    </div>
  );
}
