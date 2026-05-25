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
  // Cookbook recipe presets — each slug matches a /docs/cookbook/{slug} page.
  // Deep-linked via /sandbox?preset={slug}.
  {
    id: 'gc-estimator-supplier-chain',
    label: 'Recipe: GC → Estimator → Supplier',
    code: `# Recipe: GC → Estimator → Supplier
# /docs/cookbook/gc-estimator-supplier-chain
#
# In the real recipe each agent is its own process; here we use the
# in-browser client to call simulated peers and watch typed artifacts flow.

from taco_browser import TacoClient, extract_structured_data

estimator = TacoClient("http://estimator.example.com:8001")
supplier = TacoClient("http://pipeworks.example.com:8002")

bom = {
    "projectId": "PRJ-2026-OAKRIDGE-MEDICAL",
    "trade": "mechanical",
    "csiDivision": "23",
    "lineItems": [
        {"id": "L-001", "description": "Copper pipe, type L",
         "quantity": 120, "unit": "LF", "size": '3/4"'},
        {"id": "L-002", "description": "90 deg elbow, type L",
         "quantity": 24, "unit": "EA", "size": '3/4"'},
    ],
}

# Hop 1: estimator
est_task = estimator.send_message("estimate", bom)
estimate = extract_structured_data(est_task.artifacts[0].parts[0])
print(f"Estimate total: \${estimate['total']:,} {estimate['currency']}")

# Hop 2: supplier (the BOM goes here, not the estimate)
quote_task = supplier.send_message("material-procurement", bom)
quote = extract_structured_data(quote_task.artifacts[0].parts[0])
print(f"\\nSupplier: {quote['supplier']}")
for item in quote['items']:
    line_total = item['unitPrice'] * item['qty']
    print(f"  {item['sku']:<10} qty={item['qty']:<4} "
          f"\${item['unitPrice']:.2f}  total \${line_total:.2f}  "
          f"(lead {item['leadDays']}d)")
print(f"\\nQuote valid until: {quote['validUntil']}")
`,
  },
  {
    id: 'rfi-round-trip',
    label: 'Recipe: RFI round-trip',
    code: `# Recipe: RFI round-trip
# /docs/cookbook/rfi-round-trip
#
# An audit agent emits a typed rfi-v1; the design responder returns a
# typed reply. End-to-end in two messages.

from taco_browser import TacoClient, extract_structured_data

responder = TacoClient("http://design-responder.example.com:8003")

rfi = {
    "projectId": "PRJ-2026-OAKRIDGE-MEDICAL",
    "subject": "Pipe routing conflict at column line C/4",
    "question": "M-201 shows 4in HW supply routed through structural beam "
                "at C/4. S-201 shows beam continuous. Confirm intended routing.",
    "category": "design-conflict",
    "priority": "high",
    "references": [{"sheetId": "M-201", "area": "grid C4"}],
}

task = responder.send_message("rfi-response", rfi)
# Note: in the browser shim, the 'rfi-response' task type isn't pre-canned —
# the response is a generic 'no mock' artifact. The Python (taco-agent) path
# in the recipe is the real implementation.
print(f"Task state: {task.state}")
print(f"Subject: {rfi['subject']}")
print(f"Priority: {rfi['priority']}")
print()
print("In the real recipe, the responder's reply is a typed rfi-response-v1")
print("artifact. The /docs/cookbook/rfi-round-trip page shows the full flow.")
`,
  },
  {
    id: 'bom-to-quote-marketplace',
    label: 'Recipe: BOM-to-Quote marketplace',
    code: `# Recipe: BOM-to-Quote marketplace
# /docs/cookbook/bom-to-quote-marketplace
#
# Fan a single BOM out to multiple supplier agents in parallel, then
# pick a winner by policy. (asyncio in the real recipe; sequential here
# since the browser shim is sync.)

from taco_browser import TacoClient, extract_structured_data

suppliers = [
    ("PipeWorks Supply", TacoClient("http://pipeworks.example.com:8002")),
    ("MetroFlow Distribution", TacoClient("http://metroflow.example.com:8004")),
    ("Eastern Pipe", TacoClient("http://eastern.example.com:8005")),
]

bom = {
    "projectId": "PRJ-2026-OAKRIDGE-MEDICAL",
    "trade": "mechanical",
    "csiDivision": "23",
    "lineItems": [
        {"id": "L-001", "description": "Copper pipe, type L",
         "quantity": 120, "unit": "LF"},
    ],
}

quotes = []
for name, client in suppliers:
    task = client.send_message("material-procurement", bom)
    q = extract_structured_data(task.artifacts[0].parts[0])
    total = sum(i['unitPrice'] * i['qty'] for i in q['items'])
    lead = max(i['leadDays'] for i in q['items'])
    quotes.append((name, total, lead))

print(f"{'Supplier':<28} {'Total':>10}   {'Lead':>5}")
print("-" * 50)
for name, total, lead in quotes:
    print(f"{name:<28} \${total:>9,.2f}   {lead:>3}d")

# Policy: cheapest within 4-day lead time
MAX_LEAD = 4
eligible = [(n, t, l) for n, t, l in quotes if l <= MAX_LEAD]
if eligible:
    winner = min(eligible, key=lambda x: x[1])
    print(f"\\nSelected: {winner[0]} (\${winner[1]:,.2f}, lead {winner[2]}d)")
else:
    print(f"\\nNo quote met lead-time ceiling of {MAX_LEAD}d.")
`,
  },
  {
    id: 'change-order-impact',
    label: 'Recipe: Change order impact',
    code: `# Recipe: Change order impact
# /docs/cookbook/change-order-impact
#
# Cross-schema reasoning: read live estimate + schedule, emit a typed
# change-order-v1 with both cost and schedule deltas.

from taco_browser import TacoClient, extract_structured_data

estimator = TacoClient("http://estimator.example.com:8001")

# Pull baseline (in real recipe, also fetch schedule from scheduler agent)
project = {"projectId": "PRJ-2026-OAKRIDGE-MEDICAL"}
baseline = extract_structured_data(
    estimator.send_message("estimate", project).artifacts[0].parts[0]
)
print(f"Baseline cost: \${baseline['total']:,}")

# Proposed scope addition
new_bom = {
    "projectId": project["projectId"],
    "trade": "mechanical",
    "lineItems": [
        {"id": "L-301", "description": "VAV box, 800 cfm",
         "quantity": 6, "unit": "EA"},
    ],
}

# Get cost delta from the same estimator (in real recipe, second send_message)
delta_estimate = extract_structured_data(
    estimator.send_message("estimate", new_bom).artifacts[0].parts[0]
)
delta_cost = delta_estimate['total']

co = {
    "projectId": project["projectId"],
    "changeOrderId": "CO-007",
    "description": "Add HVAC zoning for level 19 east wing",
    "costImpact": {
        "amount": delta_cost,
        "baselineTotal": baseline['total'],
        "newTotal": baseline['total'] + delta_cost,
    },
    "scheduleImpact": {"deltaDays": 4, "affectedActivities": ["A-1910"]},
    "metadata": {"generatedBy": "change-order-analyzer-v1"},
}

print(f"\\nChange order {co['changeOrderId']}: {co['description']}")
print(f"  Cost delta:  \${co['costImpact']['amount']:,}")
print(f"  New total:   \${co['costImpact']['newTotal']:,}")
print(f"  Schedule:    +{co['scheduleImpact']['deltaDays']}d on "
      f"{len(co['scheduleImpact']['affectedActivities'])} activities")
`,
  },
];

const DEFAULT_PRESET_ID = 'define';

function readPresetFromUrl() {
  if (typeof window === 'undefined') return null;
  const params = new URLSearchParams(window.location.search);
  const preset = params.get('preset');
  if (preset && PRESETS.find((p) => p.id === preset)) return preset;
  return null;
}

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
  // Initialize from URL ?preset=... when present, else the default preset.
  const initialPresetId = readPresetFromUrl() ?? DEFAULT_PRESET_ID;
  const initialPreset = PRESETS.find((p) => p.id === initialPresetId) ?? PRESETS[0];
  const [activePreset, setActivePreset] = useState(initialPreset.id);
  const [code, setCode] = useState(initialPreset.code);
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
