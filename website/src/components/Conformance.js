import {useCallback, useState} from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';

/**
 * Conformance test runner for a live TACO agent.
 *
 * Pure client-side. Hits the agent's well-known paths from the visitor's
 * browser, parses the agent card, and runs a battery of structural checks
 * against the TACO + A2A spec. Each check returns { status, message,
 * details? } and the UI renders pass / fail / skip with remediation hints.
 *
 * CORS-aware: when the browser blocks a request, we surface a clear
 * explanation and offer the equivalent curl invocation so the user can
 * re-run the check locally.
 */

// ---- Reference data -----------------------------------------------------

const RECOGNIZED_TRADES = [
  'mechanical',
  'electrical',
  'plumbing',
  'structural',
  'civil',
  'architectural',
  'fire-protection',
  'general',
  'multi-trade',
];

const RECOGNIZED_SCHEMAS = [
  'bom-v1',
  'rfi-v1',
  'estimate-v1',
  'quote-v1',
  'schedule-v1',
  'change-order-v1',
];

const RECOGNIZED_TASK_TYPES = [
  'takeoff',
  'estimate',
  'bid-leveling',
  'value-engineering',
  'scope-review',
  'plan-comparison',
  'rfi-generation',
  'rfi-response',
  'submittal-review',
  'spec-compliance-check',
  'change-order-analysis',
  'drawing-markup',
  'schedule-coordination',
  'material-procurement',
  'clash-detection',
  'safety-compliance',
  'progress-tracking',
  'punch-list',
];

const X_CONSTRUCTION_EXTENSION_URI =
  'https://taco.construction/extensions/x-construction/v1';

// ---- Check runners ------------------------------------------------------

function normalizeBase(input) {
  let url = input.trim();
  if (!url) throw new Error('Agent URL is required');
  if (!/^https?:\/\//i.test(url)) url = `https://${url}`;
  return url.replace(/\/+$/, '');
}

function pass(id, label, message, details) {
  return {id, label, status: 'pass', message, details};
}
function fail(id, label, message, details, hint) {
  return {id, label, status: 'fail', message, details, hint};
}
function skip(id, label, message) {
  return {id, label, status: 'skip', message};
}

async function fetchAgentCard(baseUrl, token) {
  const headers = {Accept: 'application/json'};
  if (token) headers.Authorization = `Bearer ${token}`;

  const candidates = [
    `${baseUrl}/.well-known/agent-card.json`,
    `${baseUrl}/.well-known/agent.json`,
  ];

  let lastError = null;
  for (const url of candidates) {
    try {
      const res = await fetch(url, {headers, mode: 'cors'});
      if (res.ok) {
        const card = await res.json();
        return {card, url, status: res.status};
      }
      lastError = new Error(`HTTP ${res.status} fetching ${url}`);
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError ?? new Error('Could not fetch agent card');
}

function checkRequiredCardFields(card) {
  const required = ['name', 'version', 'url'];
  const missing = required.filter((k) => !card[k]);
  if (missing.length === 0) {
    return pass(
      'card-required-fields',
      'Agent card has required fields',
      `name, version, url all present`,
    );
  }
  return fail(
    'card-required-fields',
    'Agent card has required fields',
    `Missing: ${missing.join(', ')}`,
    null,
    'Set these top-level fields on your Agent Card before serving it. See /docs/agent-card-extensions.',
  );
}

function checkSkills(card) {
  if (!Array.isArray(card.skills) || card.skills.length === 0) {
    return fail(
      'skills-present',
      'Agent advertises at least one skill',
      'No skills found on agent card',
      null,
      'Add at least one skill with an id, taskType, and optional input/output schemas.',
    );
  }
  return pass(
    'skills-present',
    'Agent advertises at least one skill',
    `${card.skills.length} skill${card.skills.length === 1 ? '' : 's'} declared`,
  );
}

function checkConstructionExtension(card) {
  const inlineExt = card['x-construction'];
  const declared = Array.isArray(card?.capabilities?.extensions)
    ? card.capabilities.extensions.some(
        (e) => (typeof e === 'string' ? e : e?.uri) === X_CONSTRUCTION_EXTENSION_URI,
      )
    : false;

  if (!inlineExt && !declared) {
    return fail(
      'construction-extension',
      'Agent card declares the TACO construction extension',
      'No `x-construction` field and no extension URI under `capabilities.extensions[]`',
      {
        inlineFound: false,
        declaredFound: false,
      },
      'Either include an `x-construction` object on the card (with at minimum `trade`) or declare the extension URI in `capabilities.extensions[]`.',
    );
  }
  return pass(
    'construction-extension',
    'Agent card declares the TACO construction extension',
    `inline=${!!inlineExt}, declared=${declared}`,
  );
}

function checkTrade(card) {
  const trade = card?.['x-construction']?.trade;
  if (!trade) {
    return skip('trade', 'Trade is a recognized TACO value', 'No `x-construction.trade` set');
  }
  if (RECOGNIZED_TRADES.includes(trade)) {
    return pass('trade', 'Trade is a recognized TACO value', `trade=${trade}`);
  }
  return fail(
    'trade',
    'Trade is a recognized TACO value',
    `Unknown trade: "${trade}"`,
    {trade, recognized: RECOGNIZED_TRADES},
    'Use one of the recognized trades listed in /docs/glossary or in the Trade enum.',
  );
}

function checkCsiDivisions(card) {
  const divs = card?.['x-construction']?.csiDivisions;
  if (!Array.isArray(divs)) {
    return skip('csi-divisions', 'CSI divisions look valid', 'No `csiDivisions` array');
  }
  const bad = divs.filter((d) => !/^\d{2}$/.test(String(d)));
  if (bad.length === 0) {
    return pass(
      'csi-divisions',
      'CSI divisions look valid',
      `${divs.length} valid 2-digit MasterFormat division${divs.length === 1 ? '' : 's'}`,
    );
  }
  return fail(
    'csi-divisions',
    'CSI divisions look valid',
    `Invalid entries: ${bad.join(', ')}`,
    {csiDivisions: divs},
    'CSI divisions should be 2-digit strings, e.g. "22", "23", "26".',
  );
}

function checkSkillTaskTypes(card) {
  if (!Array.isArray(card.skills)) {
    return skip('task-types', 'Skill task types are recognized', 'No skills to check');
  }
  const skillTaskTypes = card.skills
    .map((s) => s?.['x-construction']?.taskType ?? s?.taskType)
    .filter(Boolean);
  if (skillTaskTypes.length === 0) {
    return fail(
      'task-types',
      'Skill task types are recognized',
      'No skills carry a taskType',
      {skillTaskTypes},
      'Each skill should declare a `taskType` (either inline or via `x-construction.taskType`).',
    );
  }
  const unknown = [...new Set(skillTaskTypes)].filter(
    (t) => !RECOGNIZED_TASK_TYPES.includes(t),
  );
  if (unknown.length === 0) {
    return pass(
      'task-types',
      'Skill task types are recognized',
      `${skillTaskTypes.length} skill task type${skillTaskTypes.length === 1 ? '' : 's'}, all recognized`,
    );
  }
  return fail(
    'task-types',
    'Skill task types are recognized',
    `Unknown task types: ${unknown.join(', ')}`,
    {unknown, recognized: RECOGNIZED_TASK_TYPES},
    'Use one of the 18 recognized TACO task types, or propose a new one via a GitHub issue.',
  );
}

function checkSkillSchemas(card) {
  if (!Array.isArray(card.skills)) {
    return skip('schemas', 'Skill schemas reference recognized TACO schemas', 'No skills to check');
  }
  const advertised = card.skills
    .flatMap((s) => [s?.inputSchema, s?.outputSchema])
    .filter(Boolean);
  if (advertised.length === 0) {
    return skip(
      'schemas',
      'Skill schemas reference recognized TACO schemas',
      'No skills advertise input/output schemas',
    );
  }
  const unknown = [...new Set(advertised)].filter((s) => {
    if (s.startsWith('http://') || s.startsWith('https://')) return false; // user URL — accept
    return !RECOGNIZED_SCHEMAS.includes(s);
  });
  if (unknown.length === 0) {
    return pass(
      'schemas',
      'Skill schemas reference recognized TACO schemas',
      `${advertised.length} schema reference${advertised.length === 1 ? '' : 's'}, all recognized`,
    );
  }
  return fail(
    'schemas',
    'Skill schemas reference recognized TACO schemas',
    `Unknown schema names: ${unknown.join(', ')}`,
    {unknown, recognized: RECOGNIZED_SCHEMAS},
    'Schema references should be one of the canonical TACO schema names (bom-v1, rfi-v1, etc.) or a full URL.',
  );
}

function checkSecurityIfAdvertised(card) {
  const schemes = card.securitySchemes;
  const security = card.security;
  if (!schemes && !security) {
    return skip(
      'security-schemes',
      'Security declarations are internally consistent',
      'No securitySchemes or security advertised',
    );
  }
  if (security && !schemes) {
    return fail(
      'security-schemes',
      'Security declarations are internally consistent',
      '`security` requirements reference schemes, but `securitySchemes` is missing',
      {security},
      'Add a `securitySchemes` object to the agent card defining each scheme referenced by `security[]`.',
    );
  }
  if (schemes && security) {
    const referenced = security.flatMap((s) => Object.keys(s));
    const declared = Object.keys(schemes);
    const missing = referenced.filter((r) => !declared.includes(r));
    if (missing.length > 0) {
      return fail(
        'security-schemes',
        'Security declarations are internally consistent',
        `Referenced but undeclared: ${missing.join(', ')}`,
        {missing, declared},
        'Every name in `security[]` must have a matching key under `securitySchemes`.',
      );
    }
  }
  return pass(
    'security-schemes',
    'Security declarations are internally consistent',
    schemes ? `${Object.keys(schemes).length} scheme(s) declared` : 'no security required',
  );
}

async function checkHealth(baseUrl, token) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  try {
    const res = await fetch(`${baseUrl}/health`, {headers, mode: 'cors'});
    if (res.ok) {
      return pass('health', 'Health endpoint reachable', `GET /health → ${res.status}`);
    }
    return skip(
      'health',
      'Health endpoint reachable',
      `GET /health → ${res.status} (optional)`,
    );
  } catch (_) {
    return skip(
      'health',
      'Health endpoint reachable',
      'GET /health failed or blocked (optional)',
    );
  }
}

async function runConformance({url, token}) {
  const baseUrl = normalizeBase(url);
  const results = [];

  let card;
  let cardUrl;
  try {
    const r = await fetchAgentCard(baseUrl, token);
    card = r.card;
    cardUrl = r.url;
    results.push(
      pass(
        'card-reachable',
        'Agent card is reachable',
        `GET ${cardUrl} → 200, valid JSON`,
      ),
    );
  } catch (err) {
    const isCors =
      err instanceof TypeError ||
      String(err.message || err).match(/Failed to fetch|NetworkError|CORS/i);
    const curlExample = `curl -fsSL "${baseUrl}/.well-known/agent-card.json" | jq .`;
    results.push(
      fail(
        'card-reachable',
        'Agent card is reachable',
        isCors
          ? 'The browser blocked the request (likely CORS).'
          : `Could not fetch agent card: ${err.message ?? err}`,
        {cors: isCors, curl: curlExample, attemptedFrom: [
          `${baseUrl}/.well-known/agent-card.json`,
          `${baseUrl}/.well-known/agent.json`,
        ]},
        isCors
          ? 'Either add this origin to your agent\'s CORS allowlist, or run the equivalent curl locally (shown in details).'
          : 'Make sure your agent serves /.well-known/agent-card.json (preferred) or /.well-known/agent.json.',
      ),
    );
    return {baseUrl, results, card: null};
  }

  results.push(checkRequiredCardFields(card));
  results.push(checkSkills(card));
  results.push(checkConstructionExtension(card));
  results.push(checkTrade(card));
  results.push(checkCsiDivisions(card));
  results.push(checkSkillTaskTypes(card));
  results.push(checkSkillSchemas(card));
  results.push(checkSecurityIfAdvertised(card));
  results.push(await checkHealth(baseUrl, token));

  return {baseUrl, results, card};
}

// ---- UI -----------------------------------------------------------------

const STATUS_GLYPH = {pass: '✓', fail: '✗', skip: '○'};

function CheckRow({check}) {
  const [open, setOpen] = useState(false);
  const hasDetails = check.details || check.hint;
  return (
    <li className={`conform-check conform-check--${check.status}`}>
      <button
        type="button"
        className="conform-check__head"
        onClick={() => hasDetails && setOpen((v) => !v)}
        aria-expanded={open}
        disabled={!hasDetails}>
        <span className="conform-check__glyph" aria-hidden="true">
          {STATUS_GLYPH[check.status]}
        </span>
        <span className="conform-check__label">{check.label}</span>
        <span className="conform-check__message">{check.message}</span>
        {hasDetails ? (
          <span className="conform-check__toggle">{open ? '−' : '+'}</span>
        ) : null}
      </button>
      {open && hasDetails ? (
        <div className="conform-check__body">
          {check.hint ? (
            <div className="conform-check__hint">{check.hint}</div>
          ) : null}
          {check.details ? (
            <pre className="conform-check__details">
              <code>{JSON.stringify(check.details, null, 2)}</code>
            </pre>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

function ConformanceInner() {
  const [url, setUrl] = useState('');
  const [token, setToken] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  const run = useCallback(async (e) => {
    e?.preventDefault?.();
    setError(null);
    setReport(null);
    setRunning(true);
    try {
      const r = await runConformance({url, token});
      setReport(r);
    } catch (err) {
      setError(err.message ?? String(err));
    } finally {
      setRunning(false);
    }
  }, [url, token]);

  const passCount = report?.results.filter((r) => r.status === 'pass').length ?? 0;
  const failCount = report?.results.filter((r) => r.status === 'fail').length ?? 0;
  const skipCount = report?.results.filter((r) => r.status === 'skip').length ?? 0;
  const total = report?.results.length ?? 0;

  return (
    <div className="conform">
      <form className="conform__form" onSubmit={run}>
        <div className="conform__field">
          <label htmlFor="conform-url">Agent URL</label>
          <input
            id="conform-url"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://my-agent.example.com:8080"
            spellCheck={false}
            autoComplete="off"
            required
          />
        </div>
        <div className="conform__field">
          <label htmlFor="conform-token">
            Bearer token <span className="conform__field-hint">(optional)</span>
          </label>
          <div className="conform__token-row">
            <input
              id="conform-token"
              type={showToken ? 'text' : 'password'}
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="for agents requiring authentication"
              spellCheck={false}
              autoComplete="off"
            />
            <button
              type="button"
              className="conform__token-toggle"
              onClick={() => setShowToken((v) => !v)}
              aria-label={showToken ? 'Hide token' : 'Show token'}>
              {showToken ? 'hide' : 'show'}
            </button>
          </div>
        </div>
        <button
          type="submit"
          className="conform__run"
          disabled={running || !url.trim()}>
          {running ? 'Running…' : 'Run conformance check'}
        </button>
      </form>

      <div className="conform__notice">
        Checks run in your browser. Nothing is sent to TACO; the only network
        requests are the ones your browser makes to the URL above.
      </div>

      {error ? <div className="conform__error">{error}</div> : null}

      {report ? (
        <div className="conform__report">
          <header className="conform__summary">
            <div className="conform__score">
              <span className="conform__score-num">{passCount}</span>
              <span className="conform__score-of">/ {total} passed</span>
            </div>
            <div className="conform__score-breakdown">
              <span className="conform__score-pill conform__score-pill--pass">
                {passCount} pass
              </span>
              <span className="conform__score-pill conform__score-pill--fail">
                {failCount} fail
              </span>
              <span className="conform__score-pill conform__score-pill--skip">
                {skipCount} skip
              </span>
            </div>
          </header>
          <ul className="conform__checks">
            {report.results.map((r) => (
              <CheckRow key={r.id} check={r} />
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export default function Conformance() {
  return (
    <BrowserOnly fallback={<div className="conform conform--loading">Loading…</div>}>
      {() => <ConformanceInner />}
    </BrowserOnly>
  );
}
