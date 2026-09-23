#!/usr/bin/env node
/**
 * Runs every playground preset in Pyodide, the way the /playground page does,
 * and exits non-zero if one raises. CI runs it against the SDK in the repo so a
 * change to taco-agent that breaks an example fails the pull request, not the
 * page after the next release.
 *
 *   node scripts/check-playground.mjs path/to/taco_agent-*.whl   # a local build
 *   node scripts/check-playground.mjs 0.3.17                     # a release on PyPI
 *
 * Needs the pyodide npm package at the version the page uses:
 *   npm install --no-save pyodide@<PYODIDE_VERSION>
 */

import fs from 'node:fs';
import path from 'node:path';
import {loadPyodide, version as pyodideVersion} from 'pyodide';
import {PRESETS, PYODIDE_VERSION, playgroundRequirements} from '../src/data/playground-presets.js';

if (pyodideVersion !== PYODIDE_VERSION) {
  console.error(`pyodide ${pyodideVersion} is installed but the playground uses ${PYODIDE_VERSION}.`);
  process.exit(2);
}

const target = process.argv[2];
if (!target) {
  console.error('Pass a taco-agent wheel or a released version.');
  process.exit(2);
}

const py = await loadPyodide();
let out = '';
py.setStdout({batched: (s) => (out += `${s}\n`)});
py.setStderr({batched: (s) => (out += `${s}\n`)});
await py.loadPackage('micropip', {messageCallback() {}});

let requirements;
if (target.endsWith('.whl')) {
  const name = path.basename(target);
  py.FS.writeFile(`/tmp/${name}`, fs.readFileSync(target));
  requirements = [
    ...playgroundRequirements(null).filter((r) => !r.startsWith('taco-agent')),
    `taco-agent[server,client] @ emfs:/tmp/${name}`,
  ];
} else {
  requirements = playgroundRequirements(target);
}
await py.runPythonAsync(`import micropip\nawait micropip.install(${JSON.stringify(requirements)})`);
const installed = py.runPython("from importlib.metadata import version\nversion('taco-agent')");
console.log(`taco-agent ${installed} on Pyodide ${pyodideVersion}`);

let failed = 0;
for (const preset of PRESETS) {
  out = '';
  const ns = py.runPython("dict(__name__='__main__')");
  const started = Date.now();
  try {
    await py.runPythonAsync(preset.code, {globals: ns});
    console.log(`\nok    ${preset.id} (${Date.now() - started} ms)`);
  } catch (err) {
    failed += 1;
    console.log(`\nFAIL  ${preset.id}`);
    console.log(String(err.message || err).trim());
  } finally {
    ns.destroy();
  }
  console.log(out.trimEnd().replace(/^/gm, '      '));
}

if (failed) {
  console.error(`\n${failed} of ${PRESETS.length} playground examples failed.`);
  process.exit(1);
}
console.log(`\nAll ${PRESETS.length} playground examples ran.`);
