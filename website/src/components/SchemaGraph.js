import Link from '@docusaurus/Link';

/**
 * Visualizes how TACO's 6 schemas feed into each other across a typical
 * project workflow. Schemas are positioned by their role in the lifecycle:
 *   row 1 (sources):  bom-v1, rfi-v1
 *   row 2 (derived):  estimate-v1, quote-v1, schedule-v1
 *   row 3 (impact):   change-order-v1
 *
 * Edges encode the "consumes" relationship — an arrow from A to B means
 * the workflow that produces B normally takes A as input.
 */

const W = 720;
const H = 420;

const NODES = [
  {id: 'bom-v1', label: 'bom-v1', title: 'Bill of Materials', x: 110, y: 70, accent: '#3b82f6'},
  {id: 'rfi-v1', label: 'rfi-v1', title: 'Request for Information', x: 580, y: 70, accent: '#8b5cf6'},
  {id: 'estimate-v1', label: 'estimate-v1', title: 'Cost Estimate', x: 110, y: 210, accent: '#22c55e'},
  {id: 'quote-v1', label: 'quote-v1', title: 'Supplier Quote', x: 320, y: 210, accent: '#f59e0b'},
  {id: 'schedule-v1', label: 'schedule-v1', title: 'Project Schedule', x: 530, y: 210, accent: '#06b6d4'},
  {id: 'change-order-v1', label: 'change-order-v1', title: 'Change Order', x: 320, y: 350, accent: '#ef4444'},
];

const EDGES = [
  {from: 'bom-v1', to: 'estimate-v1'},
  {from: 'bom-v1', to: 'quote-v1'},
  {from: 'estimate-v1', to: 'change-order-v1'},
  {from: 'schedule-v1', to: 'change-order-v1'},
];

const NODE_W = 170;
const NODE_H = 64;

function nodeById(id) {
  return NODES.find((n) => n.id === id);
}

function edgePath(from, to) {
  // Anchor points at vertical centers of each node's facing edge
  const x1 = from.x + NODE_W / 2;
  const y1 = from.y + NODE_H;
  const x2 = to.x + NODE_W / 2;
  const y2 = to.y;
  const midY = (y1 + y2) / 2;
  return `M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2 - 6}`;
}

export default function SchemaGraph() {
  return (
    <div className="schema-graph">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="schema-graph__svg"
        role="img"
        aria-label="Diagram of how TACO schemas feed into each other across a construction workflow">
        <defs>
          <marker
            id="schema-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" className="schema-graph__arrow" />
          </marker>
        </defs>

        {/* Edges first so nodes draw on top */}
        {EDGES.map((e, i) => {
          const a = nodeById(e.from);
          const b = nodeById(e.to);
          if (!a || !b) return null;
          return (
            <path
              key={i}
              d={edgePath(a, b)}
              className="schema-graph__edge"
              markerEnd="url(#schema-arrow)"
            />
          );
        })}

        {NODES.map((n) => (
          <Link to={`/docs/schemas/${n.id}`} key={n.id}>
            <g className="schema-graph__node-group">
              <rect
                x={n.x}
                y={n.y}
                width={NODE_W}
                height={NODE_H}
                rx={10}
                className="schema-graph__node"
                style={{stroke: n.accent}}
              />
              <text
                x={n.x + NODE_W / 2}
                y={n.y + 26}
                textAnchor="middle"
                className="schema-graph__node-label">
                {n.label}
              </text>
              <text
                x={n.x + NODE_W / 2}
                y={n.y + 46}
                textAnchor="middle"
                className="schema-graph__node-sub">
                {n.title}
              </text>
            </g>
          </Link>
        ))}

        {/* Row labels (left margin) */}
        <text x={20} y={106} className="schema-graph__row-label">
          Sources
        </text>
        <text x={20} y={246} className="schema-graph__row-label">
          Derived
        </text>
        <text x={20} y={386} className="schema-graph__row-label">
          Impact
        </text>
      </svg>
      <p className="schema-graph__caption">
        Each arrow represents a typical workflow handoff — the source schema is the
        normal input to an agent that produces the target. Click any node to open
        its explorer.
      </p>
    </div>
  );
}
