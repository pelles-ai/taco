import Link from '@docusaurus/Link';

const COMPLEXITY_LABEL = {
  beginner: 'Beginner',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
};

export default function RecipeCard({
  slug,
  title,
  blurb,
  agents,
  schemas,
  taskTypes,
  readTime,
  complexity = 'intermediate',
}) {
  return (
    <Link to={`/docs/cookbook/${slug}`} className="recipe-card">
      <div className="recipe-card__head">
        <span className={`recipe-card__complexity recipe-card__complexity--${complexity}`}>
          {COMPLEXITY_LABEL[complexity] || complexity}
        </span>
        {readTime ? (
          <span className="recipe-card__read-time">{readTime} read</span>
        ) : null}
      </div>
      <div className="recipe-card__title">{title}</div>
      <div className="recipe-card__blurb">{blurb}</div>
      <div className="recipe-card__meta">
        {agents ? (
          <div className="recipe-card__meta-row">
            <span className="recipe-card__meta-label">Agents</span>
            <span className="recipe-card__meta-value">{agents}</span>
          </div>
        ) : null}
        {schemas?.length ? (
          <div className="recipe-card__meta-row">
            <span className="recipe-card__meta-label">Schemas</span>
            <span className="recipe-card__meta-chips">
              {schemas.map((s) => (
                <code key={s}>{s}</code>
              ))}
            </span>
          </div>
        ) : null}
        {taskTypes?.length ? (
          <div className="recipe-card__meta-row">
            <span className="recipe-card__meta-label">Task types</span>
            <span className="recipe-card__meta-chips">
              {taskTypes.map((t) => (
                <code key={t}>{t}</code>
              ))}
            </span>
          </div>
        ) : null}
      </div>
    </Link>
  );
}
