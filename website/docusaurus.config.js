// @ts-check

import {themes as prismThemes} from 'prism-react-renderer';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'TACO',
  tagline: 'The A2A Construction Open-standard',
  favicon: 'img/favicon.ico',

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
        name: 'keywords',
        content:
          'construction, AI, agent, A2A, protocol, agent-to-agent, open standard, construction technology, BIM, takeoff, estimating',
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
        description:
          'An open-source construction ontology layer built on the A2A protocol. Defines task types, data schemas, and agent discovery for construction AI.',
        applicationCategory: 'DeveloperApplication',
        operatingSystem: 'Cross-platform',
        license: 'https://opensource.org/licenses/Apache-2.0',
        version: '0.2.5',
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

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      image: 'img/taco-social-card.png',
      announcementBar: {
        id: 'active_development',
        content:
          'TACO is in active development. <a href="https://github.com/pelles-ai/taco">Star us on GitHub</a> and help shape the standard.',
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
            value:
              '<a href="https://pypi.org/project/taco-agent/" target="_blank" rel="noopener noreferrer" class="navbar__version-badge">v0.2</a>',
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
              {
                label: 'Introduction',
                to: '/docs/intro',
              },
              {
                label: 'Build Your First Agent',
                to: '/docs/getting-started/build-agent',
              },
              {
                label: 'Task Types',
                to: '/docs/task-types',
              },
              {
                label: 'Data Schemas',
                to: '/docs/schemas/',
              },
            ],
          },
          {
            title: 'SDK',
            items: [
              {
                label: 'SDK Guide',
                to: '/docs/sdk',
              },
              {
                label: 'PyPI',
                href: 'https://pypi.org/project/taco-agent/',
              },
              {
                label: 'Agent Card Extensions',
                to: '/docs/agent-card-extensions',
              },
              {
                label: 'Security',
                to: '/docs/security',
              },
            ],
          },
          {
            title: 'Community',
            items: [
              {
                label: 'GitHub Discussions',
                href: 'https://github.com/pelles-ai/taco/discussions',
              },
              {
                label: 'Issues',
                href: 'https://github.com/pelles-ai/taco/issues',
              },
              {
                label: 'Contributing',
                href: 'https://github.com/pelles-ai/taco/blob/main/CONTRIBUTING.md',
              },
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'GitHub',
                href: 'https://github.com/pelles-ai/taco',
              },
              {
                label: 'A2A Protocol',
                href: 'https://a2a-protocol.org',
              },
              {
                label: 'Linux Foundation',
                href: 'https://www.linuxfoundation.org/',
              },
              {
                label: 'Pelles',
                href: 'https://pelles.ai',
              },
              {
                label: 'Blog',
                to: '/blog',
              },
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
