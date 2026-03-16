"""Embedded HTML UI for the TACO Agent Monitor."""

HTML_UI = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🌮</text></svg>">
<title>TACO Agent Monitor</title>
<style>
  :root {
    --bg: #fafafa; --bg-card: #fff; --bg-hover: #f5f5f5;
    --text: #1a1a2e; --text-muted: #6b7280; --text-dim: #9ca3af;
    --border: #e5e7eb; --border-light: #f3f4f6;
    --accent: #6366f1; --accent-light: #eef2ff;
    --in-bg: #eff6ff; --in-border: #bfdbfe; --in-text: #1d4ed8; --in-dot: #3b82f6;
    --out-bg: #ecfdf5; --out-border: #a7f3d0; --out-text: #047857; --out-dot: #10b981;
    --handler-bg: #f5f3ff; --handler-border: #ddd6fe; --handler-text: #6d28d9; --handler-dot: #8b5cf6;
    --disc-bg: #fff7ed; --disc-border: #fed7aa; --disc-text: #c2410c; --disc-dot: #f97316;
    --err-bg: #fef2f2; --err-border: #fecaca; --err-text: #dc2626; --err-dot: #ef4444;
    --green: #10b981; --green-light: #ecfdf5; --green-border: #a7f3d0;
    --red: #ef4444; --red-light: #fef2f2; --red-border: #fecaca;
    --radius: 8px; --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    --mono: 'SF Mono', 'Cascadia Code', 'Fira Code', Consolas, monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f0f17; --bg-card: #1a1a2e; --bg-hover: #22223a;
      --text: #e5e5ef; --text-muted: #9ca3b8; --text-dim: #6b7280;
      --border: #2a2a42; --border-light: #22223a;
      --accent: #818cf8; --accent-light: #1e1b4b;
      --in-bg: #172554; --in-border: #1e3a5f; --in-text: #60a5fa; --in-dot: #3b82f6;
      --out-bg: #052e16; --out-border: #14532d; --out-text: #34d399; --out-dot: #10b981;
      --handler-bg: #1e1b3a; --handler-border: #312e81; --handler-text: #a78bfa; --handler-dot: #8b5cf6;
      --disc-bg: #2a1708; --disc-border: #431407; --disc-text: #fb923c; --disc-dot: #f97316;
      --err-bg: #2a0808; --err-border: #450a0a; --err-text: #f87171; --err-dot: #ef4444;
      --green: #34d399; --green-light: #052e16; --green-border: #14532d;
      --red: #f87171; --red-light: #2a0808; --red-border: #450a0a;
    }
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: var(--font); background: var(--bg); color: var(--text); font-size: 13px; height: 100vh; display: flex; flex-direction: column; }

  /* Header */
  .header { display: flex; align-items: center; gap: 14px; padding: 14px 20px; border-bottom: 1px solid var(--border); background: var(--bg-card); flex-shrink: 0; transition: box-shadow 0.2s; z-index: 5; }
  .header.scrolled { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
  @media (prefers-color-scheme: dark) { .header.scrolled { box-shadow: 0 2px 12px rgba(0,0,0,0.3); } }
  .header-left { display: flex; align-items: center; gap: 10px; }
  .header-icon { font-size: 22px; line-height: 1; }
  .agent-name { font-size: 17px; font-weight: 700; color: var(--text); letter-spacing: -0.01em; }
  .badge { font-size: 10px; font-weight: 600; padding: 3px 8px; border-radius: 10px; background: var(--accent-light); color: var(--accent); border: 1px solid var(--accent); letter-spacing: 0.2px; white-space: nowrap; text-transform: uppercase; }
  .header-right { display: flex; align-items: center; gap: 10px; margin-left: auto; }
  .status-pill { display: flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 500; padding: 4px 10px; border-radius: 12px; transition: all 0.2s; }
  .status-pill.connected { background: var(--green-light); color: var(--green); border: 1px solid var(--green-border); }
  .status-pill.disconnected { background: var(--red-light); color: var(--red); border: 1px solid var(--red-border); }
  .status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
  .status-pill.connected .status-dot { background: var(--green); box-shadow: 0 0 6px rgba(16,185,129,0.4); }
  .status-pill.disconnected .status-dot { background: var(--red); animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
  .btn { padding: 5px 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-muted); font-size: 11px; cursor: pointer; font-family: var(--font); transition: all 0.15s; }
  .btn:hover { background: var(--bg-hover); color: var(--text); }

  /* Filters */
  .filters { display: flex; gap: 6px; padding: 8px 20px; border-bottom: 1px solid var(--border); background: var(--bg-card); flex-shrink: 0; flex-wrap: wrap; align-items: center; }
  .filters label { font-size: 11px; color: var(--text-dim); font-weight: 500; margin-right: 4px; }
  .filter-chip { padding: 3px 10px; border-radius: 12px; border: 1px solid var(--border); background: var(--bg); color: var(--text-muted); font-size: 11px; cursor: pointer; transition: all 0.15s; user-select: none; }
  .filter-chip.active { border-color: var(--accent); background: var(--accent-light); color: var(--accent); font-weight: 500; }
  .filter-chip:hover { border-color: var(--accent); }
  .chip-count { font-size: 10px; opacity: 0.7; margin-left: 2px; font-variant-numeric: tabular-nums; }
  .search-box { margin-left: 12px; position: relative; flex-shrink: 0; }
  .search-input { padding: 4px 10px 4px 26px; border-radius: 12px; border: 1px solid var(--border); background: var(--bg); color: var(--text); font-size: 11px; font-family: var(--font); width: 160px; outline: none; transition: all 0.2s; }
  .search-input:focus { border-color: var(--accent); width: 200px; }
  .search-input::placeholder { color: var(--text-dim); }
  .search-icon { position: absolute; left: 8px; top: 50%; transform: translateY(-50%); color: var(--text-dim); font-size: 11px; pointer-events: none; }
  .event-count { margin-left: auto; font-size: 11px; color: var(--text-dim); font-variant-numeric: tabular-nums; }

  /* Timeline */
  .timeline { flex: 1; overflow-y: auto; padding: 8px 20px 80px; }
  .event { display: flex; gap: 10px; padding: 8px 12px; border-radius: var(--radius); margin-bottom: 4px; transition: background 0.15s; cursor: pointer; border: 1px solid transparent; }
  .event:hover { background: var(--bg-hover); }
  .event.expanded { border-color: var(--border); }
  .event-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 4px; flex-shrink: 0; }
  .event-body { flex: 1; min-width: 0; }
  .event-header { display: flex; align-items: center; gap: 8px; }
  .event-time { font-size: 11px; color: var(--text-dim); font-variant-numeric: tabular-nums; font-family: var(--mono); flex-shrink: 0; cursor: default; }
  .event-kind { font-size: 9px; font-weight: 600; padding: 2px 6px; border-radius: 4px; flex-shrink: 0; text-transform: uppercase; letter-spacing: 0.3px; white-space: nowrap; }
  .event-method { font-size: 12px; font-weight: 600; color: var(--text); }
  .event-summary { font-size: 12px; color: var(--text-muted); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .event-duration { font-size: 11px; color: var(--text-dim); font-family: var(--mono); margin-left: auto; flex-shrink: 0; }
  .event-payload { margin-top: 8px; padding: 10px; border-radius: 6px; background: var(--bg); border: 1px solid var(--border-light); font-family: var(--mono); font-size: 11px; white-space: pre-wrap; word-break: break-all; max-height: 400px; overflow-y: auto; color: var(--text-muted); line-height: 1.5; }
  .event-error { color: var(--err-text); font-weight: 500; margin-top: 4px; font-size: 12px; }

  /* Kind-specific colors */
  .kind-in .event-dot { background: var(--in-dot); }
  .kind-in .event-kind { background: var(--in-bg); color: var(--in-text); border: 1px solid var(--in-border); }
  .kind-out .event-dot { background: var(--out-dot); }
  .kind-out .event-kind { background: var(--out-bg); color: var(--out-text); border: 1px solid var(--out-border); }
  .kind-handler .event-dot { background: var(--handler-dot); }
  .kind-handler .event-kind { background: var(--handler-bg); color: var(--handler-text); border: 1px solid var(--handler-border); }
  .kind-disc .event-dot { background: var(--disc-dot); }
  .kind-disc .event-kind { background: var(--disc-bg); color: var(--disc-text); border: 1px solid var(--disc-border); }
  .kind-err .event-dot { background: var(--err-dot); }
  .kind-err .event-kind { background: var(--err-bg); color: var(--err-text); border: 1px solid var(--err-border); }

  /* Scroll anchor */
  .scroll-btn { position: fixed; bottom: 20px; right: 20px; padding: 8px 16px; border-radius: 20px; background: var(--accent); color: #fff; border: none; font-size: 12px; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.2); display: none; z-index: 10; font-family: var(--font); }
  .scroll-btn.visible { display: block; }

  /* Empty state */
  .empty { text-align: center; padding: 60px 20px; color: var(--text-dim); }
  .empty-icon { font-size: 36px; margin-bottom: 12px; }
  .empty h2 { font-size: 16px; font-weight: 500; margin-bottom: 4px; color: var(--text-muted); }
</style>
</head>
<body>

<div class="header" id="header">
  <div class="header-left">
    <span class="header-icon">&#x1F32E;</span>
    <span class="agent-name" id="agentName">Agent</span>
    <span class="badge">Monitor</span>
  </div>
  <div class="header-right">
    <div class="status-pill disconnected" id="statusPill">
      <span class="status-dot"></span>
      <span id="statusText">Connecting...</span>
    </div>
    <button class="btn" onclick="clearEvents()">Clear</button>
  </div>
</div>

<div class="filters">
  <label>Filter:</label>
  <span class="filter-chip active" data-filter="all" onclick="toggleFilter(this)">All</span>
  <span class="filter-chip active" data-filter="incoming" onclick="toggleFilter(this)">Incoming <span class="chip-count" data-count="incoming"></span></span>
  <span class="filter-chip active" data-filter="outgoing" onclick="toggleFilter(this)">Outgoing <span class="chip-count" data-count="outgoing"></span></span>
  <span class="filter-chip active" data-filter="handler" onclick="toggleFilter(this)">Handler <span class="chip-count" data-count="handler"></span></span>
  <span class="filter-chip active" data-filter="discovery" onclick="toggleFilter(this)">Discovery <span class="chip-count" data-count="discovery"></span></span>
  <div class="search-box">
    <span class="search-icon">&#x1F50D;</span>
    <input class="search-input" id="searchInput" type="text" placeholder="Search events..." oninput="onSearch()">
  </div>
  <span class="event-count" id="eventCount">0 events</span>
</div>

<div class="timeline" id="timeline"></div>
<button class="scroll-btn" id="scrollBtn" onclick="scrollToBottom()">&#x2193; New events</button>

<script>
const timeline = document.getElementById('timeline');
const scrollBtn = document.getElementById('scrollBtn');
const eventCountEl = document.getElementById('eventCount');
const agentNameEl = document.getElementById('agentName');
const statusPill = document.getElementById('statusPill');
const statusText = document.getElementById('statusText');
const headerEl = document.getElementById('header');
const searchInput = document.getElementById('searchInput');

// Derive the base path so fetch/ws work when mounted under a prefix
const basePath = location.pathname.replace(/\/$/, '');

let events = [];
let autoScroll = true;
let expandedId = null;
let filters = { all: true, incoming: true, outgoing: true, handler: true, discovery: true };
let searchQuery = '';
let ws = null;
let reconnectDelay = 1000;

// --- Search ---
function onSearch() {
  searchQuery = searchInput.value.toLowerCase().trim();
  renderAll();
}

// --- Filters ---
function toggleFilter(chip) {
  const f = chip.dataset.filter;
  if (f === 'all') {
    const allActive = chip.classList.contains('active');
    document.querySelectorAll('.filter-chip').forEach(c => {
      c.classList.toggle('active', !allActive);
      filters[c.dataset.filter] = !allActive;
    });
  } else {
    filters[f] = !filters[f];
    chip.classList.toggle('active', filters[f]);
    const allChip = document.querySelector('[data-filter="all"]');
    const nonAll = ['incoming','outgoing','handler','discovery'];
    const allOn = nonAll.every(k => filters[k]);
    allChip.classList.toggle('active', allOn);
    filters.all = allOn;
  }
  renderAll();
}

function kindCategory(kind) {
  if (kind.startsWith('incoming')) return 'incoming';
  if (kind.startsWith('outgoing')) return 'outgoing';
  if (kind.startsWith('handler')) return 'handler';
  if (kind === 'discovery') return 'discovery';
  return 'incoming';
}

function matchesSearch(ev) {
  if (!searchQuery) return true;
  const hay = `${ev.method || ''} ${ev.summary || ''} ${ev.error || ''}`.toLowerCase();
  return hay.includes(searchQuery);
}

function isVisible(ev) {
  const catVisible = filters.all || filters[kindCategory(ev.kind)];
  return catVisible && matchesSearch(ev);
}

// --- Filter counts ---
function updateFilterCounts() {
  const counts = { incoming: 0, outgoing: 0, handler: 0, discovery: 0 };
  for (const ev of events) {
    const cat = kindCategory(ev.kind);
    if (counts[cat] !== undefined) counts[cat]++;
  }
  for (const [cat, count] of Object.entries(counts)) {
    const el = document.querySelector(`[data-count="${cat}"]`);
    if (el) el.textContent = count > 0 ? `(${count})` : '';
  }
}

// --- Rendering ---
function kindClass(kind) {
  if (kind.includes('error') || kind === 'handler_error') return 'kind-err';
  if (kind.startsWith('incoming')) return 'kind-in';
  if (kind.startsWith('outgoing')) return 'kind-out';
  if (kind.startsWith('handler')) return 'kind-handler';
  if (kind === 'discovery') return 'kind-disc';
  return 'kind-in';
}

function kindLabel(kind) {
  const map = {
    'incoming_request': 'RECEIVED',
    'incoming_response': 'REPLIED',
    'outgoing_request': 'CALLING',
    'outgoing_response': 'GOT REPLY',
    'handler_start': 'PROCESSING',
    'handler_end': 'COMPLETED',
    'handler_error': 'FAILED',
    'discovery': 'DISCOVERY',
  };
  return map[kind] || kind.toUpperCase();
}

function formatTimeAbsolute(ts) {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
      + '.' + String(d.getMilliseconds()).padStart(3, '0');
  } catch { return ts; }
}

function formatTimeRelative(ts) {
  try {
    const diff = Math.max(0, (Date.now() - new Date(ts).getTime()) / 1000);
    if (diff < 2) return 'just now';
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return formatTimeAbsolute(ts);
  } catch { return ts; }
}

function truncatePayload(obj) {
  const s = JSON.stringify(obj, null, 2);
  return s.length > 8000 ? s.slice(0, 8000) + '\n... (truncated)' : s;
}

function renderEvent(ev) {
  if (!isVisible(ev)) return '';
  const kc = kindClass(ev.kind);
  const expanded = expandedId === ev.id;
  const dur = ev.duration_ms != null ? `${Math.round(ev.duration_ms)}ms` : '';
  const arrow = ev.direction === 'in' ? '&#x2B07;' : ev.direction === 'out' ? '&#x2B06;' : '&#x2699;';

  const safeId = escapeAttr(ev.id);
  const safeTs = escapeAttr(ev.ts);
  let html = `<div class="event ${kc} ${expanded ? 'expanded' : ''}" data-id="${safeId}" onclick="toggleExpand('${safeId}')">
    <div class="event-dot"></div>
    <div class="event-body">
      <div class="event-header">
        <span class="event-time" data-ts="${safeTs}" title="${escapeAttr(formatTimeAbsolute(ev.ts))}">${formatTimeRelative(ev.ts)}</span>
        <span class="event-kind">${kindLabel(ev.kind)}</span>
        <span class="event-method">${arrow} ${ev.method || ''}</span>
        ${dur ? `<span class="event-duration">${dur}</span>` : ''}
      </div>
      <div class="event-summary">${escapeHtml(ev.summary || '')}</div>
      ${ev.error ? `<div class="event-error">${escapeHtml(ev.error)}</div>` : ''}
      ${expanded && ev.payload != null ? `<div class="event-payload">${escapeHtml(truncatePayload(ev.payload))}</div>` : ''}
    </div>
  </div>`;
  return html;
}

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function escapeAttr(s) {
  return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/</g,'&lt;');
}

function renderAll() {
  const visible = events.filter(isVisible);
  timeline.innerHTML = visible.length === 0
    ? '<div class="empty"><div class="empty-icon">&#x1F32E;</div><h2>No events yet</h2><p>Events will appear here as the agent processes requests</p></div>'
    : visible.map(renderEvent).join('');
  eventCountEl.textContent = `${events.length} events`;
  updateFilterCounts();
  if (autoScroll) scrollToBottom();
}

function toggleExpand(id) {
  expandedId = expandedId === id ? null : id;
  renderAll();
}

// --- Scroll ---
timeline.addEventListener('scroll', () => {
  const atBottom = timeline.scrollHeight - timeline.scrollTop - timeline.clientHeight < 60;
  autoScroll = atBottom;
  scrollBtn.classList.toggle('visible', !atBottom && events.length > 0);
  headerEl.classList.toggle('scrolled', timeline.scrollTop > 0);
});

function scrollToBottom() {
  timeline.scrollTop = timeline.scrollHeight;
  autoScroll = true;
  scrollBtn.classList.remove('visible');
}

// --- Relative time refresh ---
function refreshRelativeTimes() {
  if (document.hidden) return;
  document.querySelectorAll('.event-time[data-ts]').forEach(el => {
    el.textContent = formatTimeRelative(el.dataset.ts);
  });
}
setInterval(refreshRelativeTimes, 5000);

// --- Append events efficiently ---
function incrementFilterCount(ev) {
  const cat = kindCategory(ev.kind);
  const el = document.querySelector(`[data-count="${cat}"]`);
  if (!el) return;
  const cur = parseInt(el.textContent.replace(/[()]/g, ''), 10) || 0;
  el.textContent = `(${cur + 1})`;
}

function appendEvent(ev) {
  events.push(ev);
  incrementFilterCount(ev);
  if (isVisible(ev)) {
    const empty = timeline.querySelector('.empty');
    if (empty) empty.remove();
    timeline.insertAdjacentHTML('beforeend', renderEvent(ev));
  }
  eventCountEl.textContent = `${events.length} events`;
  if (autoScroll) scrollToBottom();
}

// --- Data ---
async function loadHistory() {
  try {
    const resp = await fetch(`${basePath}/api/events?limit=500`);
    const data = await resp.json();
    events = data;
    renderAll();
  } catch(e) {
    console.warn('Failed to load history:', e);
  }
}

async function loadInfo() {
  try {
    const resp = await fetch(`${basePath}/api/info`);
    const info = await resp.json();
    agentNameEl.textContent = info.agentName || 'Agent';
    document.title = `\u{1F32E} ${info.agentName || 'Agent'} \u2014 Monitor`;
  } catch(e) {
    console.warn('Failed to load info:', e);
  }
}

async function clearEvents() {
  try {
    await fetch(`${basePath}/api/clear`, { method: 'POST' });
    events = [];
    expandedId = null;
    renderAll();
  } catch(e) { console.warn('Clear failed:', e); }
}

// --- WebSocket ---
function connectWs() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}${basePath}/ws`);

  ws.onopen = () => {
    statusPill.className = 'status-pill connected';
    statusText.textContent = 'Live';
    reconnectDelay = 1000;
  };

  ws.onmessage = (e) => {
    try {
      const ev = JSON.parse(e.data);
      appendEvent(ev);
    } catch {}
  };

  ws.onclose = () => {
    statusPill.className = 'status-pill disconnected';
    statusText.textContent = 'Reconnecting...';
    setTimeout(connectWs, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 1.5, 10000);
  };

  ws.onerror = () => ws.close();
}

// --- Init ---
loadInfo();
loadHistory().then(connectWs);
</script>
</body>
</html>"""
