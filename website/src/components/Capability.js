import Link from '@docusaurus/Link';

/**
 * One concrete thing this audience can do with TACO today.
 * Group multiple via <CapabilityGrid> in the parent MDX.
 */
export function Capability({title, description, link}) {
  return (
    <div className="capability">
      <div className="capability__title">{title}</div>
      <div className="capability__desc">{description}</div>
      {link ? (
        <Link className="capability__link" to={link.to} href={link.href}>
          {link.label} &rarr;
        </Link>
      ) : null}
    </div>
  );
}

export function CapabilityGrid({children}) {
  return <div className="capability-grid">{children}</div>;
}
