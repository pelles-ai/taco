import Link from '@docusaurus/Link';

const ALL_RECIPES = {
  'gc-estimator-supplier-chain': {
    title: 'GC → Estimator → Supplier',
    blurb: 'Canonical three-hop chain. Takeoff to priced + sourced materials.',
  },
  'rfi-round-trip': {
    title: 'RFI Round-trip',
    blurb: 'Auditor flags a conflict, design responder drafts a typed reply.',
  },
  'bom-to-quote-marketplace': {
    title: 'BOM-to-Quote Marketplace',
    blurb: 'Fan a BOM out to many suppliers in parallel, level the quotes.',
  },
  'change-order-impact': {
    title: 'Change Order Impact',
    blurb: 'Live cost + schedule delta from the current baselines.',
  },
  'schedule-aware-procurement': {
    title: 'Schedule-Aware Procurement',
    blurb: 'Reject quotes whose lead time pushes past the activity start.',
  },
};

/**
 * Curated row of cookbook recipes most relevant to this audience.
 * Pass an array of recipe slugs in display order.
 */
export default function RecipeRail({slugs}) {
  return (
    <div className="recipe-rail">
      {slugs.map((slug) => {
        const r = ALL_RECIPES[slug];
        if (!r) return null;
        return (
          <Link
            to={`/docs/cookbook/${slug}`}
            key={slug}
            className="recipe-rail__item">
            <div className="recipe-rail__title">{r.title}</div>
            <div className="recipe-rail__blurb">{r.blurb}</div>
            <div className="recipe-rail__cta">Read recipe &rarr;</div>
          </Link>
        );
      })}
    </div>
  );
}
