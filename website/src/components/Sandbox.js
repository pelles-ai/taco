import {useCallback, useEffect, useRef, useState} from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';

/**
 * In-browser TACO sandbox powered by Pyodide. The user writes real Python
 * against a `taco_browser` shim that mirrors the SDK's public surface but
 * returns canned responses instead of making network calls.
 *
 * Pyodide is ~10MB; we lazy-load it from the official CDN only when the user
 * clicks Run. The first run takes a few seconds; subsequent runs are instant.
 */

const PYODIDE_VERSION = '0.28.0';
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full`;

const PRESETS = [
  {
    id: 'define',
    label: 'Define an agent',
    code: `from taco_browser import ConstructionAgentCard, ConstructionSkill

card = ConstructionAgentCard(
    name="My Mechanical Estimator",
    trade="mechanical",
    csi_divisions=["22", "23"],
    skills=[
        ConstructionSkill(
            id="generate-estimate",
            task_type="estimate",
            input_schema="bom-v1",
            output_schema="estimate-v1",
        ),
    ],
)

print(card.to_json())
`,
  },
  {
    id: 'send',
    label: 'Send a task',
    code: `from taco_browser import TacoClient, extract_structured_data

client = TacoClient("http://estimator.example.com:8080")

bom = {
    "projectId": "PRJ-0042",
    "lineItems": [
        {"description": "Copper pipe 1/2in", "quantity": 120, "unit": "LF"},
    ],
}

task = client.send_message("estimate", bom)
print(f"Task state: {task.state}")
print()

result = extract_structured_data(task.artifacts[0].parts[0])
print(f"Total: \${result['total']:,} {result['currency']}")
print(f"Schema: {result['schema']}")
`,
  },
  {
    id: 'pipeline',
    label: 'Two-step pipeline',
    code: `from taco_browser import TacoClient, extract_structured_data

takeoff_agent = TacoClient("http://takeoff.example.com:8080")
estimator = TacoClient("http://estimator.example.com:8080")

# Step 1: takeoff
bom_task = takeoff_agent.send_message("takeoff", {"projectId": "PRJ-001"})
bom = extract_structured_data(bom_task.artifacts[0].parts[0])
print(f"Generated BOM with {len(bom['lineItems'])} items")

# Step 2: feed the BOM into the estimator
est_task = estimator.send_message("estimate", bom)
est = extract_structured_data(est_task.artifacts[0].parts[0])

print(f"\\nEstimated cost: \${est['total']:,} {est['currency']}")
for item in est['lineItems']:
    print(f"  {item['description']:<32} \${item['subtotal']:>8,}")
`,
  },
];

function loadPyodideScript() {
  return new Promise((resolve, reject) => {
    if (window.loadPyodide) {
      resolve(window.loadPyodide);
      return;
    }
    const script = document.createElement('script');
    script.src = `${PYODIDE_CDN}/pyodide.js`;
    script.onload = () => resolve(window.loadPyodide);
    script.onerror = () =>
      reject(new Error('Failed to load Pyodide from CDN. Check your network.'));
    document.head.appendChild(script);
  });
}

function SandboxInner() {
  const [activePreset, setActivePreset] = useState(PRESETS[0].id);
  const [code, setCode] = useState(PRESETS[0].code);
  const [output, setOutput] = useState('');
  const [status, setStatus] = useState('idle'); // idle | loading | running | error
  const [statusMsg, setStatusMsg] = useState('');
  const pyodideRef = useRef(null);

  const switchPreset = useCallback((id) => {
    const p = PRESETS.find((x) => x.id === id);
    if (!p) return;
    setActivePreset(id);
    setCode(p.code);
    setOutput('');
  }, []);

  const ensurePyodide = useCallback(async () => {
    if (pyodideRef.current) return pyodideRef.current;
    setStatus('loading');
    setStatusMsg('Loading Pyodide…');
    const loadPyodide = await loadPyodideScript();
    const pyodide = await loadPyodide({indexURL: `${PYODIDE_CDN}/`});

    setStatusMsg('Loading taco_browser…');
    const shimResp = await fetch('/sandbox/taco_browser.py');
    if (!shimResp.ok) {
      throw new Error(`Could not fetch taco_browser.py (HTTP ${shimResp.status})`);
    }
    const shimSource = await shimResp.text();
    pyodide.FS.writeFile('/home/pyodide/taco_browser.py', shimSource);

    pyodideRef.current = pyodide;
    setStatus('idle');
    setStatusMsg('');
    return pyodide;
  }, []);

  const run = useCallback(async () => {
    try {
      const pyodide = await ensurePyodide();
      setStatus('running');
      setStatusMsg('Running…');
      setOutput('');

      const buf = [];
      pyodide.setStdout({batched: (s) => buf.push(s)});
      pyodide.setStderr({batched: (s) => buf.push(s)});

      try {
        await pyodide.runPythonAsync(code);
        setOutput(buf.join('\n').trim() || '(no output)');
        setStatus('idle');
        setStatusMsg('');
      } catch (err) {
        setOutput(buf.join('\n').trim());
        setStatus('error');
        setStatusMsg(String(err).split('\n').slice(-3).join('\n'));
      }
    } catch (err) {
      setStatus('error');
      setStatusMsg(String(err.message || err));
    }
  }, [code, ensurePyodide]);

  // Preload on mount to make first-run snappier (but don't block render)
  useEffect(() => {
    const idleCallback =
      typeof window !== 'undefined' && window.requestIdleCallback;
    if (idleCallback) {
      const id = window.requestIdleCallback(() => {
        ensurePyodide().catch(() => {
          /* surface the error only when the user actually clicks Run */
        });
      });
      return () => window.cancelIdleCallback?.(id);
    }
  }, [ensurePyodide]);

  const isBusy = status === 'loading' || status === 'running';

  return (
    <div className="sandbox">
      <div className="sandbox__head">
        <div className="sandbox__presets">
          {PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => switchPreset(p.id)}
              className={`sandbox__preset ${
                activePreset === p.id ? 'sandbox__preset--active' : ''
              }`}>
              {p.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={run}
          disabled={isBusy}
          className="sandbox__run">
          {status === 'loading'
            ? 'Loading…'
            : status === 'running'
              ? 'Running…'
              : 'Run'}
        </button>
      </div>

      <div className="sandbox__panes">
        <div className="sandbox__pane sandbox__pane--editor">
          <div className="sandbox__pane-label">main.py</div>
          <textarea
            className="sandbox__editor"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            spellCheck={false}
            aria-label="Python code editor"
          />
        </div>
        <div className="sandbox__pane sandbox__pane--output">
          <div className="sandbox__pane-label">output</div>
          <pre className="sandbox__output">
            {output || (
              <span className="sandbox__output-hint">
                {status === 'idle' && !statusMsg
                  ? 'Click Run to execute. First run loads Pyodide (~10MB), takes a few seconds.'
                  : statusMsg}
              </span>
            )}
            {status === 'error' && statusMsg ? (
              <span className="sandbox__output-error">{'\n\n' + statusMsg}</span>
            ) : null}
          </pre>
        </div>
      </div>

      <div className="sandbox__footnote">
        Runs <code>taco_browser</code> — a client-side shim of the TACO SDK.
        Real agent traffic requires <code>pip install taco-agent</code>.
      </div>
    </div>
  );
}

export default function Sandbox() {
  return (
    <BrowserOnly fallback={<div className="sandbox sandbox--loading">Loading sandbox…</div>}>
      {() => <SandboxInner />}
    </BrowserOnly>
  );
}
