import {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {useHistory} from '@docusaurus/router';
import BrowserOnly from '@docusaurus/BrowserOnly';

/**
 * CMD+K command palette. Modal opens on Ctrl/Cmd+K or `/`, lets the user
 * filter a curated set of navigation actions and execute with Enter.
 *
 * No external dep — vanilla React + a list filter. The action set is
 * hand-curated for high signal (key pages, every schema, every recipe,
 * every ADR's category, sandbox, conformance, glossary).
 */

const ACTIONS = [
  // Top-level
  {id: 'home', title: 'Home', group: 'Pages', href: '/'},
  {id: 'sandbox', title: 'Sandbox — run Python in your browser', group: 'Tools', href: '/sandbox'},
  {id: 'conformance', title: 'Conformance — test your TACO agent', group: 'Tools', href: '/conformance'},

  // Concepts
  {id: 'why', title: 'Why TACO?', group: 'Concepts', href: '/docs/why-taco'},
  {id: 'intro', title: 'Introduction', group: 'Concepts', href: '/docs/intro'},
  {id: 'scope', title: 'What TACO is and isn\'t', group: 'Concepts', href: '/docs/scope'},
  {id: 'protocol-stack', title: 'A2A, MCP, and TACO', group: 'Concepts', href: '/docs/protocol-stack'},
  {id: 'core-concepts', title: 'Core Concepts', group: 'Concepts', href: '/docs/core-concepts'},
  {id: 'task-types', title: 'Task Types (browse)', group: 'Concepts', href: '/docs/task-types'},
  {id: 'agent-card-ext', title: 'Agent Card Extensions', group: 'Concepts', href: '/docs/agent-card-extensions'},
  {id: 'security', title: 'Security model', group: 'Concepts', href: '/docs/security'},
  {id: 'standards', title: 'Standards alignment', group: 'Concepts', href: '/docs/standards'},
  {id: 'glossary', title: 'Glossary', group: 'Concepts', href: '/docs/glossary'},

  // Build
  {id: 'quick-start', title: 'Quick Start', group: 'Build', href: '/docs/getting-started/quick-start'},
  {id: 'build-agent', title: 'Build a Custom Agent', group: 'Build', href: '/docs/getting-started/build-agent'},
  {id: 'multi-agent', title: 'Agent-to-Agent Communication', group: 'Build', href: '/docs/getting-started/multi-agent'},
  {id: 'integrate-platform', title: 'Integrate Your Platform', group: 'Build', href: '/docs/getting-started/integrate-platform'},
  {id: 'best-practices', title: 'Best Practices', group: 'Build', href: '/docs/best-practices'},
  {id: 'pitfalls', title: 'Common Pitfalls', group: 'Build', href: '/docs/pitfalls'},
  {id: 'examples', title: 'Examples', group: 'Build', href: '/docs/examples'},

  // Cookbook recipes
  {id: 'cb-index', title: 'Cookbook (all recipes)', group: 'Cookbook', href: '/docs/cookbook/'},
  {id: 'cb-chain', title: 'Recipe: GC → Estimator → Supplier', group: 'Cookbook', href: '/docs/cookbook/gc-estimator-supplier-chain'},
  {id: 'cb-rfi', title: 'Recipe: RFI Round-trip', group: 'Cookbook', href: '/docs/cookbook/rfi-round-trip'},
  {id: 'cb-quote', title: 'Recipe: BOM-to-Quote Marketplace', group: 'Cookbook', href: '/docs/cookbook/bom-to-quote-marketplace'},
  {id: 'cb-co', title: 'Recipe: Change Order Impact', group: 'Cookbook', href: '/docs/cookbook/change-order-impact'},
  {id: 'cb-sched', title: 'Recipe: Schedule-Aware Procurement', group: 'Cookbook', href: '/docs/cookbook/schedule-aware-procurement'},

  // Case studies
  {id: 'cs-oakridge', title: 'Case study: Oakridge Medical week', group: 'Case Studies', href: '/docs/case-studies/oakridge-medical-week'},
  {id: 'cs-stafford', title: 'Case study: Stafford Mechanical onboarding', group: 'Case Studies', href: '/docs/case-studies/stafford-mechanical-onboarding'},
  {id: 'cs-riverbend', title: 'Case study: City of Riverbend transit RFP', group: 'Case Studies', href: '/docs/case-studies/riverbend-transit-rfp'},

  // Schemas
  {id: 'schemas', title: 'All schemas (with graph)', group: 'Schemas', href: '/docs/schemas/'},
  {id: 'sch-bom', title: 'Schema: bom-v1', group: 'Schemas', href: '/docs/schemas/bom-v1'},
  {id: 'sch-rfi', title: 'Schema: rfi-v1', group: 'Schemas', href: '/docs/schemas/rfi-v1'},
  {id: 'sch-est', title: 'Schema: estimate-v1', group: 'Schemas', href: '/docs/schemas/estimate-v1'},
  {id: 'sch-quote', title: 'Schema: quote-v1', group: 'Schemas', href: '/docs/schemas/quote-v1'},
  {id: 'sch-sched', title: 'Schema: schedule-v1', group: 'Schemas', href: '/docs/schemas/schedule-v1'},
  {id: 'sch-co', title: 'Schema: change-order-v1', group: 'Schemas', href: '/docs/schemas/change-order-v1'},

  // SDK reference
  {id: 'sdk-guide', title: 'SDK Guide', group: 'Reference', href: '/docs/sdk'},
  {id: 'sdk-ref', title: 'SDK Reference (all symbols)', group: 'Reference', href: '/docs/sdk-reference/'},
  {id: 'sdk-cards', title: 'SDK: Agent Cards', group: 'Reference', href: '/docs/sdk-reference/agent-cards'},
  {id: 'sdk-server', title: 'SDK: A2AServer', group: 'Reference', href: '/docs/sdk-reference/server'},
  {id: 'sdk-client', title: 'SDK: TacoClient', group: 'Reference', href: '/docs/sdk-reference/client'},
  {id: 'sdk-registry', title: 'SDK: AgentRegistry', group: 'Reference', href: '/docs/sdk-reference/registry'},
  {id: 'cli', title: 'CLI Reference', group: 'Reference', href: '/docs/cli'},

  // Audience
  {id: 'for-gc', title: 'For General Contractors', group: 'By role', href: '/for/general-contractor'},
  {id: 'for-owner', title: 'For Owners', group: 'By role', href: '/for/owner'},
  {id: 'for-sub', title: 'For Subcontractors', group: 'By role', href: '/for/subcontractor'},
  {id: 'for-vendor', title: 'For Platform Vendors', group: 'By role', href: '/for/platform-vendor'},
  {id: 'for-mech', title: 'For Mechanical Trades', group: 'By role', href: '/for/mechanical'},
  {id: 'for-elec', title: 'For Electrical Trades', group: 'By role', href: '/for/electrical'},
  {id: 'for-plum', title: 'For Plumbing Trades', group: 'By role', href: '/for/plumbing'},
  {id: 'for-struct', title: 'For Structural Trades', group: 'By role', href: '/for/structural'},

  // Community
  {id: 'rfp', title: 'RFP Template', group: 'Community', href: '/docs/rfp-template'},
  {id: 'roadmap', title: 'Roadmap', group: 'Community', href: '/docs/roadmap'},
  {id: 'changelog', title: 'Changelog', group: 'Community', href: '/docs/changelog'},
  {id: 'adrs', title: 'Architecture Decision Records', group: 'Community', href: '/docs/decisions/'},
  {id: 'spec', title: 'Formal SPEC documents', group: 'Community', href: '/docs/spec/'},
  {id: 'compare', title: 'Compare TACO to alternatives', group: 'Community', href: '/docs/compare'},
  {id: 'ecosystem', title: 'Ecosystem', group: 'Community', href: '/docs/ecosystem'},
  {id: 'github', title: 'GitHub repo (external)', group: 'External', href: 'https://github.com/pelles-ai/taco', external: true},
  {id: 'discussions', title: 'GitHub Discussions (external)', group: 'External', href: 'https://github.com/pelles-ai/taco/discussions', external: true},
];

function scoreMatch(action, query) {
  if (!query) return 1;
  const q = query.toLowerCase();
  const t = action.title.toLowerCase();
  if (t === q) return 100;
  if (t.startsWith(q)) return 50;
  if (t.includes(q)) return 25;
  // word-boundary match
  const words = t.split(/\W+/);
  if (words.some((w) => w.startsWith(q))) return 20;
  return 0;
}

function PaletteInner({onClose}) {
  const history = useHistory();
  const inputRef = useRef(null);
  const [query, setQuery] = useState('');
  const [activeIdx, setActiveIdx] = useState(0);

  const results = useMemo(() => {
    return ACTIONS
      .map((a) => ({...a, _score: scoreMatch(a, query)}))
      .filter((a) => a._score > 0)
      .sort((a, b) => b._score - a._score)
      .slice(0, 50);
  }, [query]);

  // Group by category (preserving the sorted-by-score order within each group)
  const grouped = useMemo(() => {
    const out = new Map();
    for (const r of results) {
      if (!out.has(r.group)) out.set(r.group, []);
      out.get(r.group).push(r);
    }
    return [...out.entries()];
  }, [results]);

  // Flat list mirrors `results` for keyboard navigation
  useEffect(() => {
    setActiveIdx(0);
  }, [query]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const execute = useCallback(
    (action) => {
      if (!action) return;
      if (action.external) {
        window.open(action.href, '_blank', 'noopener,noreferrer');
      } else {
        history.push(action.href);
      }
      onClose();
    },
    [history, onClose],
  );

  const onKeyDown = useCallback(
    (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIdx((i) => Math.min(i + 1, results.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIdx((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        execute(results[activeIdx]);
      }
    },
    [results, activeIdx, execute, onClose],
  );

  // Track the current flat index across groups to color-highlight the active row
  let runningIdx = -1;

  return (
    <div className="cmdk-overlay" onClick={onClose} role="presentation">
      <div
        className="cmdk-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onClick={(e) => e.stopPropagation()}>
        <div className="cmdk-header">
          <svg className="cmdk-header-icon" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Jump to a page, recipe, schema, or tool…"
            aria-label="Command search"
          />
          <kbd className="cmdk-esc">esc</kbd>
        </div>

        <div className="cmdk-results">
          {results.length === 0 ? (
            <div className="cmdk-empty">No matches. Try a different term.</div>
          ) : (
            grouped.map(([group, items]) => (
              <div className="cmdk-group" key={group}>
                <div className="cmdk-group-label">{group}</div>
                <ul className="cmdk-list">
                  {items.map((a) => {
                    runningIdx += 1;
                    const isActive = runningIdx === activeIdx;
                    return (
                      <li
                        key={a.id}
                        className={`cmdk-item ${isActive ? 'cmdk-item--active' : ''}`}
                        onMouseEnter={() => setActiveIdx(runningIdx)}
                        onClick={() => execute(a)}>
                        <span className="cmdk-item-title">{a.title}</span>
                        {a.external ? (
                          <span className="cmdk-item-external" aria-hidden="true">↗</span>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))
          )}
        </div>

        <div className="cmdk-footer">
          <span className="cmdk-footer-hint">
            <kbd>↑</kbd><kbd>↓</kbd> to navigate
          </span>
          <span className="cmdk-footer-hint">
            <kbd>↵</kbd> to open
          </span>
          <span className="cmdk-footer-hint">
            <kbd>esc</kbd> to close
          </span>
        </div>
      </div>
    </div>
  );
}

function CommandPaletteInner() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function onKey(e) {
      // CMD+K or Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
        return;
      }
      // `/` to open, but only when not already in an input
      if (e.key === '/' && !open) {
        const tag = document.activeElement?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA') return;
        e.preventDefault();
        setOpen(true);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  if (!open) return null;
  return <PaletteInner onClose={() => setOpen(false)} />;
}

export default function CommandPalette() {
  return <BrowserOnly>{() => <CommandPaletteInner />}</BrowserOnly>;
}
