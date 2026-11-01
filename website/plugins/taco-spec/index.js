// @ts-check
/**
 * taco-spec: feeds the site from the canonical spec in ../spec at build time.
 *
 * - Reads every JSON Schema in spec/schemas and the task-type tables in
 *   spec/task-types.md, and exposes them to components via global data
 *   (usePluginData('taco-spec')). Nothing is hand-copied into the site.
 * - Validates every example in src/data/schema-examples against its schema
 *   and fails the build if one is invalid, so the examples shown on the
 *   schema pages can never drift from the schemas.
 * - Serves each schema at /schemas/<name>.json (dev and build) by adding a
 *   copy step to the client webpack build.
 */

const fs = require('node:fs');
const path = require('node:path');
const Ajv2020 = require('ajv/dist/2020').default;
const addFormats = require('ajv-formats').default;

const SPEC_DIR = path.resolve(__dirname, '..', '..', '..', 'spec');
const SCHEMA_DIR = path.join(SPEC_DIR, 'schemas');
const TASK_TYPES_MD = path.join(SPEC_DIR, 'task-types.md');
const EXTENSIONS_MD = path.join(SPEC_DIR, 'agent-card-extensions.md');
const EXAMPLES_DIR = path.resolve(__dirname, '..', '..', 'src', 'data', 'schema-examples');

/** Backticked identifiers in a table cell, e.g. "`bom-v1` + `estimate-v1`". */
function codeNames(cell) {
  return [...cell.matchAll(/`([a-z0-9-]+)`/g)].map((m) => m[1]);
}

/**
 * Parse the phase sections of spec/task-types.md. Each "## Phase" heading is
 * followed by a table whose rows are:
 *   | `task-type` | description | typical input | output schema |
 */
function parseTaskTypes(md) {
  const out = [];
  let phase = null;
  for (const line of md.split('\n')) {
    const heading = line.match(/^##\s+(.+?)\s*$/);
    if (heading) {
      phase = heading[1];
      continue;
    }
    const row = line.match(/^\|\s*`([a-z0-9-]+)`\s*\|(.*)\|\s*$/);
    if (row && phase) {
      const cells = row[2].split('|').map((c) => c.trim());
      const [description = '', input = '', output = ''] = cells;
      out.push({
        id: row[1],
        phase,
        description,
        inputText: input.replace(/`/g, ''),
        inputSchemas: codeNames(input),
        outputText: output.replace(/`/g, ''),
        outputSchema: codeNames(output)[0] || null,
      });
    }
  }
  return out;
}

module.exports = function tacoSpecPlugin(context) {
  return {
    name: 'taco-spec',

    getPathsToWatch() {
      return [path.join(SCHEMA_DIR, '*.json'), TASK_TYPES_MD, EXTENSIONS_MD, path.join(EXAMPLES_DIR, '*.json')];
    },

    async loadContent() {
      const schemas = {};
      for (const file of fs.readdirSync(SCHEMA_DIR).filter((f) => f.endsWith('.json')).sort()) {
        schemas[file.replace(/\.json$/, '')] = JSON.parse(
          fs.readFileSync(path.join(SCHEMA_DIR, file), 'utf8'),
        );
      }

      // Examples: one per schema, validated here so a bad example fails the build.
      const ajv = new Ajv2020({allErrors: true, strict: false});
      addFormats(ajv);
      const examples = {};
      const problems = [];
      for (const [id, schema] of Object.entries(schemas)) {
        const file = path.join(EXAMPLES_DIR, `${id}.json`);
        if (!fs.existsSync(file)) {
          problems.push(`${id}: no example at src/data/schema-examples/${id}.json`);
          continue;
        }
        const example = JSON.parse(fs.readFileSync(file, 'utf8'));
        const {$id, ...rest} = schema;
        const validate = ajv.compile(rest);
        if (!validate(example)) {
          const detail = (validate.errors || [])
            .map((e) => `    ${e.instancePath || '/'} ${e.message}`)
            .join('\n');
          problems.push(`${id}: example does not validate\n${detail}`);
        }
        examples[id] = example;
      }
      if (problems.length) {
        throw new Error(`[taco-spec] Schema examples are invalid:\n${problems.join('\n')}`);
      }

      const taskTypes = parseTaskTypes(fs.readFileSync(TASK_TYPES_MD, 'utf8'));

      // Workflow relationships, derived from the task-type table: a task type
      // consumes its input schemas and produces its output schema.
      const relationships = {};
      for (const id of Object.keys(schemas)) {
        relationships[id] = {producedBy: [], consumedBy: [], consumes: []};
      }
      for (const t of taskTypes) {
        const out = t.outputSchema;
        if (out && relationships[out]) {
          relationships[out].producedBy.push(t.id);
          for (const input of t.inputSchemas) {
            if (relationships[input] && !relationships[out].consumes.includes(input)) {
              relationships[out].consumes.push(input);
            }
          }
        }
        for (const input of t.inputSchemas) {
          if (relationships[input]) relationships[input].consumedBy.push(t.id);
        }
      }

      // Recognized trades and the extension URI, from spec/agent-card-extensions.md.
      const extMd = fs.readFileSync(EXTENSIONS_MD, 'utf8');
      const tradeRow = extMd.split('\n').find((l) => /^\|\s*`trade`\s*\|/.test(l));
      const trades = tradeRow ? codeNames(tradeRow.split('Values:')[1] || '') : [];
      const uriMatch = extMd.match(/https:\/\/[^\s"`)]+\/extensions\/x-construction\/v\d+/);
      if (!trades.length || !uriMatch) {
        throw new Error('[taco-spec] Could not read trades or the extension URI from spec/agent-card-extensions.md');
      }

      return {
        schemas,
        examples,
        taskTypes,
        relationships,
        trades,
        extensionUri: uriMatch[0],
      };
    },

    async contentLoaded({content, actions}) {
      actions.setGlobalData(content);
    },

    configureWebpack(config, isServer) {
      if (isServer) return {};
      const CopyPlugin = require('copy-webpack-plugin');
      return {
        plugins: [
          new CopyPlugin({
            patterns: [{from: path.join(SCHEMA_DIR, '*.json'), to: 'schemas/[name][ext]'}],
          }),
        ],
      };
    },
  };
};
