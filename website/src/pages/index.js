import {useEffect, useRef} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import CodeBlock from '@theme/CodeBlock';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

import ArchitectureDiagram from '@site/src/components/ArchitectureDiagram';

function useScrollFadeIn() {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add('fade-in--visible');
          observer.unobserve(el);
        }
      },
      {threshold: 0.15},
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return ref;
}

function FadeIn({children, className = ''}) {
  const ref = useScrollFadeIn();
  return (
    <div ref={ref} className={`fade-in ${className}`}>
      {children}
    </div>
  );
}

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
          <a href="https://a2a-protocol.org">A2A (Agent-to-Agent) protocol</a>{' '}
          (Linux Foundation)
        </p>
      </div>
    </header>
  );
}

function StatsRow() {
  const stats = [
    {value: '18', label: 'Task Types'},
    {value: '6', label: 'Data Schemas'},
    {value: '16', label: 'CSI Divisions'},
    {value: '100%', label: 'A2A Compatible'},
  ];
  return (
    <section className="stats-section">
      <div className="container">
        <div className="stats-row">
          {stats.map((s) => (
            <div className="stat" key={s.label}>
              <div className="stat__value">{s.value}</div>
              <div className="stat__label">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ProblemSection() {
  return (
    <FadeIn>
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
    </FadeIn>
  );
}

function ClipboardIcon() {
  return (
    <svg viewBox="0 0 24 24">
      <rect x="8" y="2" width="8" height="4" rx="1" />
      <path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2" />
      <line x1="9" y1="12" x2="15" y2="12" />
      <line x1="9" y1="16" x2="13" y2="16" />
    </svg>
  );
}

function CodeBracketsIcon() {
  return (
    <svg viewBox="0 0 24 24">
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
      <line x1="14" y1="4" x2="10" y2="20" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
      <circle cx="11" cy="11" r="3" strokeDasharray="2 2" />
    </svg>
  );
}

function FeaturesSection() {
  return (
    <FadeIn>
      <section className="section section--alt">
        <div className="container">
          <Heading as="h2" className="section__heading">
            What TACO Standardizes
          </Heading>
          <div className="features">
            <div className="feature-card">
              <div className="feature-card__icon"><ClipboardIcon /></div>
              <div className="feature-card__title">Task Types</div>
              <div className="feature-card__desc">
                A typed vocabulary of construction workflows — takeoff, estimate,
                rfi-generation, submittal-review, schedule-coordination, and more.
              </div>
            </div>
            <div className="feature-card">
              <div className="feature-card__icon"><CodeBracketsIcon /></div>
              <div className="feature-card__title">Data Schemas</div>
              <div className="feature-card__desc">
                Typed JSON schemas for construction artifacts — bom-v1, rfi-v1,
                estimate-v1, schedule-v1. Output from one agent is valid input for
                the next.
              </div>
            </div>
            <div className="feature-card">
              <div className="feature-card__icon"><SearchIcon /></div>
              <div className="feature-card__title">Agent Discovery</div>
              <div className="feature-card__desc">
                Find agents by trade, CSI division, project type, and platform
                integration. Construction extensions to A2A Agent Cards.
              </div>
            </div>
          </div>
        </div>
      </section>
    </FadeIn>
  );
}

function DiagramSection() {
  return (
    <FadeIn>
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
    </FadeIn>
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
    <FadeIn>
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
              <code>pip install taco-agent</code>
            </div>
          </div>
        </div>
      </section>
    </FadeIn>
  );
}

const principles = [
  {
    marker: '01',
    title: 'Ontology, not protocol.',
    desc: 'TACO builds on A2A using its native extension points. Every TACO agent is a standard A2A agent.',
  },
  {
    marker: '02',
    title: 'Agents are opaque.',
    desc: 'Collaborate without exposing internals. Pricing models and trade secrets stay private.',
  },
  {
    marker: '03',
    title: 'Open and composable.',
    desc: 'Apache 2.0. The spec, schemas, and SDK are open source.',
  },
  {
    marker: '04',
    title: 'Construction-native.',
    desc: 'Designed for how construction works — by trade, CSI division, project phase, and platform.',
  },
];

function PrinciplesSection() {
  return (
    <FadeIn>
      <section className="section">
        <div className="container">
          <Heading as="h2" className="section__heading">
            Principles
          </Heading>
          <div className="principles">
            {principles.map((p) => (
              <div className="principle" key={p.marker}>
                <div className="principle__marker">{p.marker}</div>
                <div className="principle__title">{p.title}</div>
                <div className="principle__desc">{p.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </FadeIn>
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
          Initiated by <a href="https://pelles.ai">Pelles</a> | Apache 2.0
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
      <StatsRow />
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
