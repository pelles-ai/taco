// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    {
      type: 'category',
      label: 'Overview',
      collapsed: false,
      items: ['why-taco', 'intro', 'scope'],
    },
    {
      type: 'category',
      label: 'Concepts',
      collapsed: false,
      items: [
        'protocol-stack',
        'core-concepts',
        'task-types',
        'agent-card-extensions',
        'security',
      ],
    },
    {
      type: 'category',
      label: 'Build',
      collapsed: false,
      items: [
        'getting-started/quick-start',
        'getting-started/build-agent',
        'getting-started/multi-agent',
        'getting-started/integrate-platform',
        'best-practices',
        'pitfalls',
        'examples',
      ],
    },
    {
      type: 'category',
      label: 'Cookbook',
      collapsed: true,
      link: {type: 'doc', id: 'cookbook/index'},
      items: [
        'cookbook/gc-estimator-supplier-chain',
        'cookbook/rfi-round-trip',
        'cookbook/bom-to-quote-marketplace',
        'cookbook/change-order-impact',
        'cookbook/schedule-aware-procurement',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      collapsed: false,
      items: [
        'sdk',
        'cli',
        {
          type: 'category',
          label: 'SDK Reference',
          link: {type: 'doc', id: 'sdk-reference/index'},
          collapsed: true,
          items: [
            'sdk-reference/agent-cards',
            'sdk-reference/server',
            'sdk-reference/client',
            'sdk-reference/agent',
            'sdk-reference/registry',
            'sdk-reference/tasks-and-messages',
            'sdk-reference/helpers',
            'sdk-reference/persistence',
            'sdk-reference/push-notifications',
            'sdk-reference/enums',
          ],
        },
        {
          type: 'category',
          label: 'Data Schemas',
          link: {type: 'doc', id: 'schemas/index'},
          collapsed: true,
          items: [
            'schemas/bom-v1',
            'schemas/rfi-v1',
            'schemas/estimate-v1',
            'schemas/schedule-v1',
            'schemas/quote-v1',
            'schemas/change-order-v1',
          ],
        },
        'glossary',
      ],
    },
    {
      type: 'category',
      label: 'Specification',
      collapsed: true,
      link: {type: 'doc', id: 'spec/index'},
      items: [
        'spec/SPEC-001-agent-cards',
        'spec/SPEC-002-task-types',
        'spec/SPEC-003-data-schemas',
        'spec/SPEC-004-security',
        'spec/SPEC-005-conformance',
      ],
    },
    {
      type: 'category',
      label: 'Project',
      collapsed: true,
      items: [
        'roadmap',
        'changelog',
        'ecosystem',
        'compare',
        'standards',
        {
          type: 'category',
          label: 'Architecture Decisions',
          link: {type: 'doc', id: 'decisions/index'},
          collapsed: true,
          items: [
            'decisions/build-on-a2a',
            'decisions/json-schema-source-of-truth',
            'decisions/construction-shaped-scopes',
            'decisions/sidecar-pattern',
            'decisions/in-memory-registry-first',
            'decisions/schema-versioning',
            'decisions/v1-wire-cutover',
            'decisions/in-browser-playground',
            'decisions/extension-uri-naming',
          ],
        },
      ],
    },
  ],
};

export default sidebars;
