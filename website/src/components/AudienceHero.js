import Heading from '@theme/Heading';
import Link from '@docusaurus/Link';

/**
 * Per-role page header. Smaller than the homepage hero — this page is a
 * landing for a specific audience, not the front door.
 */
export default function AudienceHero({
  role,
  title,
  subtitle,
  primaryCta,
  secondaryCta,
}) {
  return (
    <header className="audience-hero">
      <div className="container">
        <span className="audience-hero__role">For {role}</span>
        <Heading as="h1" className="audience-hero__title">
          {title}
        </Heading>
        <p className="audience-hero__subtitle">{subtitle}</p>
        {(primaryCta || secondaryCta) && (
          <div className="audience-hero__ctas">
            {primaryCta && (
              <Link
                className="button button--lg button--accent"
                to={primaryCta.to}
                href={primaryCta.href}>
                {primaryCta.label}
              </Link>
            )}
            {secondaryCta && (
              <Link
                className="button button--lg button--outline-light"
                to={secondaryCta.to}
                href={secondaryCta.href}>
                {secondaryCta.label}
              </Link>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
