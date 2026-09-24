import {useMemo, useState} from 'react';
import Link from '@docusaurus/Link';
import {usePluginData} from '@docusaurus/useGlobalData';

/**
 * Filterable list of every task type in spec/task-types.md. Rows, phases and
 * schema status come from the spec at build time (plugins/taco-spec), so the
 * list can't fall out of date with the spec.
 */

function SchemaRef({name, known}) {
  if (!name) return <span className="ttb__none">none</span>;
  return known ? (
    <Link to={`/docs/schemas/${name}`}>
      <code>{name}</code>
    </Link>
  ) : (
    <code className="ttb__planned-code">{name}</code>
  );
}

export default function TaskTypeBrowser() {
  const {taskTypes, schemas} = usePluginData('taco-spec');
  const phases = useMemo(() => [...new Set(taskTypes.map((t) => t.phase))], [taskTypes]);
  const [phase, setPhase] = useState('all');
  const [status, setStatus] = useState('all');
  const [query, setQuery] = useState('');

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return taskTypes.filter((t) => {
      const defined = Boolean(t.outputSchema && schemas[t.outputSchema]);
      if (phase !== 'all' && t.phase !== phase) return false;
      if (status === 'defined' && !defined) return false;
      if (status === 'planned' && defined) return false;
      if (!q) return true;
      return [t.id, t.description, t.inputText, t.outputText].join(' ').toLowerCase().includes(q);
    });
  }, [taskTypes, schemas, phase, status, query]);

  const definedCount = taskTypes.filter((t) => t.outputSchema && schemas[t.outputSchema]).length;

  return (
    <div className="ttb">
      <div className="ttb__controls">
        <label className="ttb__search">
          <span className="sr-only">Filter task types</span>
          <input
            id="ttb-query"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter by name, input or output"
          />
        </label>
        <div className="ttb__group" role="group" aria-label="Project phase">
          {['all', ...phases].map((p) => (
            <button
              key={p}
              type="button"
              aria-pressed={phase === p}
              className={`ttb__chip ${phase === p ? 'ttb__chip--on' : ''}`}
              onClick={() => setPhase(p)}>
              {p === 'all' ? 'All phases' : p}
            </button>
          ))}
        </div>
        <div className="ttb__group" role="group" aria-label="Output schema status">
          {[
            ['all', 'Any output'],
            ['defined', 'Schema defined'],
            ['planned', 'Schema planned'],
          ].map(([id, label]) => (
            <button
              key={id}
              type="button"
              aria-pressed={status === id}
              className={`ttb__chip ${status === id ? 'ttb__chip--on' : ''}`}
              onClick={() => setStatus(id)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <p className="ttb__count" role="status" aria-live="polite">
        Showing {rows.length} of {taskTypes.length} task types. {definedCount} have a
        defined output schema today.
      </p>

      <div className="ttb__table-wrap">
        <table className="ttb__table">
          <thead>
            <tr>
              <th scope="col">Task type</th>
              <th scope="col">What it does</th>
              <th scope="col">Typical input</th>
              <th scope="col">Output</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => {
              const defined = Boolean(t.outputSchema && schemas[t.outputSchema]);
              return (
                <tr key={t.id}>
                  <td>
                    <code className="ttb__id">{t.id}</code>
                    <span className="ttb__phase">{t.phase}</span>
                  </td>
                  <td>{t.description}</td>
                  <td className="ttb__input">
                    {t.inputSchemas.length
                      ? t.inputText.split(/([a-z]+(?:-[a-z]+)*-v\d+)/).map((part, i) =>
                          schemas[part] ? <SchemaRef key={i} name={part} known /> : part,
                        )
                      : t.inputText}
                  </td>
                  <td>
                    {t.outputSchema ? (
                      <>
                        <SchemaRef name={t.outputSchema} known={defined} />
                        {!defined ? <span className="ttb__planned">planned</span> : null}
                      </>
                    ) : (
                      <span className="ttb__free">{t.outputText || 'none'}</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {rows.length === 0 ? (
        <p className="ttb__empty">No task types match. Clear the filter or pick another phase.</p>
      ) : null}
    </div>
  );
}
