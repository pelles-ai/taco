// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    'why-taco',
    'intro',
    'protocol-stack',
    'core-concepts',
    {
      type: 'category',
      label: 'Getting Started',
      collapsed: false,
      items: [
        'getting-started/quick-start',
        'getting-started/build-agent',
        'getting-started/multi-agent',
        'getting-started/integrate-platform',
      ],
    },
    'task-types',
    'agent-card-extensions',
    {
      type: 'category',
      label: 'Data Schemas',
      link: {
        type: 'doc',
        id: 'schemas/index',
      },
      items: [
        'schemas/bom-v1',
        'schemas/rfi-v1',
        'schemas/estimate-v1',
        'schemas/schedule-v1',
        'schemas/quote-v1',
        'schemas/change-order-v1',
      ],
    },
    'sdk',
    'cli',
    'security',
    'examples',
  ],
};

export default sidebars;
