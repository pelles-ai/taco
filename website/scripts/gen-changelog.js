#!/usr/bin/env node
/**
 * gen-changelog.js: copy ../CHANGELOG.md into docs/changelog.md with
 * Docusaurus frontmatter so the changelog renders in the docs, the sidebar
 * and the search index.
 *
 * Runs automatically before `npm run build` and `npm run start` via the
 * `prebuild` / `prestart` hooks. The output is gitignored: CHANGELOG.md at
 * the repo root is the only source of truth.
 */

const fs = require('node:fs');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const SOURCE = path.join(REPO_ROOT, 'CHANGELOG.md');
const TARGET = path.resolve(__dirname, '..', 'docs', 'changelog.md');

const FRONTMATTER = `---
title: Changelog
description: Every notable change to the TACO SDK, generated from CHANGELOG.md at the repo root.
custom_edit_url: https://github.com/pelles-ai/taco/edit/main/CHANGELOG.md
---

# Changelog

:::info Generated page
This page is copied from [\`CHANGELOG.md\`](https://github.com/pelles-ai/taco/blob/main/CHANGELOG.md) at build time. Edit that file, not this one.
:::

`;

function generate() {
  if (!fs.existsSync(SOURCE)) {
    console.error(`[gen-changelog] CHANGELOG.md not found at ${SOURCE}`);
    process.exit(1);
  }

  const raw = fs.readFileSync(SOURCE, 'utf8');

  // The source opens with `# Changelog`; the frontmatter block supplies the
  // page heading, so drop the duplicate. Everything else stays verbatim so
  // heading anchors (#unreleased, #01x--2026-03-15) remain stable.
  const body = raw.replace(/^#\s+Changelog\s*\n+/m, '');

  fs.mkdirSync(path.dirname(TARGET), {recursive: true});
  fs.writeFileSync(TARGET, FRONTMATTER + body.trim() + '\n');
  console.log(`[gen-changelog] wrote ${path.relative(REPO_ROOT, TARGET)}`);
}

generate();
