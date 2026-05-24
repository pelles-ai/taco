import {useColorMode} from '@docusaurus/theme-common';

/**
 * Construction agent network. Zones use tinted fills + colored strokes
 * (rather than solid colored fills) so the gold TACO bar stays the focal point.
 */
export default function ArchitectureDiagram() {
  const {colorMode} = useColorMode();
  const isDark = colorMode === 'dark';
  const registryFill = isDark ? '#11172a' : '#fafbfd';
  const registryStroke = isDark ? '#1e273b' : '#e6e9ef';
  const registryTextFill = isDark ? '#98a1b3' : '#5b6478';
  const connectorStroke = isDark ? '#2a3450' : '#cbd5e1';
  const labelFill = isDark ? '#e8ecf3' : '#0b1220';
  const subLabelFill = isDark ? '#98a1b3' : '#5b6478';

  // Tinted zone fill values — opacity baked in via rgba.
  const zone = (rgb) => ({
    fill: `rgba(${rgb}, ${isDark ? 0.18 : 0.10})`,
    stroke: `rgba(${rgb}, ${isDark ? 0.55 : 0.45})`,
    strokeWidth: 1,
  });

  // Agent chip fill
  const chipFill = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(15,23,42,0.04)';
  const chipStroke = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15,23,42,0.06)';

  return (
    <>
      <p className="diagram-mobile-note">← Scroll horizontally to explore →</p>
      <svg
        viewBox="0 0 860 420"
        className="arch-diagram"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-label="TACO architecture diagram showing agent zones connected through the TACO shared layer">
        <defs>
          <linearGradient id="tacoGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#EAB308" />
            <stop offset="50%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#EAB308" />
          </linearGradient>
        </defs>

        {/* Top agent zones — tinted fills, colored borders */}
        <g className="zone-group">
          {/* Preconstruction */}
          <rect x="20" y="20" width="250" height="110" rx="10" {...zone('124,58,237')} />
          <text x="145" y="48" textAnchor="middle" className="zone-label" fill={labelFill}>
            Preconstruction
          </text>
          <rect x="35" y="60" width="100" height="28" rx="6" fill={chipFill} stroke={chipStroke} />
          <text x="85" y="79" textAnchor="middle" className="agent-label" fill={labelFill}>
            Takeoff Agent
          </text>
          <rect x="150" y="60" width="105" height="28" rx="6" fill={chipFill} stroke={chipStroke} />
          <text x="202" y="79" textAnchor="middle" className="agent-label" fill={labelFill}>
            Estimating Agent
          </text>
          <text x="145" y="113" textAnchor="middle" className="zone-detail" fill={subLabelFill}>
            bid-leveling · value-engineering · scope-review
          </text>
        </g>

        <g className="zone-group">
          {/* Document Management */}
          <rect x="305" y="20" width="250" height="110" rx="10" {...zone('37,99,235')} />
          <text x="430" y="48" textAnchor="middle" className="zone-label" fill={labelFill}>
            Document Management
          </text>
          <rect x="320" y="60" width="100" height="28" rx="6" fill={chipFill} stroke={chipStroke} />
          <text x="370" y="79" textAnchor="middle" className="agent-label" fill={labelFill}>
            RFI Agent
          </text>
          <rect x="435" y="60" width="105" height="28" rx="6" fill={chipFill} stroke={chipStroke} />
          <text x="487" y="79" textAnchor="middle" className="agent-label" fill={labelFill}>
            Submittal Agent
          </text>
          <text x="430" y="113" textAnchor="middle" className="zone-detail" fill={subLabelFill}>
            spec-compliance · change-order · drawing-markup
          </text>
        </g>

        <g className="zone-group">
          {/* Field + Coordination */}
          <rect x="590" y="20" width="250" height="110" rx="10" {...zone('22,163,74')} />
          <text x="715" y="48" textAnchor="middle" className="zone-label" fill={labelFill}>
            Field + Coordination
          </text>
          <rect x="605" y="60" width="105" height="28" rx="6" fill={chipFill} stroke={chipStroke} />
          <text x="657" y="79" textAnchor="middle" className="agent-label" fill={labelFill}>
            Schedule Agent
          </text>
          <rect x="720" y="60" width="105" height="28" rx="6" fill={chipFill} stroke={chipStroke} />
          <text x="772" y="79" textAnchor="middle" className="agent-label" fill={labelFill}>
            Safety Agent
          </text>
          <text x="715" y="113" textAnchor="middle" className="zone-detail" fill={subLabelFill}>
            clash-detection · progress-tracking · punch-list
          </text>
        </g>

        {/* Schema labels above TACO bar */}
        <text x="145" y="158" textAnchor="middle" className="schema-label">
          bom-v1 · estimate-v1
        </text>
        <text x="430" y="158" textAnchor="middle" className="schema-label">
          rfi-v1 · change-order-v1
        </text>
        <text x="715" y="158" textAnchor="middle" className="schema-label">
          schedule-v1
        </text>

        {/* Connection lines top */}
        <line x1="145" y1="130" x2="145" y2="170" stroke={connectorStroke} strokeWidth="1" strokeDasharray="3,3" />
        <line x1="430" y1="130" x2="430" y2="170" stroke={connectorStroke} strokeWidth="1" strokeDasharray="3,3" />
        <line x1="715" y1="130" x2="715" y2="170" stroke={connectorStroke} strokeWidth="1" strokeDasharray="3,3" />

        {/* TACO central bar — gold focal point */}
        <rect x="20" y="170" width="820" height="60" rx="10" fill="url(#tacoGrad)" />
        <text x="430" y="198" textAnchor="middle" className="taco-bar-text">
          TACO — Shared Task Types, Data Schemas, Agent Discovery
        </text>
        <text x="430" y="218" textAnchor="middle" className="taco-bar-subtext">
          Every TACO agent is a standard A2A agent
        </text>

        {/* Connection lines bottom */}
        <line x1="145" y1="230" x2="145" y2="270" stroke={connectorStroke} strokeWidth="1" strokeDasharray="3,3" />
        <line x1="430" y1="230" x2="430" y2="270" stroke={connectorStroke} strokeWidth="1" strokeDasharray="3,3" />
        <line x1="715" y1="230" x2="715" y2="270" stroke={connectorStroke} strokeWidth="1" strokeDasharray="3,3" />

        {/* Schema labels below TACO bar */}
        <text x="145" y="265" textAnchor="middle" className="schema-label">
          quote-v1
        </text>
        <text x="430" y="265" textAnchor="middle" className="schema-label">
          OAuth scopes · trust tiers
        </text>
        <text x="715" y="265" textAnchor="middle" className="schema-label">
          Agent Cards
        </text>

        {/* Bottom agent zones */}
        <g className="zone-group">
          {/* Supply Chain */}
          <rect x="20" y="280" width="250" height="80" rx="10" {...zone('217,119,6')} />
          <text x="145" y="308" textAnchor="middle" className="zone-label" fill={labelFill}>
            Supply Chain
          </text>
          <rect x="35" y="318" width="105" height="28" rx="6" fill={chipFill} stroke={chipStroke} />
          <text x="87" y="337" textAnchor="middle" className="agent-label" fill={labelFill}>
            Supplier Agent
          </text>
          <rect x="150" y="318" width="105" height="28" rx="6" fill={chipFill} stroke={chipStroke} />
          <text x="202" y="337" textAnchor="middle" className="agent-label" fill={labelFill}>
            Logistics Agent
          </text>
        </g>

        <g className="zone-group">
          {/* External Parties */}
          <rect x="305" y="280" width="250" height="80" rx="10" {...zone('220,38,38')} />
          <text x="430" y="308" textAnchor="middle" className="zone-label" fill={labelFill}>
            External Parties
          </text>
          <rect x="320" y="318" width="105" height="28" rx="6" fill={chipFill} stroke={chipStroke} />
          <text x="372" y="337" textAnchor="middle" className="agent-label" fill={labelFill}>
            Architect Agent
          </text>
          <rect x="435" y="318" width="105" height="28" rx="6" fill={chipFill} stroke={chipStroke} />
          <text x="487" y="337" textAnchor="middle" className="agent-label" fill={labelFill}>
            Engineer Agent
          </text>
        </g>

        <g className="zone-group">
          {/* Orchestration */}
          <rect x="590" y="280" width="250" height="80" rx="10" {...zone('8,145,178')} />
          <text x="715" y="308" textAnchor="middle" className="zone-label" fill={labelFill}>
            Orchestration
          </text>
          <rect x="605" y="318" width="220" height="28" rx="6" fill={chipFill} stroke={chipStroke} />
          <text x="715" y="337" textAnchor="middle" className="agent-label" fill={labelFill}>
            GC Orchestrator / Agent Registry
          </text>
        </g>

        {/* Agent Registry bar at bottom */}
        <rect x="20" y="385" width="820" height="28" rx="8" fill={registryFill} stroke={registryStroke} />
        <text x="430" y="404" textAnchor="middle" className="registry-text" fill={registryTextFill}>
          TACO Agent Registry — discover agents by trade, CSI division, task type, and platform
        </text>
      </svg>
    </>
  );
}
