import {useMemo, useState} from 'react';
import Link from '@docusaurus/Link';

/**
 * Interactive browser for the 18 TACO task types.
 *
 * Replaces the static phase-grouped tables on /docs/task-types with a
 * filterable matrix. Free-text search across name + description, plus
 * facets for project phase and output-schema status.
 */

const TASK_TYPES = [
  // Preconstruction
  {
    id: 'takeoff',
    name: 'takeoff',
    phase: 'preconstruction',
    description: 'Quantity takeoff from construction documents (plan sheets, PDF, DWG, RVT).',
    input: 'Plan sheets, drawings',
    outputSchema: 'bom-v1',
    outputStatus: 'defined',
    outputHref: '/docs/schemas/bom-v1',
  },
  {
    id: 'estimate',
    name: 'estimate',
    phase: 'preconstruction',
    description: 'Cost estimation from a bill of materials.',
    input: 'bom-v1',
    outputSchema: 'estimate-v1',
    outputStatus: 'defined',
    outputHref: '/docs/schemas/estimate-v1',
  },
  {
    id: 'bid-leveling',
    name: 'bid-leveling',
    phase: 'preconstruction',
    description: 'Compare and normalize bids from multiple subs into apples-to-apples form.',
    input: 'Multiple estimate-v1',
    outputSchema: 'bid-comparison-v1',
    outputStatus: 'planned',
  },
  {
    id: 'value-engineering',
    name: 'value-engineering',
    phase: 'preconstruction',
    description: 'Identify cost-reduction opportunities through alternates and scope substitutions.',
    input: 'bom-v1 + estimate-v1',
    outputSchema: 've-suggestions-v1',
    outputStatus: 'planned',
  },
  {
    id: 'scope-review',
    name: 'scope-review',
    phase: 'preconstruction',
    description: 'Analyze scope of work for gaps, overlaps, or inconsistencies.',
    input: 'Spec documents, bom-v1',
    outputSchema: 'scope-report-v1',
    outputStatus: 'planned',
  },
  {
    id: 'plan-comparison',
    name: 'plan-comparison',
    phase: 'preconstruction',
    description: 'Detect changes between drawing revisions.',
    input: 'Two sets of plan sheets',
    outputSchema: 'plan-delta-v1',
    outputStatus: 'planned',
  },
  // Document Management
  {
    id: 'rfi-generation',
    name: 'rfi-generation',
    phase: 'document-management',
    description: 'Flag design conflicts and generate RFIs from coordinated drawings.',
    input: 'Plan sheets, bom-v1',
    outputSchema: 'rfi-v1',
    outputStatus: 'defined',
    outputHref: '/docs/schemas/rfi-v1',
  },
  {
    id: 'rfi-response',
    name: 'rfi-response',
    phase: 'document-management',
    description: 'Draft a typed response to an RFI from the design side.',
    input: 'rfi-v1',
    outputSchema: 'rfi-response-v1',
    outputStatus: 'planned',
  },
  {
    id: 'submittal-review',
    name: 'submittal-review',
    phase: 'document-management',
    description: 'Review submittals against spec for compliance.',
    input: 'Submittal documents, specs',
    outputSchema: 'submittal-review-v1',
    outputStatus: 'planned',
  },
  {
    id: 'spec-compliance-check',
    name: 'spec-compliance-check',
    phase: 'document-management',
    description: 'Verify materials and methods against project specifications.',
    input: 'bom-v1, spec documents',
    outputSchema: 'compliance-report-v1',
    outputStatus: 'planned',
  },
  {
    id: 'change-order-analysis',
    name: 'change-order-analysis',
    phase: 'document-management',
    description: 'Analyze impact of proposed scope changes on cost and schedule.',
    input: 'Change order docs, bom-v1, schedule-v1',
    outputSchema: 'change-order-v1',
    outputStatus: 'defined',
    outputHref: '/docs/schemas/change-order-v1',
  },
  {
    id: 'drawing-markup',
    name: 'drawing-markup',
    phase: 'document-management',
    description: 'Annotate drawings with findings, markup, or review notes.',
    input: 'Plan sheets',
    outputSchema: 'Marked-up plan sheets',
    outputStatus: 'planned',
  },
  // Field + Coordination
  {
    id: 'schedule-coordination',
    name: 'schedule-coordination',
    phase: 'field-coordination',
    description: 'Build or update project schedules from scope, estimate, and constraints.',
    input: 'bom-v1, estimate-v1, constraints',
    outputSchema: 'schedule-v1',
    outputStatus: 'defined',
    outputHref: '/docs/schemas/schedule-v1',
  },
  {
    id: 'material-procurement',
    name: 'material-procurement',
    phase: 'field-coordination',
    description: 'Source materials and get pricing + lead time from supplier networks.',
    input: 'bom-v1',
    outputSchema: 'quote-v1',
    outputStatus: 'defined',
    outputHref: '/docs/schemas/quote-v1',
  },
  {
    id: 'clash-detection',
    name: 'clash-detection',
    phase: 'field-coordination',
    description: 'Identify spatial conflicts between trades in coordinated BIM models.',
    input: 'BIM models, bom-v1 from multiple trades',
    outputSchema: 'clash-report-v1',
    outputStatus: 'planned',
  },
  {
    id: 'safety-compliance',
    name: 'safety-compliance',
    phase: 'field-coordination',
    description: 'Check plans, site conditions, or workflows for safety compliance.',
    input: 'Site data, plan sheets',
    outputSchema: 'safety-report-v1',
    outputStatus: 'planned',
  },
  {
    id: 'progress-tracking',
    name: 'progress-tracking',
    phase: 'field-coordination',
    description: 'Monitor construction progress against the schedule.',
    input: 'Site photos/scans, schedule-v1',
    outputSchema: 'progress-report-v1',
    outputStatus: 'planned',
  },
  {
    id: 'punch-list',
    name: 'punch-list',
    phase: 'field-coordination',
    description: 'Generate deficiency lists from final inspections.',
    input: 'Inspection data, photos',
    outputSchema: 'punch-list-v1',
    outputStatus: 'planned',
  },
];

const PHASE_LABEL = {
  preconstruction: 'Preconstruction',
  'document-management': 'Document Management',
  'field-coordination': 'Field + Coordination',
};

const PHASES = ['any', ...Object.keys(PHASE_LABEL)];

const STATUS_TABS = [
  {id: 'all', label: 'All schemas'},
  {id: 'defined', label: 'Defined only'},
  {id: 'planned', label: 'Planned only'},
];

export default function TaskTypeBrowser() {
  const [query, setQuery] = useState('');
  const [phase, setPhase] = useState('any');
  const [status, setStatus] = useState('all');

  const filtered = useMemo(() => {
    return TASK_TYPES.filter((t) => {
      if (phase !== 'any' && t.phase !== phase) return false;
      if (status !== 'all' && t.outputStatus !== status) return false;
      if (query.trim()) {
        const q = query.toLowerCase();
        const hay = `${t.name} ${t.description} ${t.input} ${t.outputSchema}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [query, phase, status]);

  return (
    <div className="task-type-browser">
      <div className="task-type-browser__controls">
        <div className="task-type-browser__search">
          <svg className="task-type-browser__search-icon" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter task types"
            aria-label="Filter task types"
          />
          {query ? (
            <button
              type="button"
              className="task-type-browser__clear"
              onClick={() => setQuery('')}
              aria-label="Clear filter">
              ×
            </button>
          ) : null}
        </div>
        <div className="task-type-browser__facet">
          <label htmlFor="ttb-phase">Phase</label>
          <select id="ttb-phase" value={phase} onChange={(e) => setPhase(e.target.value)}>
            <option value="any">Any</option>
            {Object.entries(PHASE_LABEL).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>
        <div className="task-type-browser__tabs" role="tablist">
          {STATUS_TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={status === t.id}
              className={`task-type-browser__tab ${
                status === t.id ? 'task-type-browser__tab--active' : ''
              }`}
              onClick={() => setStatus(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="task-type-browser__count">
        {filtered.length} task type{filtered.length === 1 ? '' : 's'}
      </div>

      {filtered.length === 0 ? (
        <div className="task-type-browser__empty">
          No task types match these filters.
        </div>
      ) : (
        <ul className="task-type-browser__list">
          {filtered.map((t) => (
            <li key={t.id} className="task-type-card" id={t.id}>
              <div className="task-type-card__head">
                <code className="task-type-card__name">{t.name}</code>
                <span className={`task-type-card__phase task-type-card__phase--${t.phase}`}>
                  {PHASE_LABEL[t.phase]}
                </span>
              </div>
              <p className="task-type-card__desc">{t.description}</p>
              <div className="task-type-card__io">
                <div className="task-type-card__io-row">
                  <span className="task-type-card__io-label">Input</span>
                  <span className="task-type-card__io-value">{t.input}</span>
                </div>
                <div className="task-type-card__io-row">
                  <span className="task-type-card__io-label">Output</span>
                  <span className="task-type-card__io-value">
                    {t.outputHref ? (
                      <Link to={t.outputHref}>
                        <code>{t.outputSchema}</code>
                      </Link>
                    ) : (
                      <code>{t.outputSchema}</code>
                    )}
                    <span className={`task-type-card__status task-type-card__status--${t.outputStatus}`}>
                      {t.outputStatus}
                    </span>
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
