import {useEffect, useMemo, useRef, useState} from 'react';
import Link from '@docusaurus/Link';
import {TERMS, AUDIENCE_LABEL} from '@site/src/data/glossary';

/**
 * Bidirectional glossary with a live filter and an audience facet.
 *
 * Each term is a stable hash anchor (e.g. #rfi) so other docs can link
 * straight at a definition.
 */

const AUDIENCE_TABS = [
  {id: 'all', label: 'All'},
  {id: 'construction', label: 'Construction'},
  {id: 'protocol', label: 'Protocol'},
  {id: 'both', label: 'Both'},
];

function matches(term, query) {
  if (!query) return true;
  const q = query.toLowerCase();
  const hay = [term.term, term.full, term.short, ...(term.aliases || [])]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return hay.includes(q);
}

function GlossaryEntry({entry}) {
  return (
    <article className="glossary-entry" id={entry.id}>
      <header className="glossary-entry__head">
        <div className="glossary-entry__title-row">
          <h3 className="glossary-entry__title">
            <a href={`#${entry.id}`} className="glossary-entry__anchor">
              {entry.term}
            </a>
          </h3>
          <span
            className={`glossary-entry__audience glossary-entry__audience--${entry.audience}`}>
            {AUDIENCE_LABEL[entry.audience]}
          </span>
        </div>
        {entry.full && entry.full !== entry.term ? (
          <div className="glossary-entry__full">{entry.full}</div>
        ) : null}
        {entry.aliases?.length ? (
          <div className="glossary-entry__aliases">
            also known as {entry.aliases.join(', ')}
          </div>
        ) : null}
      </header>
      <p className="glossary-entry__short">{entry.short}</p>
      {entry.long ? (
        <p className="glossary-entry__long">{entry.long}</p>
      ) : null}
      {entry.seeAlso?.length ? (
        <div className="glossary-entry__see-also">
          <span className="glossary-entry__see-also-label">See also</span>
          <span className="glossary-entry__see-also-items">
            {entry.seeAlso.map((s) => {
              const isExternal = s.href?.startsWith('http');
              return isExternal ? (
                <a
                  key={s.href}
                  href={s.href}
                  target="_blank"
                  rel="noopener noreferrer">
                  {s.label} ↗
                </a>
              ) : (
                <Link key={s.href} to={s.href}>
                  {s.label}
                </Link>
              );
            })}
          </span>
        </div>
      ) : null}
    </article>
  );
}

export default function Glossary() {
  const [query, setQuery] = useState('');
  const [audience, setAudience] = useState('all');
  const inputRef = useRef(null);

  // Scroll to a hash anchor on first load
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const hash = window.location.hash?.slice(1);
    if (hash) {
      const el = document.getElementById(hash);
      if (el) {
        setTimeout(() => el.scrollIntoView({behavior: 'instant', block: 'start'}), 0);
      }
    }
  }, []);

  // `/` to focus
  useEffect(() => {
    if (typeof window === 'undefined') return;
    function onKey(e) {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const filtered = useMemo(() => {
    const byAudience =
      audience === 'all'
        ? TERMS
        : TERMS.filter((t) => t.audience === audience || t.audience === 'both');
    return byAudience.filter((t) => matches(t, query));
  }, [query, audience]);

  const sorted = useMemo(
    () => [...filtered].sort((a, b) => a.term.toLowerCase().localeCompare(b.term.toLowerCase())),
    [filtered],
  );

  return (
    <div className="glossary">
      <div className="glossary__controls">
        <div className="glossary__search">
          <svg
            className="glossary__search-icon"
            viewBox="0 0 24 24"
            aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter terms (press / to focus)"
            aria-label="Filter glossary terms"
          />
          {query ? (
            <button
              type="button"
              className="glossary__clear"
              onClick={() => setQuery('')}
              aria-label="Clear filter">
              ×
            </button>
          ) : null}
        </div>
        <div className="glossary__tabs" role="tablist">
          {AUDIENCE_TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={audience === t.id}
              className={`glossary__tab ${
                audience === t.id ? 'glossary__tab--active' : ''
              }`}
              onClick={() => setAudience(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="glossary__count">
        {sorted.length} {sorted.length === 1 ? 'term' : 'terms'}
      </div>

      {sorted.length === 0 ? (
        <div className="glossary__empty">
          No terms match. Try widening the filter or clearing the audience tab.
        </div>
      ) : (
        <div className="glossary__list">
          {sorted.map((entry) => (
            <GlossaryEntry key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
