import {useCallback, useMemo, useRef, useState} from 'react';
import Link from '@docusaurus/Link';
import {usePluginData} from '@docusaurus/useGlobalData';
import CopyButton from '@site/src/components/CopyButton';

/**
 * Explorer for one TACO JSON Schema, rendered from spec/schemas at build
 * time (see plugins/taco-spec). Three views:
 *   Fields    the property tree with type, required and enum values
 *   Validate  paste JSON and check it against the schema in the browser
 *   Schema    the raw JSON Schema, with a link to /schemas/<id>.json
 * The example in the Validate view is checked against the schema during the
 * build, so it always validates.
 */

function typeLabel(prop) {
  if (!prop) return 'unknown';
  if (prop.enum) return 'enum';
  if (prop.type === 'array') {
    const items = prop.items || {};
    return items.type ? `array of ${items.type}` : 'array';
  }
  if (Array.isArray(prop.type)) return prop.type.join(' | ');
  return prop.type || 'object';
}

function constraints(prop) {
  const out = [];
  if (prop.format) out.push(prop.format);
  if (prop.minimum !== undefined) out.push(`min ${prop.minimum}`);
  if (prop.maximum !== undefined) out.push(`max ${prop.maximum}`);
  if (prop.minItems !== undefined) out.push(`at least ${prop.minItems}`);
  if (prop.pattern) out.push(`pattern ${prop.pattern}`);
  return out;
}

function childObject(prop) {
  if (prop.type === 'object' && prop.properties) return prop;
  if (prop.type === 'array' && prop.items && prop.items.properties) return prop.items;
  return null;
}

function Field({name, prop, required, depth}) {
  const child = childObject(prop);
  const [open, setOpen] = useState(depth < 1);
  const extras = constraints(prop);
  return (
    <li className="sx-field">
      <div className="sx-field__row">
        {child ? (
          <button
            type="button"
            className={`sx-field__toggle ${open ? 'sx-field__toggle--open' : ''}`}
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-label={`${open ? 'Collapse' : 'Expand'} ${name}`}>
            <svg viewBox="0 0 10 10" aria-hidden="true">
              <path d="M3 1.5 L7 5 L3 8.5" />
            </svg>
          </button>
        ) : (
          <span className="sx-field__leaf" aria-hidden="true" />
        )}
        <code className="sx-field__name">{name}</code>
        <span className="sx-field__type">{typeLabel(prop)}</span>
        {required ? <span className="sx-field__req">required</span> : null}
        {extras.map((c) => (
          <span className="sx-field__constraint" key={c}>
            {c}
          </span>
        ))}
      </div>
      {prop.description ? <p className="sx-field__desc">{prop.description}</p> : null}
      {prop.enum ? (
        <div className="sx-field__enum">
          {prop.enum.map((v) => (
            <code key={String(v)}>{String(v)}</code>
          ))}
        </div>
      ) : null}
      {child && open ? <Fields node={child} depth={depth + 1} /> : null}
    </li>
  );
}

function Fields({node, depth = 0}) {
  const required = new Set(node.required || []);
  return (
    <ul className={`sx-fields ${depth ? 'sx-fields--nested' : ''}`}>
      {Object.entries(node.properties || {}).map(([name, prop]) => (
        <Field key={name} name={name} prop={prop} required={required.has(name)} depth={depth} />
      ))}
    </ul>
  );
}

let ajvPromise = null;
function loadAjv() {
  if (!ajvPromise) {
    ajvPromise = Promise.all([import('ajv/dist/2020'), import('ajv-formats')]).then(
      ([{default: Ajv2020}, {default: addFormats}]) => {
        const ajv = new Ajv2020({allErrors: true, strict: false});
        addFormats(ajv);
        return ajv;
      },
    );
  }
  return ajvPromise;
}

function Validate({schema, schemaId, example}) {
  const initial = useMemo(() => JSON.stringify(example, null, 2), [example]);
  const [src, setSrc] = useState(initial);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const validator = useRef(null);

  const run = useCallback(async () => {
    setBusy(true);
    try {
      const data = JSON.parse(src);
      if (!validator.current) {
        const ajv = await loadAjv();
        const {$id, ...rest} = schema;
        validator.current = ajv.compile(rest);
      }
      const ok = validator.current(data);
      setResult({ok, errors: validator.current.errors || []});
    } catch (err) {
      setResult({ok: false, parseError: err.message});
    } finally {
      setBusy(false);
    }
  }, [src, schema]);

  return (
    <div className="sx-validate">
      <div className="sx-validate__panes">
        <label className="sx-validate__pane">
          <span className="sx-label">JSON to check</span>
          <textarea
            id={`sx-input-${schemaId}`}
            className="sx-validate__input"
            value={src}
            onChange={(e) => {
              setSrc(e.target.value);
              setResult(null);
            }}
            spellCheck={false}
          />
        </label>
        <div className="sx-validate__pane">
          <span className="sx-label">Result</span>
          <div className="sx-validate__result" role="status" aria-live="polite">
            {result === null ? (
              <p className="sx-validate__hint">
                The sample {schemaId} is loaded. Edit it or paste your own, then
                select Validate. Nothing leaves your browser.
              </p>
            ) : result.parseError ? (
              <div className="sx-validate__bad">
                <strong>Not valid JSON.</strong>
                <pre>{result.parseError}</pre>
              </div>
            ) : result.ok ? (
              <div className="sx-validate__ok">
                <strong>Valid {schemaId}.</strong> Every required field is present
                and every value matches its type.
              </div>
            ) : (
              <div className="sx-validate__bad">
                <strong>
                  {result.errors.length} {result.errors.length === 1 ? 'problem' : 'problems'}
                </strong>
                <ul>
                  {result.errors.map((e, i) => (
                    <li key={i}>
                      <code>{e.instancePath || '(root)'}</code> {e.message}
                      {e.params && e.params.allowedValues ? (
                        <span className="sx-validate__allowed">
                          {' '}
                          Allowed: {e.params.allowedValues.join(', ')}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="sx-validate__actions">
        <button type="button" className="btn btn--primary btn--sm" onClick={run} disabled={busy}>
          {busy ? 'Validating' : 'Validate'}
        </button>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => {
            setSrc(initial);
            setResult(null);
          }}>
          Restore the sample
        </button>
      </div>
    </div>
  );
}

function Raw({schema, schemaId}) {
  const text = useMemo(() => JSON.stringify(schema, null, 2), [schema]);
  return (
    <div className="sx-raw">
      <div className="sx-raw__bar">
        <a href={`/schemas/${schemaId}.json`} target="_blank" rel="noopener noreferrer">
          /schemas/{schemaId}.json
        </a>
        <CopyButton text={text} />
      </div>
      <pre className="sx-raw__code">
        <code>{text}</code>
      </pre>
    </div>
  );
}

function Relationships({rel}) {
  if (!rel) return null;
  const rows = [
    {label: 'Produced by', items: rel.producedBy, to: () => '/docs/task-types'},
    {label: 'Built from', items: rel.consumes, to: (id) => `/docs/schemas/${id}`},
    {label: 'Feeds task types', items: rel.consumedBy, to: () => '/docs/task-types'},
  ].filter((r) => r.items && r.items.length);
  if (!rows.length) return null;
  return (
    <dl className="sx-rels">
      {rows.map((r) => (
        <div className="sx-rels__row" key={r.label}>
          <dt>{r.label}</dt>
          <dd>
            {r.items.map((id) => (
              <Link key={id} to={r.to(id)}>
                <code>{id}</code>
              </Link>
            ))}
          </dd>
        </div>
      ))}
    </dl>
  );
}

const TABS = [
  {id: 'fields', label: 'Fields'},
  {id: 'validate', label: 'Validate'},
  {id: 'schema', label: 'Schema'},
];

export default function SchemaExplorer({schemaId}) {
  const {schemas, examples, relationships} = usePluginData('taco-spec');
  const schema = schemas[schemaId];
  const [tab, setTab] = useState('fields');
  if (!schema) {
    return <p className="sx-missing">No schema named {schemaId} in spec/schemas.</p>;
  }
  const requiredCount = (schema.required || []).length;
  const fieldCount = Object.keys(schema.properties || {}).length;

  return (
    <section className="sx" aria-label={`${schemaId} schema explorer`}>
      <header className="sx__head">
        <div className="sx__meta">
          <span className="sx__id">{schemaId}</span>
          <span>JSON Schema 2020-12</span>
          <span>
            {fieldCount} top-level fields, {requiredCount} required
          </span>
        </div>
        <div className="sx__uri">
          <span className="sx-label">$id</span>
          <code>{schema.$id}</code>
          <CopyButton text={schema.$id} />
        </div>
      </header>

      <div className="sx__tabs" role="tablist" aria-label="Schema views">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            id={`sx-tab-${schemaId}-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`sx-panel-${schemaId}`}
            className={`sx__tab ${tab === t.id ? 'sx__tab--active' : ''}`}
            onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      <div
        className="sx__body"
        role="tabpanel"
        id={`sx-panel-${schemaId}`}
        aria-labelledby={`sx-tab-${schemaId}-${tab}`}>
        {tab === 'fields' ? <Fields node={schema} /> : null}
        {tab === 'validate' ? (
          <Validate schema={schema} schemaId={schemaId} example={examples[schemaId]} />
        ) : null}
        {tab === 'schema' ? <Raw schema={schema} schemaId={schemaId} /> : null}
      </div>

      <Relationships rel={relationships[schemaId]} />
    </section>
  );
}

/** The validated sample payload for a schema, as a JSON code block. */
export function SchemaExample({schemaId}) {
  const {examples} = usePluginData('taco-spec');
  const text = JSON.stringify(examples[schemaId], null, 2);
  return (
    <div className="sx-example">
      <div className="sx-raw__bar">
        <span className="sx-label">Sample {schemaId}, validated against the schema at build time</span>
        <CopyButton text={text} />
      </div>
      <pre className="sx-raw__code">
        <code>{text}</code>
      </pre>
    </div>
  );
}
