import Link from '@docusaurus/Link';

const paths = [
  {
    title: 'Building an Agent',
    description: 'Create a TACO-compatible agent in 5 minutes. Define your trade, declare schemas, and start serving.',
    audience: 'Engineers',
    link: '/docs/getting-started/build-agent',
  },
  {
    title: 'Integrating a Platform',
    description: 'Add an agent sidecar to your existing construction platform. Map your capabilities to TACO task types.',
    audience: 'Platforms',
    link: '/docs/getting-started/integrate-platform',
  },
  {
    title: 'Contributing',
    description: 'Help define new task types, schemas, and the future of construction agent interoperability.',
    audience: 'Community',
    link: 'https://github.com/pelles-ai/taco/blob/main/CONTRIBUTING.md',
  },
];

export default function AudiencePaths() {
  return (
    <div className="path-list">
      {paths.map((p) => {
        const isExternal = p.link.startsWith('http');
        const Component = isExternal ? 'a' : Link;
        const props = isExternal
          ? {href: p.link, target: '_blank', rel: 'noopener noreferrer'}
          : {to: p.link};
        return (
          <Component className="path-row" key={p.title} {...props}>
            <span className="path-row__audience">{p.audience}</span>
            <span className="path-row__body">
              <span className="path-row__title">{p.title}</span>
              <span className="path-row__desc">{p.description}</span>
            </span>
            <span className="path-row__arrow" aria-hidden="true">&rarr;</span>
          </Component>
        );
      })}
    </div>
  );
}
