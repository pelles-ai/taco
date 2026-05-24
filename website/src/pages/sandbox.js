import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import Link from '@docusaurus/Link';

import Sandbox from '@site/src/components/Sandbox';

export default function SandboxPage() {
  return (
    <Layout
      title="Sandbox"
      description="Run TACO Python code in your browser — no install required. Powered by Pyodide and a client-side SDK shim.">
      <main className="sandbox-page">
        <div className="container">
          <header className="sandbox-page__head">
            <span className="section__eyebrow">Sandbox</span>
            <Heading as="h1" className="sandbox-page__title">
              Try TACO in your browser
            </Heading>
            <p className="sandbox-page__subtitle">
              Real Python, running under{' '}
              <a
                href="https://pyodide.org/"
                target="_blank"
                rel="noopener noreferrer">
                Pyodide
              </a>
              . The SDK is a client-side shim that returns canned, typed
              responses — enough to feel the ergonomics without installing
              anything.
            </p>
          </header>

          <Sandbox />

          <section className="sandbox-page__next">
            <Heading as="h2" className="sandbox-page__next-title">
              Next steps
            </Heading>
            <div className="sandbox-page__next-grid">
              <Link to="/docs/getting-started/quick-start" className="sandbox-page__next-card">
                <div className="sandbox-page__next-card-title">Install for real</div>
                <div className="sandbox-page__next-card-desc">
                  <code>pip install taco-agent</code> and ship a live agent in
                  under two minutes.
                </div>
              </Link>
              <Link to="/docs/sdk" className="sandbox-page__next-card">
                <div className="sandbox-page__next-card-title">SDK Reference</div>
                <div className="sandbox-page__next-card-desc">
                  Full Python API — models, server, client, registry, CLI.
                </div>
              </Link>
              <Link to="/docs/protocol-stack" className="sandbox-page__next-card">
                <div className="sandbox-page__next-card-title">A2A, MCP &amp; TACO</div>
                <div className="sandbox-page__next-card-desc">
                  How the three protocols stack together for construction agents.
                </div>
              </Link>
            </div>
          </section>
        </div>
      </main>
    </Layout>
  );
}
