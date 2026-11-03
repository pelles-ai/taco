#!/usr/bin/env node
/**
 * Checks the conformance checker (src/lib/conformance.js) against cards with
 * known results, built from the sample card on /conformance. CI regenerates
 * that sample from the SDK first (scripts/served-card.py), so the card a real
 * A2AServer serves must pass every required check.
 *
 *   node scripts/check-conformance.mjs
 */

import fs from 'node:fs';
import {createRequire} from 'node:module';
import {checkCard} from '../src/lib/conformance.js';

const require = createRequire(import.meta.url);
const facts = await require('../plugins/taco-spec')({}).loadContent();
const spec = {
  trades: facts.trades,
  taskTypes: facts.taskTypes.map((t) => t.id),
  schemaNames: Object.keys(facts.schemas),
  extensionUri: facts.extensionUri,
};

const sample = JSON.parse(
  fs.readFileSync(new URL('../src/data/sample-agent-card.json', import.meta.url), 'utf8'),
);

/** A copy of the sample card with `change` applied to it. */
function card(change = () => {}) {
  const copy = structuredClone(sample);
  change(copy);
  return copy;
}
const declaration = (c) => c.capabilities.extensions.find((e) => e.uri === spec.extensionUri);

let failures = 0;
function expect(label, c, id, wanted) {
  const got = checkCard(c, spec).find((r) => r.id === id)?.status;
  if (got === wanted) {
    console.log(`ok    ${label}`);
  } else {
    failures += 1;
    console.error(`FAIL  ${label}: check ${id} is ${got}, expected ${wanted}`);
  }
}

const requiredFailures = checkCard(sample, spec).filter((r) => r.level === 'required' && r.status !== 'pass' && r.status !== 'skip');
if (requiredFailures.length) {
  failures += 1;
  console.error('FAIL  the sample card fails required checks:', requiredFailures.map((r) => `${r.id} ${r.status}`));
} else {
  console.log('ok    the sample card passes every required check');
}

expect('sample: params match the inline fields', sample, 'params', 'pass');
expect('sample: protocol versions listed', sample, 'protocols', 'pass');
expect('params key order does not matter', card((c) => {
  const d = declaration(c);
  d.params = Object.fromEntries(Object.entries(d.params).reverse());
}), 'params', 'pass');
expect('params with another trade', card((c) => { declaration(c).params.trade = 'electrical'; }), 'params', 'fail');
expect('params with another task type', card((c) => {
  declaration(c).params.skills['estimate-mech'].taskType = 'takeoff';
}), 'params', 'fail');
expect('params listing a skill the card lacks', card((c) => {
  declaration(c).params.skills.ghost = {taskType: 'estimate', outputSchema: 'estimate-v1'};
}), 'params', 'fail');
expect('params missing a skill', card((c) => { declaration(c).params.skills = {}; }), 'params', 'fail');
expect('declaration without params', card((c) => { delete declaration(c).params; }), 'params', 'warn');
expect('no declaration', card((c) => { c.capabilities.extensions = []; }), 'params', 'skip');
expect('no supportedInterfaces', card((c) => { delete c.supportedInterfaces; }), 'protocols', 'warn');
expect('only a v0.3 interface', card((c) => {
  c.supportedInterfaces = c.supportedInterfaces.filter((i) => i.protocolVersion === '0.3');
}), 'protocols', 'warn');
expect('v1 over gRPC only', card((c) => {
  c.supportedInterfaces = [{url: c.url, protocolBinding: 'GRPC', protocolVersion: '1.0'}];
}), 'protocols', 'warn');

if (failures) {
  console.error(`\n${failures} conformance check expectation(s) failed.`);
  process.exit(1);
}
