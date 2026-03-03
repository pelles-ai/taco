import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import CodeBlock from '@theme/CodeBlock';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

import ArchitectureDiagram from '@site/src/components/ArchitectureDiagram';

function HeroSection() {
  return (
    <header className="hero--taco">
      <div className="container">
        <Heading as="h1" className="hero__title">
          TACO
        </Heading>
        <p className="hero__subtitle">The A2A Construction Open-standard</p>
        <p className="hero__oneliner">
          Every construction tool should be agent-compatible. TACO gives them a
          shared language. Open spec. Open schemas. Open SDK.
        </p>
        <div className="hero__buttons">
          <Link
            className="button button--lg button--accent"
            to="/docs/intro">
            Read the Docs
          </Link>
          <Link
            className="button button--lg button--outline-light"
            href="https://github.com/pelles-ai/taco">
            View on GitHub
          </Link>
        </div>
        <p className="hero__note">
          Built on the{' '}
          <a
            href="https://a2a-protocol.org"
            style={{color: 'rgba(255,255,255,0.8)'}}>
            A2A protocol
          </a>{' '}
          (Linux Foundation)
        </p>
      </div>
    </header>
  );
}

function ProblemSection() {
  return (
    <section className="section">
      <div className="container">
        <Heading as="h2" className="section__heading">
          Construction software needs to communicate like the people using it
        </Heading>
        <p className="problem-text">
          A project superintendent coordinates across dozens of trades,
          tools, and companies every day. The software they use should be able
          to do the same. Whether it's a fully autonomous AI agent or an
          existing platform with an agent sidecar, every construction tool
          needs to speak a common language — reporting status, sharing
          generated content, and coordinating work across the project.
        </p>
        <p className="problem-text" style={{marginTop: '1rem'}}>
          Today, AI agents are entering the construction ecosystem fast —
          generating takeoffs, drafting RFIs, coordinating schedules — but
          they're being built in isolation. Different formats, different APIs,
          no shared vocabulary. TACO fixes this by giving every tool, agent,
          and platform one standard way to interoperate.
        </p>
      </div>
    </section>
  );
}

function FeaturesSection() {
  return (
    <section className="section section--alt">
      <div className="container">
        <Heading as="h2" className="section__heading">
          What TACO Standardizes
        </Heading>
        <div className="features">
          <div className="feature-card">
            <div className="feature-card__icon">&#128203;</div>
            <div className="feature-card__title">Task Types</div>
            <div className="feature-card__desc">
              A typed vocabulary of construction workflows — takeoff, estimate,
              rfi-generation, submittal-review, schedule-coordination, and more.
            </div>
          </div>
          <div className="feature-card">
            <div className="feature-card__icon">&#123;&#125;</div>
            <div className="feature-card__title">Data Schemas</div>
            <div className="feature-card__desc">
              Typed JSON schemas for construction artifacts — bom-v1, rfi-v1,
              estimate-v1, schedule-v1. Output from one agent is valid input for
              the next.
            </div>
          </div>
          <div className="feature-card">
            <div className="feature-card__icon">&#128269;</div>
            <div className="feature-card__title">Agent Discovery</div>
            <div className="feature-card__desc">
              Find agents by trade, CSI division, project type, and platform
              integration. Construction extensions to A2A Agent Cards.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function DiagramSection() {
  return (
    <section className="section">
      <div className="container">
        <Heading as="h2" className="section__heading">
          How It Works
        </Heading>
        <div className="diagram-container">
          <ArchitectureDiagram />
        </div>
        <p className="diagram-caption">
          Different companies. Different AI models. One shared language.
        </p>
      </div>
    </section>
  );
}

const exposeCode = `from taco import ConstructionAgentCard, ConstructionSkill

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

card.serve(host="0.0.0.0", port=8080)`;

const discoverCode = `from taco import TacoClient, AgentRegistry

# Discover agents by trade and capability
registry = AgentRegistry()
await registry.register("http://estimator:8001")

agents = registry.find(trade="mechanical", task_type="estimate")

# Send a task to the first matching agent
async with TacoClient(agent_url=agents[0].url) as client:
    task = await client.send_message("estimate", bom_data)
    estimate = task.artifacts[0].parts[0].structured_data`;

function QuickStartSection() {
  return (
    <section className="section section--alt">
      <div className="container">
        <Heading as="h2" className="section__heading">
          Quick Start
        </Heading>
        <div className="code-section">
          <Tabs>
            <TabItem value="expose" label="Expose your agent" default>
              <CodeBlock language="python">{exposeCode}</CodeBlock>
            </TabItem>
            <TabItem value="discover" label="Discover & call agents">
              <CodeBlock language="python">{discoverCode}</CodeBlock>
            </TabItem>
          </Tabs>
          <div className="install-badge">
            <code>pip install taco</code>
          </div>
        </div>
      </div>
    </section>
  );
}

function PrinciplesSection() {
  return (
    <section className="section">
      <div className="container">
        <Heading as="h2" className="section__heading">
          Principles
        </Heading>
        <div className="principles">
          <div className="principle">
            <div className="principle__title">Ontology, not protocol.</div>
            <div className="principle__desc">
              TACO builds on A2A using its native extension points. Every TACO
              agent is a standard A2A agent.
            </div>
          </div>
          <div className="principle">
            <div className="principle__title">Agents are opaque.</div>
            <div className="principle__desc">
              Collaborate without exposing internals. Pricing models and trade
              secrets stay private.
            </div>
          </div>
          <div className="principle">
            <div className="principle__title">Open and composable.</div>
            <div className="principle__desc">
              Apache 2.0. The spec, schemas, and SDK are open source.
            </div>
          </div>
          <div className="principle">
            <div className="principle__title">Construction-native.</div>
            <div className="principle__desc">
              Designed for how construction works — by trade, CSI division,
              project phase, and platform.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <section className="cta-section">
      <div className="container">
        <Heading as="h2">Shape the Standard</Heading>
        <p>
          TACO is early stage. We're looking for construction technology
          companies, trade contractors, GCs, and platform vendors to help define
          the schemas and build the ecosystem.
        </p>
        <Link
          className="button button--lg button--accent"
          href="https://github.com/pelles-ai/taco">
          View on GitHub
        </Link>
        <div className="cta-note">
          Initiated by <a href="https://pelles.ai" style={{color: 'rgba(255,255,255,0.7)'}}>Pelles</a> | Apache 2.0
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  return (
    <Layout
      title="The A2A Construction Open-standard"
      description="TACO is an open standard for AI agent communication in the built environment. Task types, data schemas, and agent discovery for construction.">
      <HeroSection />
      <main>
        <ProblemSection />
        <FeaturesSection />
        <DiagramSection />
        <QuickStartSection />
        <PrinciplesSection />
      </main>
      <CTASection />
    </Layout>
  );
}
