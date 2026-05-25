// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    'why-taco',
    'intro',
    'scope',
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
      collapsed: false,
      link: {
        type: 'doc',
        id: 'cookbook/index',
      },
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
      label: 'Case Studies',
      collapsed: true,
      link: {
        type: 'doc',
        id: 'case-studies/index',
      },
      items: [
        'case-studies/oakridge-medical-week',
        'case-studies/stafford-mechanical-onboarding',
        'case-studies/riverbend-transit-rfp',
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
          link: {
            type: 'doc',
            id: 'sdk-reference/index',
          },
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
          link: {
            type: 'doc',
            id: 'schemas/index',
          },
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
      ],
    },
    {
      type: 'category',
      label: 'Protocol & Community',
      collapsed: true,
      items: [
        {
          type: 'category',
          label: 'Specification',
          link: {type: 'doc', id: 'spec/index'},
          collapsed: true,
          items: [
            'spec/SPEC-001-agent-cards',
            'spec/SPEC-002-task-types',
            'spec/SPEC-003-data-schemas',
            'spec/SPEC-004-security',
            'spec/SPEC-005-conformance',
          ],
        },
        'roadmap',
        'changelog',
        'rfp-template',
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
            'decisions/pyodide-sandbox',
            'decisions/extension-uri-naming',
          ],
        },
        'ecosystem',
        'compare',
        'standards',
        'glossary',
      ],
    },
  ],
};

export default sidebars;
