/**
 * Sequence diagram: agents as labeled columns with lifelines, messages as
 * arrows between them. Each message can carry a TACO schema badge (bom-v1,
 * estimate-v1, ...) so the typed data flow is visible at a glance, and a
 * keynote number in the left gutter so the reading order is explicit.
 *
 * Props:
 *   actors:   [{ id, label, sub? }]
 *   messages: [{ from, to, label, schema?, note?, kind?: 'call' | 'return' }]
 *
 * Layout is deterministic: width scales with actor count, height with
 * message count. No layout libraries, no measurement, SSR-safe. Colors come
 * from CSS classes so the diagram follows the site theme.
 */

const GUTTER_W = 40;
const ACTOR_W = 168;
const ACTOR_H = 56;
const ACTOR_GAP = 84;
const MSG_GAP = 72;
const TOP_PAD = 8;
const BOTTOM_PAD = 28;
const SIDE_PAD = 12;

function Keynote({x, y, n}) {
  // Hexagon keynote marker, as used on drawing sheets.
  const r = 11;
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 3) * i + Math.PI / 6;
    pts.push(`${(x + r * Math.cos(a)).toFixed(2)},${(y + r * Math.sin(a)).toFixed(2)}`);
  }
  return (
    <g className="seq__keynote">
      <polygon points={pts.join(' ')} className="seq__keynote-shape" />
      <text x={x} y={y + 4} textAnchor="middle" className="seq__keynote-text">
        {n}
      </text>
    </g>
  );
}

export default function SequenceDiagram({actors, messages, ariaLabel}) {
  const n = actors.length;
  const width = GUTTER_W + SIDE_PAD * 2 + n * ACTOR_W + (n - 1) * ACTOR_GAP;
  const height = TOP_PAD + ACTOR_H + MSG_GAP * (messages.length + 1) + BOTTOM_PAD;

  const actorX = (i) => GUTTER_W + SIDE_PAD + i * (ACTOR_W + ACTOR_GAP);
  const actorCenter = (i) => actorX(i) + ACTOR_W / 2;
  const actorIndex = Object.fromEntries(actors.map((a, i) => [a.id, i]));
  const lifelineBottom = height - BOTTOM_PAD;

  return (
    <div className="seq">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="seq__svg"
        role="img"
        aria-label={ariaLabel || 'Sequence diagram of messages between agents'}>
        <defs>
          <marker
            id="seq-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" className="seq__arrowhead" />
          </marker>
        </defs>

        {actors.map((a, i) => (
          <g key={a.id} className="seq__actor-col">
            <rect
              x={actorX(i)}
              y={TOP_PAD}
              width={ACTOR_W}
              height={ACTOR_H}
              rx={3}
              className="seq__actor"
            />
            <text
              x={actorCenter(i)}
              y={TOP_PAD + 23}
              textAnchor="middle"
              className="seq__actor-label">
              {a.label}
            </text>
            {a.sub ? (
              <text
                x={actorCenter(i)}
                y={TOP_PAD + 41}
                textAnchor="middle"
                className="seq__actor-sub">
                {a.sub}
              </text>
            ) : null}
            <line
              x1={actorCenter(i)}
              y1={TOP_PAD + ACTOR_H}
              x2={actorCenter(i)}
              y2={lifelineBottom}
              className="seq__lifeline"
            />
          </g>
        ))}

        {messages.map((m, i) => {
          const fromIdx = actorIndex[m.from];
          const toIdx = actorIndex[m.to];
          if (fromIdx === undefined || toIdx === undefined) return null;
          const y = TOP_PAD + ACTOR_H + MSG_GAP * (i + 1);
          const x1 = actorCenter(fromIdx);
          const x2 = actorCenter(toIdx);
          const isReturn = m.kind === 'return';
          const labelMid = (x1 + x2) / 2;
          const badgeW = m.schema ? m.schema.length * 7.2 + 18 : 0;

          return (
            <g key={i} className="seq__msg">
              <Keynote x={GUTTER_W / 2} y={y} n={i + 1} />
              <line
                x1={x1}
                y1={y}
                x2={x2}
                y2={y}
                className={`seq__line ${isReturn ? 'seq__line--return' : ''}`}
                markerEnd="url(#seq-arrow)"
              />
              <text x={labelMid} y={y - 9} textAnchor="middle" className="seq__label">
                {m.label}
              </text>
              {m.schema ? (
                <g transform={`translate(${labelMid - badgeW / 2}, ${y + 7})`}>
                  <rect width={badgeW} height={19} rx={2} className="seq__schema-bg" />
                  <text x={badgeW / 2} y={13.5} textAnchor="middle" className="seq__schema">
                    {m.schema}
                  </text>
                </g>
              ) : null}
              {m.note ? (
                <text x={labelMid} y={y + 40} textAnchor="middle" className="seq__note">
                  {m.note}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
