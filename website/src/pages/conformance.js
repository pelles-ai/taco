import {useCallback, useEffect, useMemo, useState} from 'react';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import Link from '@docusaurus/Link';
import {usePluginData} from '@docusaurus/useGlobalData';
import CopyButton from '@site/src/components/CopyButton';
import sampleCard from '@site/src/data/sample-agent-card.json';
import {baseUrlOf, checkCard, checkHealth, fetchCard} from '@site/src/lib/conformance';

const STATUS_LABEL = {pass: 'Pass', fail: 'Fail', warn: 'Warning', skip: 'Skipped'};

function useSpecFacts() {
  const {trades, taskTypes, schemas, extensionUri} = usePluginData('taco-spec');
  return useMemo(
    () => ({
      trades,
      taskTypes: taskTypes.map((t) => t.id),
      schemaNames: Object.keys(schemas),
      extensionUri,
    }),
    [trades, taskTypes, schemas, extensionUri],
  );
}

function Summary({results, source, checkedAt, target}) {
  const required = results.filter((r) => r.level === 'required');
  const fails = required.filter((r) => r.status === 'fail').length;
  const warns = results.filter((r) => r.status === 'warn').length;
  const json = JSON.stringify(
    {
      spec: 'SPEC-005 0.3',
      checkedAt,
      target,
      conformant: fails === 0,
      results: results.map(({id, section, level, status, detail}) => ({id, section, level, status, detail})),
    },
    null,
    2,
  );
  return (
    <div className={`cf-summary ${fails ? 'cf-summary--fail' : 'cf-summary--pass'}`} role="status">
      <div className="cf-summary__verdict">
        {fails ? `${fails} required ${fails === 1 ? 'check fails' : 'checks fail'}` : 'Passes every required check'}
      </div>
      <div className="cf-summary__detail">
        {source}. {warns} {warns === 1 ? 'warning' : 'warnings'}.{' '}
        {fails ? 'Fix the failures below; each one says how.' : 'Warnings are worth fixing but do not break conformance.'}
      </div>
      {checkedAt ? (
        <div className="cf-summary__meta">
          <span>Checked {checkedAt.replace('T', ' ').replace(/\.\d+Z$/, ' UTC')} against SPEC-005 0.3</span>
          <span className="cf-summary__copy">
            Copy report as JSON <CopyButton text={json} />
          </span>
        </div>
      ) : null}
    </div>
  );
}

function ResultList({title, items}) {
  if (!items.length) return null;
  return (
    <div className="cf-group">
      <h3 className="cf-group__title">{title}</h3>
      <ol className="cf-results">
        {items.map((r) => (
          <li key={r.id} className={`cf-result cf-result--${r.status}`}>
            <span className="cf-result__section">§{r.section}</span>
            <div className="cf-result__body">
              <div className="cf-result__head">
                <span className="cf-result__title">{r.title}</span>
                <span className={`cf-pill cf-pill--${r.status}`}>{STATUS_LABEL[r.status]}</span>
              </div>
              <p className="cf-result__detail">{r.detail}</p>
              {r.fix && r.status !== 'pass' ? <p className="cf-result__fix">{r.fix}</p> : null}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

function Report({results, source, checkedAt, target}) {
  return (
    <div className="cf-report">
      <Summary results={results} source={source} checkedAt={checkedAt} target={target} />
      <ResultList title="Required (SPEC-005 §3)" items={results.filter((r) => r.level === 'required')} />
      <ResultList title="Recommended (SPEC-005 §4)" items={results.filter((r) => r.level === 'recommended')} />
    </div>
  );
}

const SAMPLE_TEXT = JSON.stringify(sampleCard, null, 2);

export default function ConformancePage() {
  const spec = useSpecFacts();
  const [mode, setMode] = useState('paste');
  const [pasted, setPasted] = useState(SAMPLE_TEXT);
  const [url, setUrl] = useState('');
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState(() => ({
    source: 'Checked the sample card served by the Python SDK',
    checkedAt: null, // set after mount, so the server render and the first client render match
    target: 'pasted card',
    results: [
      {
        id: 'reachable',
        section: '3.1',
        title: 'Agent card reachable',
        level: 'required',
        status: 'skip',
        detail: 'Pasted card, so there is no URL to fetch. Check a URL to test this.',
      },
      ...checkCard(sampleCard, spec),
    ],
  }));
  const [error, setError] = useState(null);

  useEffect(() => {
    setReport((r) => (r.checkedAt ? r : {...r, checkedAt: new Date().toISOString()}));
  }, []);

  const runPaste = useCallback(() => {
    setError(null);
    let card;
    try {
      card = JSON.parse(pasted);
    } catch (err) {
      setError(`That is not valid JSON: ${err.message}`);
      return;
    }
    if (!card || typeof card !== 'object' || Array.isArray(card)) {
      setError('Paste a single Agent Card JSON object.');
      return;
    }
    setReport({
      source: pasted === SAMPLE_TEXT ? 'Checked the sample card served by the Python SDK' : 'Checked the pasted card',
      checkedAt: new Date().toISOString(),
      target: 'pasted card',
      results: [
        {
          id: 'reachable',
          section: '3.1',
          title: 'Agent card reachable',
          level: 'required',
          status: 'skip',
          detail: 'Pasted card, so there is no URL to fetch. Check a URL to test this.',
        },
        ...checkCard(card, spec),
      ],
    });
  }, [pasted, spec]);

  const runUrl = useCallback(async () => {
    setError(null);
    let base;
    try {
      base = baseUrlOf(url);
    } catch {
      setError('Enter a full URL, for example https://estimator.example.com');
      return;
    }
    setBusy(true);
    try {
      const {card, result} = await fetchCard(base, token.trim());
      const health = await checkHealth(base, token.trim());
      setReport({
        source: `Checked ${base}`,
        checkedAt: new Date().toISOString(),
        target: base,
        results: card
          ? [result, ...checkCard(card, spec), health]
          : [result, health],
      });
    } finally {
      setBusy(false);
    }
  }, [url, token, spec]);

  const curl = url ? `curl -fsSL ${url.replace(/\/+$/, '')}/.well-known/agent-card.json` : '';

  return (
    <Layout
      title="Conformance check"
      description="Check a TACO Agent Card against the SPEC-005 conformance checks, in your browser. Paste a card or enter an agent URL.">
      <header className="page-hero">
        <div className="container">
          <p className="eyebrow">Tool · SPEC-005 · runs in your browser</p>
          <Heading as="h1" className="page-hero__title">
            Check an agent card against the spec.
          </Heading>
          <p className="page-hero__lede">
            Paste an Agent Card, or point at a running agent, and see which of the{' '}
            <Link to="/docs/spec/SPEC-005-conformance">SPEC-005</Link> checks it passes. Every check
            runs in this page; nothing is sent to TACO. A clean report means the card is
            structurally valid TACO, not that every claim on it is true.
          </p>
        </div>
      </header>

      <main className="container cf">
        <div className="cf__input">
          <div className="cf__modes" role="tablist" aria-label="What to check">
            {[
              ['paste', 'Paste a card'],
              ['url', 'Check a URL'],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={mode === id}
                className={`cf__mode ${mode === id ? 'cf__mode--on' : ''}`}
                onClick={() => {
                  setMode(id);
                  setError(null);
                }}>
                {label}
              </button>
            ))}
          </div>

          {mode === 'paste' ? (
            <div className="cf__form">
              <label htmlFor="cf-card" className="sx-label">
                Agent Card JSON
              </label>
              <textarea
                id="cf-card"
                className="cf__textarea"
                value={pasted}
                onChange={(e) => setPasted(e.target.value)}
                spellCheck={false}
                wrap="off"
              />
              <p className="cf__hint">
                Loaded with a card served by the Python SDK. Replace it with the output of{' '}
                <code>taco discover &lt;url&gt;</code> or the contents of your{' '}
                <code>/.well-known/agent-card.json</code>.
              </p>
              <div className="cf__actions">
                <button type="button" className="btn btn--primary btn--sm" onClick={runPaste}>
                  Check this card
                </button>
                <button type="button" className="btn btn--ghost btn--sm" onClick={() => setPasted(SAMPLE_TEXT)}>
                  Restore the sample
                </button>
              </div>
            </div>
          ) : (
            <div className="cf__form">
              <label htmlFor="cf-url" className="sx-label">
                Agent URL
              </label>
              <input
                id="cf-url"
                type="url"
                className="cf__field"
                placeholder="https://estimator.example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') runUrl();
                }}
              />
              <label htmlFor="cf-token" className="sx-label">
                Bearer token, only if your card is not public
              </label>
              <input
                id="cf-token"
                type="password"
                autoComplete="off"
                className="cf__field"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
              <p className="cf__hint">
                Your browser fetches <code>/.well-known/agent-card.json</code> (then the legacy{' '}
                <code>agent.json</code>) and <code>/health</code> directly. The agent must allow this
                site in its CORS policy, for example{' '}
                <code>A2AServer(card, cors_origins=["https://taco-protocol.com"])</code>. If it
                doesn't, paste the card instead.
              </p>
              {curl ? (
                <div className="cf__curl">
                  <code>{curl}</code>
                  <CopyButton text={curl} />
                </div>
              ) : null}
              <div className="cf__actions">
                <button type="button" className="btn btn--primary btn--sm" onClick={runUrl} disabled={busy || !url}>
                  {busy ? 'Checking' : 'Check this agent'}
                </button>
              </div>
            </div>
          )}
          {error ? (
            <p className="cf__error" role="alert">
              {error}
            </p>
          ) : null}
        </div>

        <section className="cf__output" aria-label="Conformance report">
          <Report {...report} />
        </section>
      </main>
    </Layout>
  );
}
