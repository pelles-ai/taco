import {useCallback, useEffect, useRef, useState} from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import {PRESETS, PYODIDE_VERSION, playgroundRequirements} from '@site/src/data/playground-presets';

/**
 * Runs the real taco-agent package in the browser. Python (Pyodide) lives in
 * a Web Worker so the page stays responsive and Stop can end a run that never
 * returns. The worker is kept for the whole visit, so a second run, or a run
 * after navigating away and back, starts immediately.
 */

const CDN_INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

// A module worker built from a string, so it needs no bundler support.
// Pyodide 314 and later only run in module workers.
const WORKER_SOURCE = `
let py = null;

function trimTraceback(message) {
  const lines = String(message).split('\\n');
  const start = lines.findIndex((l) => l.includes('File "<exec>"'));
  if (start < 0) return String(message).trim();
  return ['Traceback (most recent call last):', ...lines.slice(start)].join('\\n').trim();
}

async function install(requirements) {
  await py.runPythonAsync('import micropip\\nawait micropip.install(' + JSON.stringify(requirements) + ')');
}

async function boot({indexURL, requirements, fallback}) {
  postMessage({type: 'status', stage: 'download'});
  const {loadPyodide} = await import(indexURL + 'pyodide.mjs');
  py = await loadPyodide({indexURL});
  py.setStdout({batched: (text) => postMessage({type: 'out', stream: 'out', text})});
  py.setStderr({batched: (text) => postMessage({type: 'out', stream: 'err', text})});
  postMessage({type: 'status', stage: 'install'});
  await py.loadPackage('micropip', {messageCallback() {}});
  let pinned = true;
  try {
    await install(requirements);
  } catch (err) {
    // The release this site was built from is not on PyPI yet: take the latest.
    pinned = false;
    await install(fallback);
  }
  const version = py.runPython("from importlib.metadata import version\\nversion('taco-agent')");
  const python = py.runPython("import sys\\n'.'.join(map(str, sys.version_info[:3]))");
  postMessage({type: 'ready', version, python, pinned});
}

async function run({code}) {
  const ns = py.runPython("dict(__name__='__main__')");
  try {
    await py.runPythonAsync(code, {globals: ns});
    postMessage({type: 'done', ok: true});
  } catch (err) {
    const exit = err.type === 'SystemExit';
    const text = exit
      ? String(err.message).trim().split('\\n').pop().replace(/^SystemExit:\\s*/, '')
      : trimTraceback(err.message || err);
    postMessage({type: 'done', ok: false, text});
  } finally {
    ns.destroy();
  }
}

onmessage = (event) => {
  const msg = event.data;
  const job = msg.type === 'boot' ? boot(msg) : run(msg);
  job.catch((err) => postMessage({type: 'fatal', text: String((err && err.message) || err)}));
};
`;

let runtime = null;

function startRuntime(sdkVersion, indexURL) {
  const blobUrl = URL.createObjectURL(new Blob([WORKER_SOURCE], {type: 'text/javascript'}));
  const worker = new Worker(blobUrl, {type: 'module'});
  const rt = {worker, info: null, handler: null};
  rt.ready = new Promise((resolve, reject) => {
    worker.onmessage = (event) => {
      const msg = event.data;
      if (msg.type === 'ready') {
        rt.info = msg;
        URL.revokeObjectURL(blobUrl);
        resolve(rt);
      } else if (msg.type === 'fatal' && !rt.info) {
        reject(new Error(msg.text));
      }
      if (rt.handler) rt.handler(msg);
    };
    worker.onerror = (event) => {
      event.preventDefault();
      reject(new Error(event.message || 'The Python worker could not start.'));
    };
  });
  worker.postMessage({
    type: 'boot',
    indexURL,
    requirements: playgroundRequirements(sdkVersion),
    fallback: playgroundRequirements(null),
  });
  return rt;
}

function stopRuntime() {
  if (runtime) runtime.worker.terminate();
  runtime = null;
}

const STAGE_TEXT = {
  download: `Downloading Python (Pyodide ${PYODIDE_VERSION})`,
  install: 'Installing taco-agent and its dependencies from PyPI',
};

export default function Playground() {
  const {siteConfig} = useDocusaurusContext();
  const {sdkVersion} = siteConfig.customFields;
  const indexURL = siteConfig.customFields.pyodideIndexUrl || CDN_INDEX_URL;

  const [presetId, setPresetId] = useState(PRESETS[0].id);
  const [codes, setCodes] = useState(() => Object.fromEntries(PRESETS.map((p) => [p.id, p.code])));
  const [output, setOutput] = useState([]);
  const [phase, setPhase] = useState('idle'); // idle | booting | running
  const [stage, setStage] = useState(null);
  const [info, setInfo] = useState(() => (runtime && runtime.info) || null);
  const [lastRun, setLastRun] = useState(null);
  const [bootFailed, setBootFailed] = useState(false);
  const startedAt = useRef(0);
  // Tab indents in the editor; after Escape, Tab moves focus on as usual.
  const tabLeaves = useRef(false);
  const outputRef = useRef(null);

  const preset = PRESETS.find((p) => p.id === presetId);
  const code = codes[presetId];
  const edited = code !== preset.code;

  const append = useCallback((stream, text) => {
    setOutput((prev) => [...prev, {stream, text}]);
  }, []);

  const handle = useCallback(
    (msg) => {
      if (msg.type === 'status') setStage(msg.stage);
      else if (msg.type === 'out') append(msg.stream, msg.text);
      else if (msg.type === 'done') {
        if (!msg.ok) append('err', msg.text);
        setLastRun({ok: msg.ok, ms: Math.round(performance.now() - startedAt.current)});
        setPhase('idle');
      } else if (msg.type === 'fatal' && runtime && runtime.info) {
        append('err', msg.text);
        setPhase('idle');
      }
    },
    [append],
  );

  useEffect(() => {
    if (runtime) runtime.handler = handle;
    return () => {
      if (runtime && runtime.handler === handle) runtime.handler = null;
    };
  }, [handle]);

  useEffect(() => {
    if (outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight;
  }, [output]);

  const run = useCallback(async () => {
    if (phase !== 'idle') return;
    setOutput([]);
    setLastRun(null);
    setBootFailed(false);
    if (!runtime) runtime = startRuntime(sdkVersion, indexURL);
    runtime.handler = handle;
    if (!runtime.info) {
      setPhase('booting');
      try {
        await runtime.ready;
      } catch (err) {
        stopRuntime();
        append(
          'err',
          `Could not start Python: ${err.message}\nCheck your connection and run again. The playground needs cdn.jsdelivr.net and pypi.org.`,
        );
        setPhase('idle');
        setStage(null);
        setBootFailed(true);
        return;
      }
      setInfo(runtime.info);
      setStage(null);
    }
    setPhase('running');
    startedAt.current = performance.now();
    runtime.worker.postMessage({type: 'run', code});
  }, [phase, sdkVersion, indexURL, handle, append, code]);

  const stop = useCallback(() => {
    stopRuntime();
    setInfo(null);
    setStage(null);
    setPhase('idle');
    setLastRun({stopped: true});
    append('err', 'Stopped. Python starts again on the next run.');
  }, [append]);

  const onKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      run();
    } else if (e.key === 'Escape') {
      tabLeaves.current = true;
    } else if (e.key === 'Tab' && !e.shiftKey && !tabLeaves.current) {
      e.preventDefault();
      const el = e.currentTarget;
      const {selectionStart: start, selectionEnd: end} = el;
      const next = `${code.slice(0, start)}    ${code.slice(end)}`;
      setCodes((prev) => ({...prev, [presetId]: next}));
      requestAnimationFrame(() => {
        el.selectionStart = el.selectionEnd = start + 4;
      });
    }
  };

  let statusText;
  if (phase === 'booting') statusText = `${STAGE_TEXT[stage] || 'Starting Python'}…`;
  else if (phase === 'running') statusText = 'Running…';
  else if (bootFailed) statusText = 'Python did not start';
  else if (lastRun && lastRun.stopped) statusText = 'Stopped';
  else if (lastRun) statusText = lastRun.ok ? `Finished in ${lastRun.ms} ms` : `Stopped with an error after ${lastRun.ms} ms`;
  else if (info) statusText = 'Ready';
  else statusText = 'Python starts on the first run';

  return (
    <div className="pg">
      <div className="pg__tabs" role="tablist" aria-label="Examples">
        {PRESETS.map((p, i) => (
          <button
            key={p.id}
            type="button"
            role="tab"
            aria-selected={p.id === presetId}
            className={`pg__tab ${p.id === presetId ? 'pg__tab--active' : ''}`}
            onClick={() => setPresetId(p.id)}>
            <span className="pg__tab-num">{String(i + 1).padStart(2, '0')}</span>
            {p.label}
            {codes[p.id] !== p.code ? <span className="pg__tab-edited" title="Edited" aria-label="edited" /> : null}
          </button>
        ))}
      </div>

      <p className="pg__summary">{preset.summary}</p>

      <div className="pg__panes">
        <div className="pg__pane">
          <div className="pg__bar">
            <label htmlFor="pg-code" className="sx-label">
              main.py{edited ? ' · edited' : ''}
            </label>
            <span className="pg__keys" id="pg-keys">
              Ctrl or ⌘ + Enter runs · Esc, then Tab, leaves the editor
            </span>
          </div>
          <textarea
            id="pg-code"
            className="pg__code"
            value={code}
            onChange={(e) => setCodes((prev) => ({...prev, [presetId]: e.target.value}))}
            onKeyDown={onKeyDown}
            onFocus={() => {
              tabLeaves.current = false;
            }}
            aria-describedby="pg-keys"
            spellCheck={false}
            autoCapitalize="off"
            autoComplete="off"
            autoCorrect="off"
            wrap="off"
          />
        </div>

        <div className="pg__pane">
          <div className="pg__bar">
            <span className="sx-label">Output</span>
            <span className={`pg__status pg__status--${phase}`} role="status">
              {phase !== 'idle' ? <span className="pg__spinner" aria-hidden="true" /> : null}
              {statusText}
            </span>
          </div>
          <pre className="pg__out" ref={outputRef} aria-live="polite">
            {output.length ? (
              output.map((line, i) => (
                // eslint-disable-next-line react/no-array-index-key
                <span key={i} className={line.stream === 'err' ? 'pg__err' : undefined}>
                  {line.text}
                  {'\n'}
                </span>
              ))
            ) : (
              <span className="pg__placeholder">
                {phase === 'booting'
                  ? 'The first run downloads about 25 MB. Your browser caches it, so later visits start faster.'
                  : 'Press Run to execute this example.'}
              </span>
            )}
          </pre>
        </div>
      </div>

      <div className="pg__foot">
        <div className="pg__actions">
          {phase === 'idle' ? (
            <button type="button" className="btn btn--primary btn--sm" onClick={run}>
              Run
            </button>
          ) : (
            <button type="button" className="btn btn--primary btn--sm" onClick={stop}>
              Stop
            </button>
          )}
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={!edited}
            onClick={() => setCodes((prev) => ({...prev, [presetId]: preset.code}))}>
            Restore the example
          </button>
        </div>
        <p className="pg__env">
          {info ? (
            <>
              taco-agent {info.version} · Python {info.python} on Pyodide {PYODIDE_VERSION}
              {!info.pinned ? ` · ${sdkVersion} is not on PyPI yet, so this is the latest release` : ''}
            </>
          ) : (
            <>
              taco-agent {sdkVersion} · Python on Pyodide {PYODIDE_VERSION} · runs in your browser
            </>
          )}
        </p>
      </div>
    </div>
  );
}
