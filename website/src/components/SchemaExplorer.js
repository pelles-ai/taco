import {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';
import CopyButton from '@site/src/components/CopyButton';

/**
 * Visual + interactive explorer for a single TACO JSON Schema.
 *
 * Loads /schemas/{schemaId}.json at runtime (Draft 2020-12), then renders:
 *   - Structure tab: navigable field tree with type/required/enum chips
 *   - Try it tab:    JSON editor + ajv-powered live validator
 *   - Raw schema:    pretty-printed full schema with copy/download
 *
 * Cross-references (which schemas reference / are referenced by this one)
 * are declared in `SCHEMA_RELATIONSHIPS` because TACO's schemas don't use
 * $ref between files yet — relationships are workflow-level, not structural.
 */

const SCHEMA_RELATIONSHIPS = {
  'bom-v1': {
    consumedBy: ['estimate-v1', 'quote-v1'],
    producedBy: ['takeoff'],
  },
  'estimate-v1': {
    consumes: ['bom-v1'],
    consumedBy: ['change-order-v1'],
    producedBy: ['estimate', 'value-engineering', 'bid-leveling'],
  },
  'quote-v1': {
    consumes: ['bom-v1'],
    producedBy: ['material-procurement'],
  },
  'schedule-v1': {
    consumedBy: ['change-order-v1'],
    producedBy: ['schedule-coordination'],
  },
  'rfi-v1': {
    producedBy: ['rfi-generation'],
  },
  'change-order-v1': {
    consumes: ['estimate-v1', 'schedule-v1'],
    producedBy: ['change-order-analysis'],
  },
};

const EXAMPLES = {
  'bom-v1': {
    projectId: 'PRJ-0042',
    trade: 'mechanical',
    csiDivision: '23',
    lineItems: [
      {
        id: 'L-001',
        description: 'Copper pipe, type L',
        quantity: 120,
        unit: 'LF',
        size: '3/4"',
        material: 'copper',
      },
    ],
    metadata: {
      generatedBy: 'takeoff-agent-v2',
      generatedAt: '2026-05-24T15:00:00Z',
    },
  },
  'rfi-v1': {
    projectId: 'PRJ-0042',
    subject: 'Pipe routing conflict at column line C/4',
    question: 'Detail M-201 shows 4" hot water supply routed through the structural beam at column line C/4. Please confirm intended routing.',
    category: 'design-conflict',
    priority: 'high',
    references: [{sheetId: 'M-201', area: 'grid C4'}],
    metadata: {generatedAt: '2026-05-24T15:00:00Z'},
  },
  'estimate-v1': {
    projectId: 'PRJ-0042',
    currency: 'USD',
    lineItems: [
      {description: 'Material', subtotal: 28400},
      {description: 'Labor (120h @ $145)', subtotal: 17400},
    ],
    summary: {total: 45800, overheadAndProfit: 7400},
    metadata: {generatedAt: '2026-05-24T15:00:00Z'},
  },
  'quote-v1': {
    projectId: 'PRJ-0042',
    supplier: {name: 'PipeWorks Supply', contact: 'sales@pipeworks.example'},
    items: [{sku: 'CU-34', unitPrice: 12.4, quantity: 120, leadTimeDays: 2}],
    validUntil: '2026-06-15',
    metadata: {generatedAt: '2026-05-24T15:00:00Z'},
  },
  'schedule-v1': {
    projectId: 'PRJ-0042',
    activities: [
      {id: 'A-100', name: 'Rough plumbing', durationDays: 14, dependencies: []},
    ],
    metadata: {generatedAt: '2026-05-24T15:00:00Z'},
  },
  'change-order-v1': {
    projectId: 'PRJ-0042',
    changeOrderId: 'CO-007',
    description: 'Add HVAC zoning for level 3 east wing',
    costImpact: {amount: 12400, currency: 'USD'},
    metadata: {generatedAt: '2026-05-24T15:00:00Z'},
  },
};

// ---- type chips & utils ----

function typeChip(prop) {
  if (!prop) return 'unknown';
  if (prop.enum) return 'enum';
  if (prop.type === 'array') {
    const items = prop.items;
    if (items?.type === 'object') return 'array<object>';
    if (items?.type) return `array<${items.type}>`;
    return 'array';
  }
  return Array.isArray(prop.type) ? prop.type.join(' | ') : prop.type || 'object';
}

// ---- structure tree ----

function FieldRow({name, prop, required, depth, path}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const childrenOf =
    prop.type === 'object' && prop.properties
      ? prop
      : prop.type === 'array' && prop.items?.type === 'object'
        ? prop.items
        : null;
  const hasChildren = childrenOf && childrenOf.properties;

  return (
    <li
      className={`schema-field schema-field--depth-${depth}`}
      data-path={path}>
      <div className="schema-field__head">
        {hasChildren ? (
          <button
            type="button"
            className={`schema-field__toggle ${
              expanded ? 'schema-field__toggle--open' : ''
            }`}
            onClick={() => setExpanded((v) => !v)}
            aria-label={expanded ? 'Collapse' : 'Expand'}
            aria-expanded={expanded}>
            ▸
          </button>
        ) : (
          <span className="schema-field__bullet" aria-hidden="true" />
        )}
        <span className="schema-field__name">{name}</span>
        <span className="schema-field__type">{typeChip(prop)}</span>
        {required ? (
          <span className="schema-field__required">required</span>
        ) : null}
        {prop.format ? (
          <span className="schema-field__format">format: {prop.format}</span>
        ) : null}
      </div>
      {prop.description ? (
        <div className="schema-field__desc">{prop.description}</div>
      ) : null}
      {prop.enum ? (
        <div className="schema-field__enum">
          {prop.enum.map((v) => (
            <code key={String(v)}>{String(v)}</code>
          ))}
        </div>
      ) : null}
      {hasChildren && expanded ? (
        <FieldList parent={childrenOf} depth={depth + 1} parentPath={path} />
      ) : null}
    </li>
  );
}

function FieldList({parent, depth = 0, parentPath = ''}) {
  const required = new Set(parent.required || []);
  const entries = Object.entries(parent.properties || {});
  if (entries.length === 0) return null;
  return (
    <ul className={`schema-fields ${depth > 0 ? 'schema-fields--nested' : ''}`}>
      {entries.map(([name, prop]) => (
        <FieldRow
          key={name}
          name={name}
          prop={prop}
          required={required.has(name)}
          depth={depth}
          path={`${parentPath}/${name}`}
        />
      ))}
    </ul>
  );
}

// ---- validator (ajv) ----

let ajvPromise = null;
function loadAjv() {
  if (!ajvPromise) {
    ajvPromise = (async () => {
      const [{default: Ajv2020}, {default: addFormats}] = await Promise.all([
        import('ajv/dist/2020.js'),
        import('ajv-formats'),
      ]);
      const ajv = new Ajv2020({allErrors: true, strict: false});
      addFormats(ajv);
      return ajv;
    })();
  }
  return ajvPromise;
}

function TryItPane({schema, schemaId}) {
  const example = EXAMPLES[schemaId] ?? {};
  const [src, setSrc] = useState(() => JSON.stringify(example, null, 2));
  const [result, setResult] = useState(null); // null | {ok, errors?}
  const [busy, setBusy] = useState(false);
  const validateRef = useRef(null);

  const ensureValidator = useCallback(async () => {
    if (validateRef.current) return validateRef.current;
    const ajv = await loadAjv();
    // Strip $id so re-compilation is cheap and per-component
    const {$id, ...rest} = schema;
    validateRef.current = ajv.compile(rest);
    return validateRef.current;
  }, [schema]);

  const run = useCallback(async () => {
    setBusy(true);
    setResult(null);
    try {
      const parsed = JSON.parse(src);
      const validate = await ensureValidator();
      const ok = validate(parsed);
      setResult({ok, errors: validate.errors || []});
    } catch (err) {
      setResult({
        ok: false,
        parseError: err.message,
      });
    } finally {
      setBusy(false);
    }
  }, [src, ensureValidator]);

  const reset = useCallback(() => {
    setSrc(JSON.stringify(example, null, 2));
    setResult(null);
  }, [example]);

  return (
    <div className="schema-tryit">
      <div className="schema-tryit__panes">
        <div className="schema-tryit__editor-wrap">
          <div className="schema-tryit__pane-label">your JSON</div>
          <textarea
            className="schema-tryit__editor"
            value={src}
            onChange={(e) => setSrc(e.target.value)}
            spellCheck={false}
            aria-label="JSON to validate"
          />
        </div>
        <div className="schema-tryit__result-wrap">
          <div className="schema-tryit__pane-label">validation</div>
          <div className="schema-tryit__result">
            {result === null ? (
              <div className="schema-tryit__hint">
                Click <strong>Validate</strong> to check your JSON against the schema.
              </div>
            ) : result.parseError ? (
              <div className="schema-tryit__error">
                <div className="schema-tryit__error-head">JSON parse error</div>
                <pre>{result.parseError}</pre>
              </div>
            ) : result.ok ? (
              <div className="schema-tryit__ok">
                <span className="schema-tryit__ok-mark">✓</span>
                Valid against <code>{schemaId}</code>
              </div>
            ) : (
              <div className="schema-tryit__errors">
                <div className="schema-tryit__errors-head">
                  ✗ {result.errors.length} validation{' '}
                  {result.errors.length === 1 ? 'error' : 'errors'}
                </div>
                <ul>
                  {result.errors.map((e, i) => (
                    <li key={i}>
                      <code>{e.instancePath || '/'}</code>
                      <span> {e.message}</span>
                      {e.params?.allowedValues ? (
                        <div className="schema-tryit__error-detail">
                          allowed: {e.params.allowedValues.map((v) => (
                            <code key={v}>{String(v)}</code>
                          ))}
                        </div>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="schema-tryit__actions">
        <button
          type="button"
          className="schema-tryit__run"
          onClick={run}
          disabled={busy}>
          {busy ? 'Validating…' : 'Validate'}
        </button>
        <button
          type="button"
          className="schema-tryit__reset"
          onClick={reset}>
          Reset to example
        </button>
      </div>
    </div>
  );
}

// ---- raw schema ----

function RawPane({schema, schemaId}) {
  const text = useMemo(() => JSON.stringify(schema, null, 2), [schema]);
  return (
    <div className="schema-raw">
      <div className="schema-raw__bar">
        <a
          href={`/schemas/${schemaId}.json`}
          download={`${schemaId}.json`}
          className="schema-raw__download">
          Download
        </a>
        <CopyButton text={text} />
      </div>
      <pre className="schema-raw__code">
        <code>{text}</code>
      </pre>
    </div>
  );
}

// ---- cross-refs ----

function RelationshipsFooter({schemaId}) {
  const rel = SCHEMA_RELATIONSHIPS[schemaId];
  if (!rel) return null;
  const sections = [
    {label: 'Consumes', key: 'consumes', type: 'schema'},
    {label: 'Consumed by', key: 'consumedBy', type: 'schema'},
    {label: 'Produced by task type', key: 'producedBy', type: 'task'},
  ];
  return (
    <div className="schema-rels">
      {sections.map((s) =>
        rel[s.key]?.length ? (
          <div className="schema-rels__row" key={s.key}>
            <span className="schema-rels__label">{s.label}</span>
            <div className="schema-rels__items">
              {rel[s.key].map((id) =>
                s.type === 'schema' ? (
                  <a key={id} href={`/docs/schemas/${id}`}>
                    <code>{id}</code>
                  </a>
                ) : (
                  <a key={id} href="/docs/task-types">
                    <code>{id}</code>
                  </a>
                ),
              )}
            </div>
          </div>
        ) : null,
      )}
    </div>
  );
}

// ---- main ----

function SchemaExplorerInner({schemaId}) {
  const [schema, setSchema] = useState(null);
  const [loadErr, setLoadErr] = useState(null);
  const [tab, setTab] = useState('structure');

  useEffect(() => {
    let cancelled = false;
    fetch(`/schemas/${schemaId}.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status} fetching ${schemaId}.json`);
        return r.json();
      })
      .then((j) => {
        if (!cancelled) setSchema(j);
      })
      .catch((e) => {
        if (!cancelled) setLoadErr(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [schemaId]);

  if (loadErr) {
    return (
      <div className="schema-explorer schema-explorer--error">
        Failed to load schema: {loadErr}
      </div>
    );
  }
  if (!schema) {
    return <div className="schema-explorer schema-explorer--loading">Loading schema…</div>;
  }

  return (
    <div className="schema-explorer">
      <header className="schema-explorer__head">
        <div className="schema-explorer__badges">
          <span className="schema-explorer__badge schema-explorer__badge--id">
            {schemaId}
          </span>
          <span className="schema-explorer__badge schema-explorer__badge--draft">
            Draft 2020-12
          </span>
        </div>
        <h2 className="schema-explorer__title">{schema.title}</h2>
        {schema.description ? (
          <p className="schema-explorer__desc">{schema.description}</p>
        ) : null}
        {schema.$id ? (
          <div className="schema-explorer__id">
            <code>{schema.$id}</code>
            <CopyButton text={schema.$id} />
          </div>
        ) : null}
      </header>

      <div className="schema-explorer__tabs" role="tablist">
        {[
          {id: 'structure', label: 'Structure'},
          {id: 'tryit', label: 'Try it'},
          {id: 'raw', label: 'Raw schema'},
        ].map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`schema-explorer__tab ${
              tab === t.id ? 'schema-explorer__tab--active' : ''
            }`}
            onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="schema-explorer__body">
        {tab === 'structure' ? <FieldList parent={schema} /> : null}
        {tab === 'tryit' ? <TryItPane schema={schema} schemaId={schemaId} /> : null}
        {tab === 'raw' ? <RawPane schema={schema} schemaId={schemaId} /> : null}
      </div>

      <RelationshipsFooter schemaId={schemaId} />
    </div>
  );
}

export default function SchemaExplorer({schemaId}) {
  return (
    <BrowserOnly
      fallback={<div className="schema-explorer schema-explorer--loading">Loading…</div>}>
      {() => <SchemaExplorerInner schemaId={schemaId} />}
    </BrowserOnly>
  );
}
