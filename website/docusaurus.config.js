// @ts-check

import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {themes as prismThemes} from 'prism-react-renderer';

/* ------------------------------------------------------------------
   Facts the homepage displays. Each one has a single source of truth
   in the repo so the site never carries a hand-typed number.
   ------------------------------------------------------------------ */

const REPO_ROOT = path.resolve(process.cwd(), '..');

/** Latest semver git tag (v0.3.13 -> 0.3.13). Falls back when git or tags are unavailable. */
function readSdkVersion() {
  const fallback = '0.3.13';
  try {
    const tag = execFileSync('git', ['describe', '--tags', '--abbrev=0', '--match', 'v*'], {
      stdio: ['ignore', 'pipe', 'ignore'],
    })
      .toString()
      .trim();
    return tag.startsWith('v') ? tag.slice(1) : tag || fallback;
  } catch {
    return fallback;
  }
}

/** Rows of the form "| `task-type` | ..." in spec/task-types.md. */
function countTaskTypes() {
  try {
    const md = fs.readFileSync(path.join(REPO_ROOT, 'spec', 'task-types.md'), 'utf8');
    const n = md.split('\n').filter((line) => /^\|\s*`[a-z0-9-]+`\s*\|/.test(line)).length;
    return n || 18;
  } catch {
    return 18;
  }
}

/** JSON schema files in spec/schemas. */
function countSchemas() {
  try {
    const n = fs
      .readdirSync(path.join(REPO_ROOT, 'spec', 'schemas'))
      .filter((f) => f.endsWith('.json')).length;
    return n || 6;
  } catch {
    return 6;
  }
}

const SDK_VERSION = readSdkVersion();
const PROTOCOL_VERSION = SDK_VERSION.split('.').slice(0, 2).join('.');
const TASK_TYPE_COUNT = countTaskTypes();
const SCHEMA_COUNT = countSchemas();

const SITE_DESCRIPTION =
  'TACO is the open standard that lets construction AI agents hand work to each other: typed task types, typed data schemas and discovery by trade and CSI division, on top of the A2A protocol.';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'TACO',
  tagline: 'One vocabulary for every construction agent',
  favicon: 'img/favicon.ico',

  customFields: {
    sdkVersion: SDK_VERSION,
    protocolVersion: PROTOCOL_VERSION,
    taskTypeCount: TASK_TYPE_COUNT,
    schemaCount: SCHEMA_COUNT,
    // Where the playground loads Pyodide from. Unset means the Pyodide CDN;
    // set it at build time to self-host Pyodide or to test without the CDN.
    pyodideIndexUrl: process.env.PYODIDE_INDEX_URL || null,
  },

  future: {
    v4: true,
  },

  url: 'https://taco-protocol.com',
  baseUrl: '/',

  organizationName: 'pelles-ai',
  projectName: 'taco',

  onBrokenLinks: 'throw',

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'throw',
    },
  },

  headTags: [
    {
      tagName: 'link',
      attributes: {
        rel: 'preload',
        href: '/fonts/archivo-variable.woff2',
        as: 'font',
        type: 'font/woff2',
        crossorigin: 'anonymous',
      },
    },
    {
      tagName: 'link',
      attributes: {
        rel: 'preload',
        href: '/fonts/inter-variable.woff2',
        as: 'font',
        type: 'font/woff2',
        crossorigin: 'anonymous',
      },
    },
    {
      tagName: 'link',
      attributes: {
        rel: 'preload',
        href: '/fonts/jetbrains-mono-variable.woff2',
        as: 'font',
        type: 'font/woff2',
        crossorigin: 'anonymous',
      },
    },
    {
      tagName: 'meta',
      attributes: {
        name: 'description',
        content: SITE_DESCRIPTION,
      },
    },
    {
      tagName: 'meta',
      attributes: {
        name: 'keywords',
        content:
          'construction, AI, agent, A2A, protocol, agent-to-agent, open standard, construction technology, BIM, takeoff, estimating, RFI, CSI division',
      },
    },
    {
      tagName: 'script',
      attributes: {
        type: 'application/ld+json',
      },
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'SoftwareApplication',
        name: 'TACO — The A2A Construction Open-standard',
        description: SITE_DESCRIPTION,
        applicationCategory: 'DeveloperApplication',
        operatingSystem: 'Cross-platform',
        license: 'https://opensource.org/licenses/Apache-2.0',
        softwareVersion: SDK_VERSION,
        codeRepository: 'https://github.com/pelles-ai/taco',
        url: 'https://taco-protocol.com',
      }),
    },
  ],

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          editUrl: 'https://github.com/pelles-ai/taco/tree/main/website/',
          showLastUpdateTime: true,
        },
        blog: {
          showReadingTime: true,
          editUrl: 'https://github.com/pelles-ai/taco/tree/main/website/',
          onInlineAuthors: 'ignore',
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  plugins: ['./plugins/taco-spec'],

  themes: [
    [
      '@easyops-cn/docusaurus-search-local',
      /** @type {import('@easyops-cn/docusaurus-search-local').PluginOptions} */
      ({
        hashed: true,
        indexDocs: true,
        indexBlog: true,
        indexPages: false,
        docsRouteBasePath: '/docs',
        highlightSearchTermsOnTargetPage: true,
        explicitSearchResultPath: true,
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      image: 'img/taco-social-card.png',
      metadata: [{name: 'og:description', content: SITE_DESCRIPTION}],
      announcementBar: {
        id: 'active_development_0_3',
        content: `TACO ${PROTOCOL_VERSION} is an open standard in active development. <a href="https://github.com/pelles-ai/taco">Star the repo</a> and help write the schemas.`,
        isCloseable: true,
      },
      colorMode: {
        defaultMode: 'dark',
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: 'TACO',
        logo: {
          alt: 'TACO Logo',
          src: 'img/taco_logo.png',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'docsSidebar',
            position: 'left',
            label: 'Docs',
          },
          {
            to: '/docs/sdk',
            label: 'SDK',
            position: 'left',
          },
          {
            to: '/playground',
            label: 'Playground',
            position: 'left',
          },
          {
            href: 'https://github.com/pelles-ai/taco/tree/main/spec',
            label: 'Spec',
            position: 'left',
          },
          {
            href: 'https://github.com/pelles-ai/taco/discussions',
            label: 'Community',
            position: 'left',
          },
          {
            to: '/blog',
            label: 'Blog',
            position: 'left',
          },
          {
            type: 'html',
            position: 'right',
            value: `<a href="https://pypi.org/project/taco-agent/" target="_blank" rel="noopener noreferrer" class="navbar__version-badge" title="taco-agent ${SDK_VERSION} on PyPI">v${SDK_VERSION}</a>`,
          },
          {
            href: 'https://github.com/pelles-ai/taco',
            position: 'right',
            className: 'header-github-link',
            'aria-label': 'GitHub repository',
            html: '<svg viewBox="0 0 16 16" width="20" height="20" style="fill: currentColor;"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Learn',
            items: [
              {label: 'Why TACO?', to: '/docs/why-taco'},
              {label: 'Introduction', to: '/docs/intro'},
              {label: 'Build your first agent', to: '/docs/getting-started/build-agent'},
              {label: 'Task types', to: '/docs/task-types'},
              {label: 'Data schemas', to: '/docs/schemas/'},
            ],
          },
          {
            title: 'SDK',
            items: [
              {label: 'SDK guide', to: '/docs/sdk'},
              {label: 'Playground', to: '/playground'},
              {label: 'Conformance check', to: '/conformance'},
              {label: 'CLI', to: '/docs/cli'},
              {label: 'PyPI', href: 'https://pypi.org/project/taco-agent/'},
              {label: 'Agent card extensions', to: '/docs/agent-card-extensions'},
              {label: 'Security', to: '/docs/security'},
            ],
          },
          {
            title: 'Community',
            items: [
              {label: 'GitHub Discussions', href: 'https://github.com/pelles-ai/taco/discussions'},
              {label: 'Issues', href: 'https://github.com/pelles-ai/taco/issues'},
              {label: 'Contributing', href: 'https://github.com/pelles-ai/taco/blob/main/CONTRIBUTING.md'},
              {label: 'Changelog', to: '/docs/changelog'},
            ],
          },
          {
            title: 'More',
            items: [
              {label: 'GitHub', href: 'https://github.com/pelles-ai/taco'},
              {label: 'A2A Protocol', href: 'https://a2a-protocol.org'},
              {label: 'Linux Foundation', href: 'https://www.linuxfoundation.org/'},
              {label: 'Pelles', href: 'https://pelles.ai'},
              {label: 'Blog', to: '/blog'},
            ],
          },
        ],
        copyright: `Copyright ${new Date().getFullYear()} Pelles. Built on the A2A protocol (Linux Foundation). Apache 2.0.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['bash', 'json', 'python'],
      },
    }),
};

export default config;
