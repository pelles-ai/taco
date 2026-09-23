import Link from '@docusaurus/Link';
import {usePluginData} from '@docusaurus/useGlobalData';

/**
 * How the six schemas feed each other, drawn from the task-type table in
 * spec/task-types.md: an arrow runs from each input schema to the output
 * schema of the task type that consumes it. Node positions are laid out by
 * hand for the current schemas; a schema added later falls into a spare
 * slot on the right until it is given a place.
 */

const W = 900;
const H = 380;
const NODE_W = 150;
const NODE_H = 58;

const POSITIONS = {
  'bom-v1': [205, 190],
  'rfi-v1': [440, 60],
  'estimate-v1': [440, 190],
  'quote-v1': [440, 320],
  'schedule-v1': [645, 100],
  'change-order-v1': [820, 255],
};
const SOURCE = [16, 190];

// Edges that skip a column are routed through the gap between rows so they
// don't run behind the boxes in between.
const ROUTES = {
  'bom-v1>schedule-v1': ([x1, y1], [x2, y2]) =>
    `M ${x1 + NODE_W / 2} ${y1} C ${x1 + 125} ${y1}, ${x1 + 105} 125, ${x1 + 175} 125 L ${x2 - NODE_W / 2 - 40} 125 C ${x2 - NODE_W / 2 - 20} 125, ${x2 - NODE_W / 2 - 20} ${y2}, ${x2 - NODE_W / 2 - 6} ${y2}`,
  'bom-v1>change-order-v1': ([x1, y1], [x2, y2]) =>
    `M ${x1 + NODE_W / 2} ${y1} C ${x1 + 125} ${y1}, ${x1 + 105} ${y2}, ${x1 + 175} ${y2} L ${x2 - NODE_W / 2 - 6} ${y2}`,
};

function centre(id, spare) {
  return POSITIONS[id] || spare[id];
}

function edgePath([x1, y1], [x2, y2]) {
  const sx = x1 + NODE_W / 2;
  const tx = x2 - NODE_W / 2;
  const mid = (sx + tx) / 2;
  return `M ${sx} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${tx - 6} ${y2}`;
}

export default function SchemaGraph() {
  const {schemas, taskTypes} = usePluginData('taco-spec');
  const ids = Object.keys(schemas);

  const spare = {};
  ids
    .filter((id) => !POSITIONS[id])
    .forEach((id, i) => {
      spare[id] = [W - NODE_W / 2 - 10, 40 + i * 70];
    });

  const edges = [];
  const producedBy = {};
  for (const t of taskTypes) {
    const out = t.outputSchema;
    if (!out || !schemas[out]) continue;
    (producedBy[out] = producedBy[out] || []).push(t.id);
    for (const input of t.inputSchemas) {
      if (schemas[input] && input !== out) {
        edges.push({from: input, to: out, task: t.id, key: `${input}-${out}-${t.id}`});
      }
    }
  }
  const fromDrawings = taskTypes.filter(
    (t) => t.outputSchema && schemas[t.outputSchema] && t.inputSchemas.length === 0,
  );

  return (
    <figure className="sgraph">
      <div className="sgraph__scroll">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="sgraph__svg"
          role="img"
          aria-label={`How TACO schemas feed each other. ${edges
            .map((e) => `${e.from} feeds ${e.to} through ${e.task}`)
            .join('. ')}.`}>
          <defs>
            <marker
              id="sgraph-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto">
              <path d="M 0 0 L 10 5 L 0 10 z" className="sgraph__arrowhead" />
            </marker>
          </defs>

          {fromDrawings.map((t) => {
            const target = centre(t.outputSchema, spare);
            return (
              <g key={`src-${t.id}`}>
                <text x={SOURCE[0]} y={SOURCE[1] - 6} className="sgraph__source">
                  drawings
                </text>
                <text x={SOURCE[0]} y={SOURCE[1] + 10} className="sgraph__source">
                  and specs
                </text>
                <path
                  d={`M ${SOURCE[0] + 72} ${SOURCE[1]} L ${target[0] - NODE_W / 2 - 6} ${target[1]}`}
                  className="sgraph__edge sgraph__edge--source"
                  markerEnd="url(#sgraph-arrow)"
                />
              </g>
            );
          })}

          {edges.map((e) => (
            <path
              key={e.key}
              d={(ROUTES[`${e.from}>${e.to}`] || edgePath)(centre(e.from, spare), centre(e.to, spare))}
              className="sgraph__edge"
              markerEnd="url(#sgraph-arrow)"
            />
          ))}

          {ids.map((id) => {
            const [cx, cy] = centre(id, spare);
            const via = (producedBy[id] || []).join(', ');
            return (
              <Link key={id} to={`/docs/schemas/${id}`} className="sgraph__node">
                <rect
                  x={cx - NODE_W / 2}
                  y={cy - NODE_H / 2}
                  width={NODE_W}
                  height={NODE_H}
                  rx={3}
                  className="sgraph__box"
                />
                <text x={cx} y={cy - 4} textAnchor="middle" className="sgraph__id">
                  {id}
                </text>
                {via ? (
                  <text x={cx} y={cy + 15} textAnchor="middle" className="sgraph__via">
                    {via}
                  </text>
                ) : null}
              </Link>
            );
          })}
        </svg>
      </div>
      <figcaption className="sgraph__caption">
        Each box is a schema, labelled with the task type that produces it. Arrows show
        which schemas a task type reads. Generated from the task-type table in the spec.
      </figcaption>
    </figure>
  );
}
