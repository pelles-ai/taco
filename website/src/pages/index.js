import {useState} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import CodeBlock from '@theme/CodeBlock';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';

import CopyButton from '@site/src/components/CopyButton';
import SequenceDiagram from '@site/src/components/SequenceDiagram';

const GITHUB = 'https://github.com/pelles-ai/taco';

/* ------------------------------------------------------------------
   Shared: section header in the manner of a drawing-sheet header.
   The label names the sheet; the rule runs to the edge.
   ------------------------------------------------------------------ */

function SheetHead({label, meta, title, lede}) {
  return (
    <div className="sheet-head">
      <div className="sheet-head__rule">
        <span className="sheet-head__label">{label}</span>
        {meta ? <span className="sheet-head__meta">{meta}</span> : null}
      </div>
      <Heading as="h2" className="sheet-head__title">
        {title}
      </Heading>
      {lede ? <p className="sheet-head__lede">{lede}</p> : null}
    </div>
  );
}

/* ------------------------------------------------------------------
   1. Hero and title block
   ------------------------------------------------------------------ */

function TitleBlock({sdkVersion, protocolVersion, taskTypeCount, schemaCount}) {
  const rows = [
    {k: 'Protocol', v: `TACO ${protocolVersion}`, to: '/docs/core-concepts'},
    {k: 'SDK', v: `taco-agent ${sdkVersion}`, href: 'https://pypi.org/project/taco-agent/'},
    {k: 'License', v: 'Apache 2.0', href: `${GITHUB}/blob/main/LICENSE`},
    {k: 'Built on', v: 'A2A protocol · Linux Foundation', href: 'https://a2a-protocol.org'},
    {k: 'Task types', v: `${taskTypeCount}, organized by project phase`, to: '/docs/task-types'},
    {k: 'Data schemas', v: `${schemaCount}, cross-referenced`, to: '/docs/schemas/'},
    {k: 'Discovery', v: 'trade · CSI division · platform', to: '/docs/agent-card-extensions'},
    {k: 'Security', v: 'scopes · trust tiers · delegation', to: '/docs/security'},
  ];

  return (
    <aside className="titleblock" aria-label="TACO at a glance">
      <div className="titleblock__head">
        <div>
          <div className="titleblock__name">TACO</div>
          <div className="titleblock__expansion">The A2A Construction Open-standard</div>
        </div>
        <div className="titleblock__rev">
          <span className="titleblock__rev-label">Rev</span>
          <span className="titleblock__rev-value">{sdkVersion}</span>
        </div>
      </div>
      <dl className="titleblock__rows">
        {rows.map((r) => (
          <div className="titleblock__row" key={r.k}>
            <dt>{r.k}</dt>
            <dd>
              {r.href ? (
                <a href={r.href} target="_blank" rel="noopener noreferrer">
                  {r.v}
                </a>
              ) : (
                <Link to={r.to}>{r.v}</Link>
              )}
            </dd>
          </div>
        ))}
      </dl>
      <div className="titleblock__foot">
        <span>
          Initiated by{' '}
          <a href="https://pelles.ai" target="_blank" rel="noopener noreferrer">
            Pelles
          </a>
        </span>
        <Link to="/docs/changelog">Revision history</Link>
      </div>
    </aside>
  );
}

function Hero(props) {
  return (
    <header className="hero">
      <div className="container hero__grid">
        <div className="hero__copy">
          <p className="eyebrow">
            Open standard · Protocol {props.protocolVersion} · Apache 2.0 · Built on A2A
          </p>
          <Heading as="h1" className="hero__title">
            One vocabulary for every construction agent.
          </Heading>
          <p className="hero__lede">
            TACO is an open standard on top of the A2A protocol. It gives AI agents,
            and the platforms behind them, the same typed task types, data schemas
            and discovery by trade and CSI division. An estimator built by one
            company can hand a bill of materials to a supplier agent built by
            another, and both know exactly what it means.
          </p>

          <div className="hero__install">
            <span className="hero__prompt" aria-hidden="true">
              $
            </span>
            <code>pip install taco-agent</code>
            <CopyButton text="pip install taco-agent" />
          </div>

          <div className="hero__actions">
            <Link className="btn btn--primary" to="/docs/getting-started/build-agent">
              Build your first agent
            </Link>
            <a
              className="btn btn--ghost"
              href={`${GITHUB}/tree/main/spec`}
              target="_blank"
              rel="noopener noreferrer">
              Read the spec
            </a>
          </div>
          <p className="hero__aside">
            New to agent protocols? <a href="#stack">Start with the three-protocol explainer</a>.
          </p>
        </div>
        <TitleBlock {...props} />
      </div>
    </header>
  );
}

/* ------------------------------------------------------------------
   2. General notes: what TACO is and is not
   Numbered, because general notes on a drawing set are numbered and
   referenced by number.
   ------------------------------------------------------------------ */

const generalNotes = [
  {
    title: 'An ontology on A2A, not a new protocol.',
    body: 'TACO uses A2A’s native extension points. Every TACO agent is a valid A2A agent, and clients that don’t know TACO ignore the extensions.',
  },
  {
    title: 'What goes in and what comes out. Never how.',
    body: 'TACO types the inputs and outputs of a task. Agents stay opaque; how one produces an estimate is its own business.',
  },
  {
    title: 'Not a replacement for the platforms you run.',
    body: 'Procore, Autodesk Construction Cloud, Bluebeam and your homegrown tools stay where they are. A sidecar makes them discoverable and callable as agents.',
  },
  {
    title: 'AI is optional.',
    body: 'A sidecar in front of legacy software, a human-in-the-loop tool, an adapter for a scheduling engine: if it speaks A2A and follows the schemas, it is a TACO agent.',
  },
  {
    title: 'Construction-native fields, not tags.',
    body: 'Trade, CSI division, project phase and platform integration are first-class in the agent card, so discovery and scopes can use them.',
  },
  {
    title: 'Open, and written in public.',
    body: 'Apache 2.0. Every task type, schema and extension is proposed, discussed and versioned on GitHub.',
  },
];

function GeneralNotes() {
  return (
    <section className="sheet" id="notes">
      <div className="container">
        <SheetHead
          label="General notes"
          meta="Apply throughout"
          title="What TACO is, and what it is not."
        />
        <ol className="notes">
          {generalNotes.map((n, i) => (
            <li className="note" key={n.title}>
              <span className="note__num">{String(i + 1).padStart(2, '0')}</span>
              <div>
                <div className="note__title">{n.title}</div>
                <p className="note__body">{n.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   3. The problem, as pairs: what happens today, what TACO replaces it with
   ------------------------------------------------------------------ */

const pairs = [
  {
    now: 'Agents can’t find each other.',
    taco: 'A registry you can query by trade, task type and CSI division.',
    to: '/docs/agent-card-extensions',
    label: 'Agent discovery',
  },
  {
    now: 'Every schema is different.',
    taco: 'Six typed schemas that reference each other: bom-v1, rfi-v1, estimate-v1, schedule-v1, quote-v1, change-order-v1.',
    to: '/docs/schemas/',
    label: 'Data schemas',
  },
  {
    now: 'Every integration is a one-off mapping.',
    taco: 'One A2A endpoint per agent. Platforms join with a sidecar instead of a rewrite.',
    to: '/docs/getting-started/integrate-platform',
    label: 'Integrate a platform',
  },
  {
    now: 'No way to scope trust across companies.',
    taco: 'Construction-shaped scopes and trust tiers: taco:trade:mechanical, taco:project:PRJ-0042:write.',
    to: '/docs/security',
    label: 'Security model',
  },
];

function Problem() {
  return (
    <section className="sheet sheet--alt" id="problem">
      <div className="container">
        <SheetHead
          label="The problem"
          title="Every tool ships its own RFI."
          lede="Procore’s RFI is not Autodesk’s RFI. Your estimator’s BOM is not your supplier’s BOM. Every integration is a one-off mapping, and an AI agent inherits every one of them."
        />
        <div className="pairs">
          <div className="pairs__head" aria-hidden="true">
            <span>Today</span>
            <span />
            <span>With TACO</span>
          </div>
          {pairs.map((p) => (
            <div className="pair" key={p.now}>
              <div className="pair__now">{p.now}</div>
              <div className="pair__arrow" aria-hidden="true">
                <svg viewBox="0 0 32 12">
                  <line x1="0" y1="6" x2="28" y2="6" />
                  <polyline points="23 1 29 6 23 11" />
                </svg>
              </div>
              <div className="pair__taco">
                <p>{p.taco}</p>
                <Link to={p.to}>{p.label} &rarr;</Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   4. How TACO fits with A2A and MCP
   Top of the stack first, as on a protocol-stack diagram.
   ------------------------------------------------------------------ */

const stackLayers = [
  {
    badge: 'TACO',
    tone: 'taco',
    job: 'Vocabulary',
    analogy: 'The trade vocabulary.',
    title: 'What construction agents know',
    body: 'The shared dictionary every construction agent uses: what a takeoff is, what a BOM looks like, what Division 23 means.',
    href: '/docs/core-concepts',
    hrefLabel: 'Core concepts',
  },
  {
    badge: 'A2A',
    tone: 'a2a',
    job: 'Transport',
    analogy: 'The jobsite radio.',
    title: 'How agents talk to each other',
    body: 'The protocol that lets one agent send a task to another. Like a two-way radio, it does not care what trade you are, only that the channel is open.',
    href: 'https://a2a-protocol.org',
    hrefLabel: 'A2A protocol',
  },
  {
    badge: 'MCP',
    tone: 'mcp',
    job: 'Tools',
    analogy: 'The toolbox.',
    title: 'How an agent reaches its own tools',
    body: 'How a single agent picks up tools and reaches into data: Procore, AutoCAD, a database, a calculator. Each agent has its own toolbox.',
    href: 'https://modelcontextprotocol.io',
    hrefLabel: 'Model Context Protocol',
  },
];

function Stack() {
  return (
    <section className="sheet" id="stack">
      <div className="container">
        <SheetHead
          label="Three protocols, three jobs"
          title="How TACO fits with A2A and MCP."
          lede="Plain language first. A2A moves the message between agents. MCP lets each agent reach its own tools. TACO is the shared construction vocabulary the message is written in."
        />
        <div className="stack">
          <div className="stack__layers" aria-hidden="true">
            {stackLayers.map((l) => (
              <div className={`layer layer--${l.tone}`} key={l.badge}>
                <span className="layer__job">{l.job}</span>
                <span className="layer__badge">{l.badge}</span>
                <span className="layer__analogy">{l.analogy}</span>
              </div>
            ))}
            <div className="stack__caption">Protocol stack, top to bottom</div>
          </div>
          <ol className="stack__notes">
            {stackLayers.map((l) => (
              <li className={`stack-note stack-note--${l.tone}`} key={l.badge}>
                <div className="stack-note__head">
                  <span className="stack-note__badge">{l.badge}</span>
                  <span className="stack-note__title">{l.title}</span>
                </div>
                <p className="stack-note__body">{l.body}</p>
                {l.href.startsWith('http') ? (
                  <a href={l.href} target="_blank" rel="noopener noreferrer">
                    {l.hrefLabel} &rarr;
                  </a>
                ) : (
                  <Link to={l.href}>{l.hrefLabel} &rarr;</Link>
                )}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   5. What TACO defines: three pillars with real counts, then the
   layer-by-layer comparison against generic A2A
   ------------------------------------------------------------------ */

const comparisonRows = [
  {
    dimension: 'Agent identity',
    a2a: 'Generic name, URL, freeform skills',
    taco: 'Trade, CSI divisions, project types, platform integrations',
  },
  {
    dimension: 'Skills',
    a2a: 'Freeform description text',
    taco: 'Typed taskType, inputSchema, outputSchema per skill',
  },
  {
    dimension: 'Data exchange',
    a2a: 'structuredData (any JSON, unvalidated)',
    taco: 'Typed schemas with cross-references between artifacts',
  },
  {
    dimension: 'Task types',
    a2a: 'Generic messaging',
    taco: 'Named construction workflows organized by project phase',
  },
  {
    dimension: 'Authorization',
    a2a: '5 auth mechanisms (apiKey through mTLS)',
    taco: 'Scope taxonomy, trust tiers, token delegation',
  },
  {
    dimension: 'Discovery',
    a2a: 'Manual /.well-known/agent-card.json lookup',
    taco: 'Queryable registry filtered by trade, task type, CSI division',
  },
];

function Defines({taskTypeCount, schemaCount}) {
  return (
    <section className="sheet sheet--alt" id="defines">
      <div className="container">
        <SheetHead
          label="Scope"
          meta="Three layers on top of A2A"
          title="What TACO defines."
        />
        <div className="pillars">
          <div className="pillar">
            <div className="pillar__count">
              {taskTypeCount}
              <span className="pillar__unit">task types</span>
            </div>
            <p className="pillar__body">
              A typed vocabulary of construction work, organized by project phase:
              takeoff, estimate, rfi-generation, submittal-review,
              schedule-coordination, material-procurement, and the rest.
            </p>
            <Link className="pillar__link" to="/docs/task-types">
              Browse the task types &rarr;
            </Link>
          </div>
          <div className="pillar">
            <div className="pillar__count">
              {schemaCount}
              <span className="pillar__unit">data schemas</span>
            </div>
            <p className="pillar__body">
              Typed JSON for the artifacts that move between trades. The output of
              one agent is valid input to the next: a bom-v1 becomes an
              estimate-v1 becomes a quote-v1.
            </p>
            <Link className="pillar__link" to="/docs/schemas/">
              Read the schemas &rarr;
            </Link>
          </div>
          <div className="pillar">
            <div className="pillar__count pillar__count--word">
              Discovery
              <span className="pillar__unit">agent card extensions</span>
            </div>
            <p className="pillar__body">
              Construction fields on A2A agent cards: trade, CSI divisions, project
              types, platform integrations. Find the mechanical estimator that
              knows Division 23 and speaks Procore.
            </p>
            <Link className="pillar__link" to="/docs/agent-card-extensions">
              See the extensions &rarr;
            </Link>
          </div>
        </div>

        <div className="compare">
          <div className="compare__head">
            <span className="sheet-head__label">Layer by layer</span>
            <p>A2A provides the transport. TACO adds construction semantics at every layer.</p>
          </div>
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
                {comparisonRows.map((row) => (
                  <tr key={row.dimension}>
                    <td className="standardization-table__dim" data-label="Dimension">
                      {row.dimension}
                    </td>
                    <td className="standardization-table__a2a" data-label="A2A (generic)">
                      {row.a2a}
                    </td>
                    <td className="standardization-table__taco" data-label="TACO adds">
                      {row.taco}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="compare__note">
            Every TACO agent is a valid A2A agent. Clients that don’t know TACO ignore
            the extensions. No lock-in, only richer context for construction.
          </p>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   6. One handoff, drawn
   ------------------------------------------------------------------ */

const handoffActors = [
  {id: 'gc', label: 'GC orchestrator', sub: 'general contractor'},
  {id: 'est', label: 'Mechanical estimator', sub: 'subcontractor'},
  {id: 'sup', label: 'Supplier quoter', sub: 'distributor'},
];

const handoffMessages = [
  {from: 'gc', to: 'est', label: 'estimate', schema: 'bom-v1'},
  {from: 'est', to: 'gc', label: 'priced estimate', schema: 'estimate-v1', kind: 'return'},
  {from: 'gc', to: 'sup', label: 'material-procurement', schema: 'bom-v1', note: 'long-lead items only'},
  {from: 'sup', to: 'gc', label: 'quote', schema: 'quote-v1', kind: 'return'},
];

function Handoff() {
  return (
    <section className="sheet" id="handoff">
      <div className="container">
        <SheetHead
          label="One handoff, drawn"
          meta="Sequence 1 of 1"
          title="Three companies. Three code bases. One vocabulary."
          lede="A general contractor’s orchestrator sends a bill of materials to a mechanical estimator, then prices the long-lead items with a supplier. Every arrow carries a typed schema, so nobody writes a mapping."
        />
        <div className="handoff">
          <SequenceDiagram
            actors={handoffActors}
            messages={handoffMessages}
            ariaLabel="A general contractor orchestrator sends a bom-v1 to a mechanical estimator and receives an estimate-v1, then sends the bom-v1 to a supplier and receives a quote-v1."
          />
          <div className="handoff__legend">
            <div className="handoff__keynotes">
              <span className="sheet-head__label">Keynotes</span>
              <ol>
                <li>The orchestrator discovers the estimator by trade and Division 22/23, then sends the takeoff as a bom-v1.</li>
                <li>The estimator returns an estimate-v1. Line items reference the BOM by id, so nothing is re-keyed.</li>
                <li>Long-lead items go to the supplier under the material-procurement task type, same bom-v1.</li>
                <li>The quote-v1 comes back with lead times the schedule agent can read next.</li>
              </ol>
            </div>
            <div className="handoff__links">
              <Link className="btn btn--ghost btn--sm" to="/docs/getting-started/multi-agent">
                Build this chain
              </Link>
              <Link className="btn btn--ghost btn--sm" to="/docs/examples">
                Run the examples
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   7. Quick start
   ------------------------------------------------------------------ */

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
    <div className="install">
      <div className="install__tabs" role="tablist" aria-label="Package manager">
        {installCommands.map((c) => (
          <button
            key={c.value}
            role="tab"
            aria-selected={active === c.value}
            className={`install__tab ${active === c.value ? 'install__tab--active' : ''}`}
            onClick={() => setActive(c.value)}>
            {c.label}
          </button>
        ))}
      </div>
      <div className="install__cmd">
        <span className="hero__prompt" aria-hidden="true">
          $
        </span>
        <code>{activeCmd.cmd}</code>
        <CopyButton text={activeCmd.cmd} />
      </div>
    </div>
  );
}

function QuickStart() {
  return (
    <section className="sheet sheet--alt" id="quickstart">
      <div className="container">
        <SheetHead
          label="Quick start"
          title="Up and running in under a minute."
          lede="Two patterns: expose your own agent, or discover and call others. The whole loop is under a hundred lines of Python."
        />
        <div className="code-section">
          <Tabs>
            <TabItem value="expose" label="Expose your agent" default>
              <CodeBlock language="python">{exposeCode}</CodeBlock>
            </TabItem>
            <TabItem value="discover" label="Discover and call agents">
              <CodeBlock language="python">{discoverCode}</CodeBlock>
            </TabItem>
          </Tabs>
          <InstallTabs />
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   8. Status, entry points and call to action
   ------------------------------------------------------------------ */

const paths = [
  {
    who: 'Developers',
    title: 'Build your first agent',
    body: 'Define your trade, declare schemas, serve an agent card. Five minutes to a discoverable agent.',
    to: '/docs/getting-started/build-agent',
  },
  {
    who: 'Platform vendors',
    title: 'Integrate your platform',
    body: 'Add an agent sidecar in front of what you already run and map its capabilities to TACO task types.',
    to: '/docs/getting-started/integrate-platform',
  },
  {
    who: 'GCs, subs, owners',
    title: 'Why TACO, in plain language',
    body: 'The superintendent’s vocabulary, machine-readable. What changes on a project when agents share it.',
    to: '/docs/why-taco',
  },
  {
    who: 'Contributors',
    title: 'Help write the standard',
    body: 'Propose a task type, review a schema, or bring a trade we haven’t covered yet.',
    href: `${GITHUB}/blob/main/CONTRIBUTING.md`,
  },
];

function Status({protocolVersion}) {
  return (
    <section className="sheet" id="status">
      <div className="container">
        <SheetHead
          label="Status"
          meta={`Protocol ${protocolVersion}`}
          title="Early, open, and written in public."
          lede="TACO is in active development. Here is what exists today, what is in flight, and where to come in."
        />
        <div className="status">
          <div className="status__col">
            <h3 className="status__h">Shipped in {protocolVersion}</h3>
            <ul>
              <li>Construction agent card extensions: trade, CSI divisions, project types, integrations</li>
              <li>Six typed schemas and the task-type vocabulary</li>
              <li>Python SDK on the A2A v1 SDK, wire-compatible with A2A 0.3</li>
              <li>Scopes, trust tiers, mTLS, PKCE and device-code declarations</li>
              <li>Agent registry, task persistence, and a live agent monitor</li>
            </ul>
          </div>
          <div className="status__col">
            <h3 className="status__h">In flight</h3>
            <ul>
              <li>A2A v1 wire cutover, with the 0.3 format kept byte-identical until then</li>
              <li>New schemas and task types, proposed and reviewed as GitHub issues</li>
              <li>More reference agents and sidecar examples</li>
            </ul>
          </div>
          <div className="status__col">
            <h3 className="status__h">Who is shipping</h3>
            <ul>
              <li>
                <a href="https://pelles.ai" target="_blank" rel="noopener noreferrer">
                  Pelles
                </a>{' '}
                initiated TACO and maintains the SDK and reference agents
              </li>
              <li>
                Built on the{' '}
                <a href="https://a2a-protocol.org" target="_blank" rel="noopener noreferrer">
                  A2A protocol
                </a>{' '}
                under the Linux Foundation
              </li>
              <li>
                Building with it?{' '}
                <a href={`${GITHUB}/blob/main/README.md`} target="_blank" rel="noopener noreferrer">
                  Open a PR to be listed
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="paths">
          {paths.map((p) => {
            const inner = (
              <>
                <span className="path__who">{p.who}</span>
                <span className="path__title">{p.title}</span>
                <span className="path__body">{p.body}</span>
                <span className="path__go" aria-hidden="true">
                  &rarr;
                </span>
              </>
            );
            return p.href ? (
              <a className="path" href={p.href} target="_blank" rel="noopener noreferrer" key={p.who}>
                {inner}
              </a>
            ) : (
              <Link className="path" to={p.to} key={p.who}>
                {inner}
              </Link>
            );
          })}
        </div>

        <div className="cta">
          <div>
            <Heading as="h2" className="cta__title">
              Help write the standard.
            </Heading>
            <p className="cta__body">
              We are looking for construction technology companies, trade contractors,
              GCs and platform vendors to shape the schemas and build the ecosystem.
            </p>
          </div>
          <div className="cta__actions">
            <a className="btn btn--primary" href={GITHUB} target="_blank" rel="noopener noreferrer">
              Star on GitHub
            </a>
            <a
              className="btn btn--ghost"
              href={`${GITHUB}/discussions`}
              target="_blank"
              rel="noopener noreferrer">
              Join the discussion
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   Page
   ------------------------------------------------------------------ */

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  const {
    sdkVersion = '0.3',
    protocolVersion = '0.3',
    taskTypeCount = 18,
    schemaCount = 6,
  } = siteConfig.customFields || {};
  const facts = {sdkVersion, protocolVersion, taskTypeCount, schemaCount};

  return (
    <Layout
      title="One vocabulary for every construction agent"
      description="TACO is the open standard that lets construction AI agents hand work to each other: typed task types, typed data schemas and discovery by trade and CSI division, on top of the A2A protocol.">
      <Hero {...facts} />
      <main>
        <GeneralNotes />
        <Problem />
        <Stack />
        <Defines {...facts} />
        <Handoff />
        <QuickStart />
        <Status {...facts} />
      </main>
    </Layout>
  );
}
