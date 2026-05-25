/**
 * Sequence diagram for cookbook recipes.
 *
 * Renders actors as labeled columns with lifelines, and messages as labeled
 * arrows between them. Each message can carry a TACO schema badge (bom-v1,
 * estimate-v1, …) so the typed data flow is visible at a glance.
 *
 * Props:
 *   actors:   [{ id, label, sub? }]
 *   messages: [{ from, to, label, schema?, note?, kind?: 'call' | 'return' }]
 *
 * Layout math is deterministic — width scales with actor count, height with
 * message count. No layout libs, no measurement, SSR-safe.
 */

const ACTOR_W = 160;
const ACTOR_H = 56;
const ACTOR_GAP = 80;
const MSG_GAP = 70;
const TOP_PAD = 8;
const BOTTOM_PAD = 32;
const SIDE_PAD = 16;

export default function SequenceDiagram({actors, messages}) {
  const n = actors.length;
  const width =
    SIDE_PAD * 2 + n * ACTOR_W + (n - 1) * ACTOR_GAP;
  const height =
    TOP_PAD + ACTOR_H + MSG_GAP * (messages.length + 1) + BOTTOM_PAD;

  const actorX = (i) => SIDE_PAD + i * (ACTOR_W + ACTOR_GAP);
  const actorCenter = (i) => actorX(i) + ACTOR_W / 2;

  const actorIndex = Object.fromEntries(actors.map((a, i) => [a.id, i]));
  const lifelineBottom = height - BOTTOM_PAD;

  return (
    <div className="seq-diagram">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="seq-diagram__svg"
        role="img"
        aria-label="Sequence diagram of messages between agents">
        <defs>
          <marker
            id="seq-arrow-call"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" className="seq-diagram__arrowhead" />
          </marker>
          <marker
            id="seq-arrow-return"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse">
            <path
              d="M 0 0 L 10 5 L 0 10 z"
              className="seq-diagram__arrowhead seq-diagram__arrowhead--return"
            />
          </marker>
        </defs>

        {/* Actor headers + lifelines */}
        {actors.map((a, i) => (
          <g key={a.id} className="seq-diagram__actor-col">
            <rect
              x={actorX(i)}
              y={TOP_PAD}
              width={ACTOR_W}
              height={ACTOR_H}
              rx={10}
              className="seq-diagram__actor"
            />
            <text
              x={actorCenter(i)}
              y={TOP_PAD + 22}
              textAnchor="middle"
              className="seq-diagram__actor-label">
              {a.label}
            </text>
            {a.sub ? (
              <text
                x={actorCenter(i)}
                y={TOP_PAD + 40}
                textAnchor="middle"
                className="seq-diagram__actor-sub">
                {a.sub}
              </text>
            ) : null}
            <line
              x1={actorCenter(i)}
              y1={TOP_PAD + ACTOR_H}
              x2={actorCenter(i)}
              y2={lifelineBottom}
              className="seq-diagram__lifeline"
            />
          </g>
        ))}

        {/* Messages */}
        {messages.map((m, i) => {
          const fromIdx = actorIndex[m.from];
          const toIdx = actorIndex[m.to];
          if (fromIdx === undefined || toIdx === undefined) return null;
          const y = TOP_PAD + ACTOR_H + MSG_GAP * (i + 1);
          const x1 = actorCenter(fromIdx);
          const x2 = actorCenter(toIdx);
          const isReturn = m.kind === 'return';
          const reverse = x1 > x2;
          const labelMid = (x1 + x2) / 2;

          return (
            <g key={i} className="seq-diagram__msg-group">
              <line
                x1={x1}
                y1={y}
                x2={x2}
                y2={y}
                className={`seq-diagram__msg-line ${
                  isReturn ? 'seq-diagram__msg-line--return' : ''
                }`}
                markerEnd={`url(#${isReturn ? 'seq-arrow-return' : 'seq-arrow-call'})`}
              />
              <text
                x={labelMid}
                y={y - 8}
                textAnchor="middle"
                className="seq-diagram__msg-label">
                {m.label}
              </text>
              {m.schema ? (
                <g
                  transform={`translate(${labelMid - 38}, ${y + 6})`}
                  className="seq-diagram__schema">
                  <rect
                    width={76}
                    height={18}
                    rx={9}
                    className="seq-diagram__schema-bg"
                  />
                  <text
                    x={38}
                    y={12}
                    textAnchor="middle"
                    className="seq-diagram__schema-label">
                    {m.schema}
                  </text>
                </g>
              ) : null}
              {m.note ? (
                <text
                  x={labelMid}
                  y={y + 32}
                  textAnchor="middle"
                  className="seq-diagram__msg-note">
                  {m.note}
                </text>
              ) : null}
              {/* tiny direction indicator for self-aware reading order */}
              {!reverse && false /* hook for future numbering */}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
