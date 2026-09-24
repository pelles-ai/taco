import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import CopyButton from '@site/src/components/CopyButton';
import Playground from '@site/src/components/Playground';

const INSTALL = 'pip install "taco-agent[all]" uvicorn';

export default function PlaygroundPage() {
  const {siteConfig} = useDocusaurusContext();
  const {sdkVersion} = siteConfig.customFields;
  return (
    <Layout
      title="Playground"
      description="Run the TACO Python SDK in your browser: define an agent card, serve it, send a typed task and validate a schema, with nothing to install.">
      <header className="page-hero">
        <div className="container">
          <p className="eyebrow">Tool · Python SDK · runs in your browser</p>
          <Heading as="h1" className="page-hero__title">
            Try the SDK without installing anything.
          </Heading>
          <p className="page-hero__lede">
            Each example is real Python using <code>taco-agent</code> {sdkVersion}, the same package
            you install from PyPI. It runs on{' '}
            <a href="https://pyodide.org" target="_blank" rel="noopener noreferrer">
              Pyodide
            </a>
            , Python compiled to WebAssembly, so your code never leaves this page. Edit anything and
            run it again.
          </p>
        </div>
      </header>

      <main className="container pg-page">
        <Playground />

        <section className="pg-next" aria-labelledby="pg-next-title">
          <Heading as="h2" id="pg-next-title" className="pg-next__title">
            Take it to your machine
          </Heading>
          <div className="pg-next__grid">
            <div className="pg-next__item">
              <p className="sx-label">Install</p>
              <div className="cf__curl">
                <code>{INSTALL}</code>
                <CopyButton text={INSTALL} />
              </div>
              <p>
                The playground talks to its server in memory. On your machine the same server
                answers HTTP with <code>uvicorn.run(server.app, port=8080)</code>.
              </p>
            </div>
            <div className="pg-next__item">
              <p className="sx-label">Build</p>
              <p>
                <Link to="/docs/getting-started/build-agent">Build your first agent</Link> walks
                through a real estimator end to end. The{' '}
                <Link to="/docs/sdk-reference">SDK reference</Link> lists every class used here.
              </p>
            </div>
            <div className="pg-next__item">
              <p className="sx-label">Check</p>
              <p>
                Paste the card from the first example into the{' '}
                <Link to="/conformance">conformance check</Link> to see how it scores against
                SPEC-005.
              </p>
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
