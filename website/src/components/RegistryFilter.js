import {useMemo, useState} from 'react';

/**
 * Interactive demo of the TACO Agent Registry.
 *
 * Realistic sample data, modeled after what `taco discover` would return
 * from a live registry. Filtering is purely client-side — no network calls.
 */

const AGENTS = [
  {
    name: 'Mech Estimator Pro',
    org: 'BuildRight Co.',
    trade: 'mechanical',
    csi: ['22', '23'],
    taskTypes: ['estimate', 'value-engineering'],
    trustTier: 1,
    integrations: ['procore', 'autocad'],
  },
  {
    name: 'HVAC Takeoff Bot',
    org: 'Climatec',
    trade: 'mechanical',
    csi: ['23'],
    taskTypes: ['takeoff', 'bid-leveling'],
    trustTier: 0,
    integrations: ['revit'],
  },
  {
    name: 'Electrical RFI Drafter',
    org: 'Sparks Engineering',
    trade: 'electrical',
    csi: ['26', '27'],
    taskTypes: ['rfi-generation', 'submittal-review'],
    trustTier: 2,
    integrations: ['acc', 'bluebeam'],
  },
  {
    name: 'Plumbing Quoter',
    org: 'PipeWorks Supply',
    trade: 'mechanical',
    csi: ['22'],
    taskTypes: ['material-procurement'],
    trustTier: 1,
    integrations: ['acc'],
  },
  {
    name: 'Structural Clash Detector',
    org: 'IronGrid Studio',
    trade: 'structural',
    csi: ['03', '05'],
    taskTypes: ['clash-detection', 'scope-review'],
    trustTier: 1,
    integrations: ['navisworks', 'revit'],
  },
  {
    name: 'Schedule Coordinator',
    org: 'TimelinePM',
    trade: 'multi-trade',
    csi: ['01'],
    taskTypes: ['schedule-coordination', 'progress-tracking'],
    trustTier: 2,
    integrations: ['p6', 'procore'],
  },
  {
    name: 'Safety Compliance Auditor',
    org: 'SafeSite AI',
    trade: 'multi-trade',
    csi: ['01'],
    taskTypes: ['safety-compliance', 'punch-list'],
    trustTier: 1,
    integrations: ['procore', 'bluebeam'],
  },
  {
    name: 'Concrete Quote Engine',
    org: 'Cast Iron Materials',
    trade: 'structural',
    csi: ['03'],
    taskTypes: ['material-procurement', 'estimate'],
    trustTier: 0,
    integrations: ['acc'],
  },
  {
    name: 'Submittal Reviewer',
    org: 'SpecGuard',
    trade: 'multi-trade',
    csi: ['03', '05', '22', '23', '26'],
    taskTypes: ['submittal-review', 'spec-compliance-check'],
    trustTier: 2,
    integrations: ['bluebeam', 'procore'],
  },
];

const TRADES = ['any', 'mechanical', 'electrical', 'structural', 'multi-trade'];
const TASK_TYPES = [
  'any',
  'takeoff',
  'estimate',
  'rfi-generation',
  'submittal-review',
  'material-procurement',
  'clash-detection',
  'schedule-coordination',
  'safety-compliance',
];

const TRUST_TIERS = [
  {value: 0, label: 'Unverified'},
  {value: 1, label: 'Org Verified'},
  {value: 2, label: 'Cert Attested'},
];

function trustLabel(tier) {
  return TRUST_TIERS.find((t) => t.value === tier)?.label ?? 'Unknown';
}

export default function RegistryFilter() {
  const [trade, setTrade] = useState('any');
  const [taskType, setTaskType] = useState('any');
  const [csi, setCsi] = useState('');
  const [minTrust, setMinTrust] = useState(0);

  const filtered = useMemo(() => {
    return AGENTS.filter((a) => {
      if (trade !== 'any' && a.trade !== trade) return false;
      if (taskType !== 'any' && !a.taskTypes.includes(taskType)) return false;
      if (csi.trim() && !a.csi.includes(csi.trim())) return false;
      if (a.trustTier < minTrust) return false;
      return true;
    });
  }, [trade, taskType, csi, minTrust]);

  const cliCommand = useMemo(() => {
    const parts = ['taco discover'];
    if (trade !== 'any') parts.push(`--trade ${trade}`);
    if (taskType !== 'any') parts.push(`--task-type ${taskType}`);
    if (csi.trim()) parts.push(`--csi ${csi.trim()}`);
    if (minTrust > 0) parts.push(`--min-trust ${minTrust}`);
    return parts.join(' ');
  }, [trade, taskType, csi, minTrust]);

  return (
    <div className="registry-filter">
      <div className="registry-filter__controls">
        <div className="registry-filter__field">
          <label htmlFor="rf-trade">Trade</label>
          <select
            id="rf-trade"
            value={trade}
            onChange={(e) => setTrade(e.target.value)}>
            {TRADES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div className="registry-filter__field">
          <label htmlFor="rf-task">Task type</label>
          <select
            id="rf-task"
            value={taskType}
            onChange={(e) => setTaskType(e.target.value)}>
            {TASK_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div className="registry-filter__field">
          <label htmlFor="rf-csi">CSI division</label>
          <input
            id="rf-csi"
            type="text"
            value={csi}
            onChange={(e) => setCsi(e.target.value)}
            placeholder="e.g. 23"
            inputMode="numeric"
            maxLength={2}
          />
        </div>

        <div className="registry-filter__field">
          <label htmlFor="rf-trust">Min trust tier</label>
          <select
            id="rf-trust"
            value={minTrust}
            onChange={(e) => setMinTrust(Number(e.target.value))}>
            {TRUST_TIERS.map((t) => (
              <option key={t.value} value={t.value}>
                {t.value} — {t.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="registry-filter__cli">
        <span className="registry-filter__cli-prompt">$</span>
        <code>{cliCommand}</code>
      </div>

      <div className="registry-filter__results">
        <div className="registry-filter__count">
          {filtered.length} agent{filtered.length === 1 ? '' : 's'} matched
        </div>
        {filtered.length === 0 ? (
          <div className="registry-filter__empty">
            No agents match these filters. Try widening the search.
          </div>
        ) : (
          <ul className="registry-filter__list">
            {filtered.map((a) => (
              <li className="registry-agent-card" key={a.name}>
                <div className="registry-agent-card__head">
                  <span className="registry-agent-card__name">{a.name}</span>
                  <span
                    className={`registry-agent-card__trust registry-agent-card__trust--${a.trustTier}`}
                    title={`Trust tier ${a.trustTier}`}>
                    {trustLabel(a.trustTier)}
                  </span>
                </div>
                <div className="registry-agent-card__org">{a.org}</div>
                <div className="registry-agent-card__meta">
                  <span className="registry-pill registry-pill--trade">
                    {a.trade}
                  </span>
                  {a.csi.map((c) => (
                    <span key={c} className="registry-pill registry-pill--csi">
                      CSI {c}
                    </span>
                  ))}
                </div>
                <div className="registry-agent-card__tasks">
                  {a.taskTypes.map((t) => (
                    <code key={t}>{t}</code>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
