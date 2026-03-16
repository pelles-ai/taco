import {Fragment, useEffect, useRef, useState} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import CodeBlock from '@theme/CodeBlock';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

import ArchitectureDiagram from '@site/src/components/ArchitectureDiagram';
import CopyButton from '@site/src/components/CopyButton';
import CountUpStats from '@site/src/components/CountUpStats';
import HowItWorks from '@site/src/components/HowItWorks';
import AudiencePaths from '@site/src/components/AudiencePaths';

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

/* ============================================================
   1. Hero
   ============================================================ */

function HeroSection() {
  return (
    <header className="hero--taco">
      <div className="container">
        <a
          className="hero__github-badge"
          href="https://github.com/pelles-ai/taco"
          target="_blank"
          rel="noopener noreferrer">
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
          Star on GitHub
        </a>

        <Heading as="h1" className="hero__title">
          One Language for Every
          <br />
          Construction Agent
        </Heading>
        <p className="hero__subtitle">
          The superintendent's vocabulary, machine-readable
        </p>
        <p className="hero__oneliner">
          TACO is an open-source construction ontology built on the{' '}
          <a href="https://a2a-protocol.org">A2A protocol</a> (Linux Foundation).
          It gives every agent — autonomous or sidecar — a common language for
          tasks, data, and discovery.
        </p>

        <div className="hero__install">
          <code>pip install taco-agent</code>
          <CopyButton text="pip install taco-agent" />
        </div>

        <div className="hero__buttons">
          <Link
            className="button button--lg button--accent"
            to="/docs/getting-started/build-agent">
            Get Started
          </Link>
          <Link
            className="button button--lg button--outline-light"
            href="https://github.com/pelles-ai/taco">
            GitHub
          </Link>
        </div>
      </div>
    </header>
  );
}

/* ============================================================
   Logo Strip — "Built on"
   ============================================================ */

function LogoStrip() {
  const links = [
    {label: 'A2A Protocol', href: 'https://a2a-protocol.org'},
    {label: 'Linux Foundation', href: 'https://www.linuxfoundation.org/'},
    {label: 'Python', href: 'https://python.org'},
    {label: 'FastAPI', href: 'https://fastapi.tiangolo.com'},
    {label: 'Pydantic', href: 'https://docs.pydantic.dev'},
  ];

  return (
    <div className="logo-strip">
      <div className="container">
        <span className="logo-strip__label">Built on</span>
        <div className="logo-strip__logos">
          {links.map((l, i) => (
            <Fragment key={l.label}>
              <a
                href={l.href}
                target="_blank"
                rel="noopener noreferrer"
                className="logo-strip__link">
                {l.label}
              </a>
              {i < links.length - 1 && (
                <span className="logo-strip__separator" />
              )}
            </Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   2. The Problem
   ============================================================ */

function TheProblemSection() {
  return (
    <FadeIn>
      <section className="section">
        <div className="container">
          <Heading as="h2" className="section__heading">
            The Problem
          </Heading>
          <div className="what-is-taco">
            <p>
              Construction AI agents are being built in isolation.
              Different APIs, different schemas, no shared vocabulary.
              Every integration is custom — <strong>REST, gRPC, SOAP,
              GraphQL, WebSocket</strong> — with no way for agents to
              discover each other, exchange typed data, or establish trust.
            </p>
          </div>
          <div className="problem-grid">
            <div className="problem-grid__item">
              <div className="problem-grid__icon">
                <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>
              </div>
              <div className="problem-grid__label">No discovery</div>
            </div>
            <div className="problem-grid__item">
              <div className="problem-grid__icon">
                <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>
              </div>
              <div className="problem-grid__label">Incompatible schemas</div>
            </div>
            <div className="problem-grid__item">
              <div className="problem-grid__icon">
                <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>
              </div>
              <div className="problem-grid__label">Manual integration</div>
            </div>
            <div className="problem-grid__item">
              <div className="problem-grid__icon">
                <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>
              </div>
              <div className="problem-grid__label">Zero trust model</div>
            </div>
          </div>
        </div>
      </section>
    </FadeIn>
  );
}

/* ============================================================
   What TACO Standardizes — comparison table
   ============================================================ */

const standardizationRows = [
  {
    dimension: 'Agent Identity',
    a2a: 'Generic name, URL, freeform skills',
    taco: 'Trade, CSI divisions, project types, platform integrations',
  },
  {
    dimension: 'Skills',
    a2a: 'Freeform description text',
    taco: 'Typed taskType, inputSchema, outputSchema per skill',
  },
  {
    dimension: 'Data Exchange',
    a2a: 'structuredData (any JSON, unvalidated)',
    taco: '6 typed schemas with cross-references between artifacts',
  },
  {
    dimension: 'Task Types',
    a2a: 'Generic messaging',
    taco: '18 named construction workflows organized by project phase',
  },
  {
    dimension: 'Authorization',
    a2a: '5 auth mechanisms (apiKey through mTLS)',
    taco: 'Scope taxonomy, trust tiers, token delegation',
  },
  {
    dimension: 'Discovery',
    a2a: 'Manual /.well-known/agent.json lookup',
    taco: 'Queryable registry filtered by trade, task type, CSI division',
  },
];

function StandardizationSection() {
  return (
    <FadeIn>
      <section className="section section--alt">
        <div className="container">
          <Heading as="h2" className="section__heading">
            What TACO Standardizes
          </Heading>
          <p className="section__subheading">
            A2A provides the transport. TACO adds construction semantics at every layer.
          </p>
          <div className="standardization-table-wrap">
            <table className="standardization-table">
              <thead>
                <tr>
                  <th>Dimension</th>
                  <th>A2A (generic)</th>
                  <th>TACO adds</th>
                </tr>
              </thead>
              <tbody>
                {standardizationRows.map((row) => (
                  <tr key={row.dimension}>
                    <td className="standardization-table__dim" data-label="Dimension">{row.dimension}</td>
                    <td className="standardization-table__a2a" data-label="A2A (generic)">{row.a2a}</td>
                    <td className="standardization-table__taco" data-label="TACO adds">{row.taco}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="standardization-note">
            Every TACO agent is a valid A2A agent. Non-TACO clients ignore the
            extensions gracefully. Zero lock-in — just richer context for construction.
          </p>
        </div>
      </section>
    </FadeIn>
  );
}

/* ============================================================
   Ecosystem Positioning
   ============================================================ */

function EcosystemSection() {
  return (
    <FadeIn>
      <section className="section section--alt">
        <div className="container">
          <Heading as="h2" className="section__heading">
            Where TACO Fits
          </Heading>
          <p className="section__subheading">
            A2A handles communication. MCP connects tools. TACO adds
            construction intelligence.
          </p>
          <div className="ecosystem-stack">
            <div className="ecosystem-layer ecosystem-layer--taco">
              <div className="ecosystem-layer__label">TACO</div>
              <div className="ecosystem-layer__desc">
                Task types, data schemas, agent discovery
              </div>
            </div>
            <div className="ecosystem-layer ecosystem-layer--a2a">
              <div className="ecosystem-layer__label">A2A Protocol</div>
              <div className="ecosystem-layer__desc">
                Agent-to-agent messaging, task lifecycle, streaming
              </div>
            </div>
            <div className="ecosystem-layer ecosystem-layer--transport">
              <div className="ecosystem-layer__label">HTTP / JSON-RPC</div>
              <div className="ecosystem-layer__desc">
                Transport layer
              </div>
            </div>
          </div>
        </div>
      </section>
    </FadeIn>
  );
}

/* ============================================================
   3. Three Pillars (Features)
   ============================================================ */

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
            Three Pillars
          </Heading>
          <p className="section__subheading">
            Everything a construction agent needs to interoperate.
          </p>
          <div className="features">
            <div className="feature-card feature-card--task-types">
              <div className="feature-card__icon feature-card__icon--lg">
                <ClipboardIcon />
              </div>
              <div className="feature-card__title">Task Types</div>
              <div className="feature-card__desc">
                A typed vocabulary of construction workflows — takeoff, estimate,
                rfi-generation, submittal-review, schedule-coordination, and more.
              </div>
              <Link className="feature-card__link" to="/docs/task-types">
                Learn more &rarr;
              </Link>
            </div>
            <div className="feature-card feature-card--schemas">
              <div className="feature-card__icon feature-card__icon--lg">
                <CodeBracketsIcon />
              </div>
              <div className="feature-card__title">Data Schemas</div>
              <div className="feature-card__desc">
                Typed JSON schemas for construction artifacts — bom-v1, rfi-v1,
                estimate-v1, schedule-v1. Output from one agent is valid input for
                the next.
              </div>
              <Link className="feature-card__link" to="/docs/schemas/">
                Learn more &rarr;
              </Link>
            </div>
            <div className="feature-card feature-card--discovery">
              <div className="feature-card__icon feature-card__icon--lg">
                <SearchIcon />
              </div>
              <div className="feature-card__title">Agent Discovery</div>
              <div className="feature-card__desc">
                Find agents by trade, CSI division, project type, and platform
                integration. Construction extensions to A2A Agent Cards.
              </div>
              <Link
                className="feature-card__link"
                to="/docs/agent-card-extensions">
                Learn more &rarr;
              </Link>
            </div>
          </div>
        </div>
      </section>
    </FadeIn>
  );
}

/* ============================================================
   4. How It Works
   ============================================================ */

function HowItWorksSection() {
  return (
    <FadeIn>
      <section className="section">
        <div className="container">
          <Heading as="h2" className="section__heading">
            How It Works
          </Heading>
          <p className="section__subheading">
            Define. Discover. Communicate. Three steps to agent interoperability.
          </p>
          <HowItWorks />
        </div>
      </section>
    </FadeIn>
  );
}

/* ============================================================
   5. Architecture Diagram
   ============================================================ */

function DiagramSection() {
  return (
    <FadeIn>
      <section className="section section--alt">
        <div className="container">
          <Heading as="h2" className="section__heading">
            Architecture
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

/* ============================================================
   6. Quick Start Code
   ============================================================ */

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

# Serve the agent card for discovery
card.serve(host="0.0.0.0", port=8080)`;

const discoverCode = `from taco import TacoClient, AgentRegistry, extract_structured_data

# Discover agents by trade and capability
registry = AgentRegistry()
await registry.register("http://estimator:8001")

agents = registry.find(trade="mechanical", task_type="estimate")

# Send a task to the first matching agent
async with TacoClient(agent_url=agents[0].url) as client:
    task = await client.send_message("estimate", bom_data)
    estimate = extract_structured_data(task.artifacts[0].parts[0])`;

const installCommands = [
  {label: 'pip', value: 'pip', cmd: 'pip install taco-agent'},
  {label: 'uv', value: 'uv', cmd: 'uv add taco-agent'},
  {label: 'poetry', value: 'poetry', cmd: 'poetry add taco-agent'},
];

function InstallTabs() {
  const [active, setActive] = useState('pip');
  const activeCmd = installCommands.find((c) => c.value === active);

  return (
    <div className="install-badge">
      <div className="install-tabs">
        {installCommands.map((c) => (
          <button
            key={c.value}
            className={`install-tabs__tab ${active === c.value ? 'install-tabs__tab--active' : ''}`}
            onClick={() => setActive(c.value)}>
            {c.label}
          </button>
        ))}
      </div>
      <div className="install-tabs__cmd">
        <code>{activeCmd.cmd}</code>
        <CopyButton text={activeCmd.cmd} />
      </div>
    </div>
  );
}

function QuickStartSection() {
  return (
    <FadeIn>
      <section className="section">
        <div className="container">
          <Heading as="h2" className="section__heading">
            Quick Start
          </Heading>
          <p className="section__subheading">
            Get up and running in under a minute.
          </p>
          <div className="code-section">
            <Tabs>
              <TabItem value="expose" label="Expose your agent" default>
                <CodeBlock language="python">{exposeCode}</CodeBlock>
              </TabItem>
              <TabItem value="discover" label="Discover & call agents">
                <CodeBlock language="python">{discoverCode}</CodeBlock>
              </TabItem>
            </Tabs>
            <InstallTabs />
          </div>
        </div>
      </section>
    </FadeIn>
  );
}

/* ============================================================
   7. Stats Row (count-up)
   ============================================================ */

function StatsSection() {
  return (
    <FadeIn className="">
      <CountUpStats />
    </FadeIn>
  );
}

/* ============================================================
   8. Get Started Paths
   ============================================================ */

function AudienceSection() {
  return (
    <FadeIn>
      <section className="section section--alt">
        <div className="container">
          <Heading as="h2" className="section__heading">
            Get Started
          </Heading>
          <p className="section__subheading">
            Choose the path that fits your role.
          </p>
          <AudiencePaths />
        </div>
      </section>
    </FadeIn>
  );
}

/* ============================================================
   Design Principles
   ============================================================ */

const principles = [
  {
    marker: 'Principle 01',
    title: 'Ontology, not protocol',
    desc: 'TACO builds on A2A using its native extension points. It does not fork or modify the underlying protocol.',
  },
  {
    marker: 'Principle 02',
    title: 'Agents are opaque',
    desc: 'TACO defines what goes in and what comes out. Agents collaborate without exposing their internals.',
  },
  {
    marker: 'Principle 03',
    title: 'Open and composable',
    desc: 'Apache 2.0 licensed. Every schema, task type, and extension is public and community-driven.',
  },
  {
    marker: 'Principle 04',
    title: 'Construction-native',
    desc: 'Designed for trade, CSI division, project phase, and platform — not retrofitted from another domain.',
  },
];

function PrinciplesSection() {
  return (
    <FadeIn>
      <section className="section">
        <div className="container">
          <Heading as="h2" className="section__heading">
            Design Principles
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

/* ============================================================
   9. CTA
   ============================================================ */

function CTASection() {
  return (
    <section className="cta-section">
      <div className="container">
        <Heading as="h2">Shape the Standard</Heading>
        <p>
          TACO is in active development. We're looking for construction technology
          companies, trade contractors, GCs, and platform vendors to help define
          the schemas and build the ecosystem.
        </p>
        <div className="cta-buttons">
          <Link
            className="button button--lg button--accent"
            href="https://github.com/pelles-ai/taco">
            Star on GitHub
          </Link>
          <Link
            className="button button--lg button--outline-light"
            href="https://github.com/pelles-ai/taco/discussions">
            Join the Discussion
          </Link>
        </div>
        <div className="cta-note">
          Initiated by <a href="https://pelles.ai">Pelles</a> | Apache 2.0 |
          Built on <a href="https://a2a-protocol.org">A2A</a> (Linux Foundation)
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   Page
   ============================================================ */

export default function Home() {
  return (
    <Layout
      title="One Language for Every Construction Agent"
      description="TACO is an open standard for AI agent communication in the built environment. Task types, data schemas, and agent discovery for construction.">
      <HeroSection />
      <LogoStrip />
      <main>
        <TheProblemSection />
        <StandardizationSection />
        <EcosystemSection />
        <FeaturesSection />
        <HowItWorksSection />
        <DiagramSection />
        <QuickStartSection />
        <StatsSection />
        <PrinciplesSection />
        <AudienceSection />
      </main>
      <CTASection />
    </Layout>
  );
}
