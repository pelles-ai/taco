/**
 * TACO conformance checks, one function per check in SPEC-005.
 *
 * Pure functions over a parsed Agent Card plus the spec facts the site is
 * built from (recognized trades, task types, schema names, extension URI),
 * so they can run in the browser and be tested in Node. Each result is:
 *   {id, section, title, level: 'required' | 'recommended',
 *    status: 'pass' | 'fail' | 'warn' | 'skip', detail, fix?}
 */

const CSI_DIVISION = /^[0-9]{2}$/;

function result(id, section, title, level, status, detail, fix) {
  return {id, section, title, level, status, detail, fix};
}

function nonEmptyString(v) {
  return typeof v === 'string' && v.trim().length > 0;
}

function skillsOf(card) {
  return Array.isArray(card.skills) ? card.skills : [];
}

function skillLabel(skill, i) {
  return skill && nonEmptyString(skill.id) ? skill.id : `skill #${i + 1}`;
}

/** Run every card-level check in SPEC-005 §3 and §4.2-4.3. */
export function checkCard(card, spec) {
  const out = [];
  const ext = card && typeof card === 'object' ? card['x-construction'] : undefined;

  // 3.2 Required top-level fields
  const missing = ['name', 'description', 'version', 'url'].filter((f) => !nonEmptyString(card[f]));
  out.push(
    result(
      'fields',
      '3.2',
      'Required top-level fields',
      'required',
      missing.length ? 'fail' : 'pass',
      missing.length
        ? `Missing or empty: ${missing.join(', ')}.`
        : 'name, description, version and url are all present.',
      missing.length ? 'Pass name, description and url to ConstructionAgentCard; to_a2a() defaults version to 1.0.0.' : undefined,
    ),
  );

  // 3.3 At least one skill
  const skills = skillsOf(card);
  out.push(
    result(
      'skills',
      '3.3',
      'At least one skill',
      'required',
      skills.length ? 'pass' : 'fail',
      skills.length ? `${skills.length} skill${skills.length === 1 ? '' : 's'} declared.` : 'skills[] is missing or empty.',
      skills.length ? undefined : 'Add a ConstructionSkill with a task type and an output schema.',
    ),
  );

  // 3.4 Construction extension declared
  const extensions = (card.capabilities && card.capabilities.extensions) || [];
  const hasUri = Array.isArray(extensions) && extensions.some((e) => e && e.uri === spec.extensionUri);
  if (!ext || typeof ext !== 'object') {
    out.push(
      result(
        'extension',
        '3.4',
        'Construction extension declared',
        'required',
        'fail',
        'The card has no inline x-construction object.',
        'Build the card with ConstructionAgentCard(...).to_a2a(), which adds it.',
      ),
    );
  } else {
    out.push(
      result(
        'extension',
        '3.4',
        'Construction extension declared',
        'required',
        hasUri ? 'pass' : 'warn',
        hasUri
          ? 'Inline x-construction is present and capabilities.extensions[] lists the canonical URI.'
          : `Inline x-construction is present, but capabilities.extensions[] does not list ${spec.extensionUri}.`,
        hasUri ? undefined : 'Call taco.apply_construction_extension_declaration(card), or build the card with to_a2a().',
      ),
    );
  }

  // 3.5 Recognized trade
  if (ext && typeof ext === 'object') {
    const ok = spec.trades.includes(ext.trade);
    out.push(
      result(
        'trade',
        '3.5',
        'Recognized trade',
        'required',
        ok ? 'pass' : 'fail',
        ok ? `trade is "${ext.trade}".` : `trade is ${JSON.stringify(ext.trade)}, which is not a recognized trade.`,
        ok ? undefined : `Use one of: ${spec.trades.join(', ')}.`,
      ),
    );

    // 3.6 Valid CSI divisions
    const divisions = ext.csiDivisions;
    if (!Array.isArray(divisions)) {
      out.push(
        result('csi', '3.6', 'Valid CSI divisions', 'required', 'fail', 'csiDivisions is missing or not a list.',
          'Declare csiDivisions as a list of two-digit strings, for example ["22", "23"].'),
      );
    } else {
      const bad = divisions.filter((d) => typeof d !== 'string' || !CSI_DIVISION.test(d));
      out.push(
        result(
          'csi',
          '3.6',
          'Valid CSI divisions',
          'required',
          bad.length ? 'fail' : 'pass',
          bad.length
            ? `Not two-digit strings: ${bad.map((d) => JSON.stringify(d)).join(', ')}.`
            : divisions.length
              ? `${divisions.join(', ')}.`
              : 'The list is empty, which is allowed.',
          bad.length ? 'Use two-digit MasterFormat division numbers as strings, for example "23".' : undefined,
        ),
      );
    }
  } else {
    out.push(result('trade', '3.5', 'Recognized trade', 'required', 'skip', 'No x-construction object to check.'));
    out.push(result('csi', '3.6', 'Valid CSI divisions', 'required', 'skip', 'No x-construction object to check.'));
  }

  // 3.7 Recognized task types, and the per-skill x-construction they live in
  const known = new Set(spec.taskTypes);
  const noExt = [];
  const unknown = [];
  skills.forEach((s, i) => {
    const sx = s && s['x-construction'];
    if (!sx || !nonEmptyString(sx.taskType)) noExt.push(skillLabel(s, i));
    else if (!known.has(sx.taskType)) unknown.push(`${skillLabel(s, i)} (${sx.taskType})`);
  });
  if (!skills.length) {
    out.push(result('task-types', '3.7', 'Recognized task types', 'required', 'skip', 'No skills to check.'));
  } else if (noExt.length) {
    out.push(
      result('task-types', '3.7', 'Recognized task types', 'required', 'fail',
        `No x-construction.taskType on: ${noExt.join(', ')}.`,
        'Declare each skill with ConstructionSkill(task_type=...), which puts taskType inside the skill\'s x-construction.'),
    );
  } else {
    out.push(
      result('task-types', '3.7', 'Recognized task types', 'required', unknown.length ? 'warn' : 'pass',
        unknown.length ? `Not a recognized task type: ${unknown.join(', ')}.` : 'Every skill uses a recognized task type.',
        unknown.length ? 'Use a task type from the spec, or propose a new one through a GitHub issue.' : undefined),
    );
  }

  // 3.8 Output schema declared; schema names recognized or URLs
  const schemaNames = new Set(spec.schemaNames);
  const noOutput = [];
  const oddNames = [];
  skills.forEach((s, i) => {
    const sx = (s && s['x-construction']) || {};
    if (!nonEmptyString(sx.outputSchema)) noOutput.push(skillLabel(s, i));
    for (const key of ['inputSchema', 'outputSchema']) {
      const v = sx[key];
      if (nonEmptyString(v) && !schemaNames.has(v) && !/^https:\/\//.test(v)) {
        oddNames.push(`${skillLabel(s, i)} ${key} "${v}"`);
      }
    }
  });
  if (!skills.length) {
    out.push(result('schemas', '3.8', 'Schemas declared and recognized', 'required', 'skip', 'No skills to check.'));
  } else if (noOutput.length) {
    out.push(
      result('schemas', '3.8', 'Schemas declared and recognized', 'required', 'fail',
        `No x-construction.outputSchema on: ${noOutput.join(', ')}.`,
        'Every skill must say what it returns: set output_schema on the ConstructionSkill.'),
    );
  } else {
    out.push(
      result('schemas', '3.8', 'Schemas declared and recognized', 'required', oddNames.length ? 'warn' : 'pass',
        oddNames.length
          ? `Neither a TACO schema name nor an https URL: ${oddNames.join('; ')}.`
          : 'Every schema reference is a TACO schema name or an https URL.',
        oddNames.length ? `Use one of ${spec.schemaNames.join(', ')}, or a full https URL to your own schema.` : undefined),
    );
  }

  // 3.9 Security declaration consistency
  if (!Array.isArray(card.security) || !card.security.length) {
    out.push(result('security', '3.9', 'Security declarations consistent', 'required', 'skip',
      'No security[] requirements declared, so there is nothing to cross-check.'));
  } else {
    const schemes = card.securitySchemes || {};
    const dangling = [...new Set(card.security.flatMap((req) => Object.keys(req || {})))].filter(
      (name) => !(name in schemes),
    );
    out.push(
      result('security', '3.9', 'Security declarations consistent', 'required', dangling.length ? 'fail' : 'pass',
        dangling.length ? `security[] names schemes missing from securitySchemes: ${dangling.join(', ')}.` : 'Every scheme named in security[] is defined in securitySchemes.',
        dangling.length ? 'Define each scheme under securitySchemes, or remove it from security[].' : undefined),
    );
  }

  // 4.2 / 4.3 Streaming and push notifications (recommended; declared or not)
  const caps = card.capabilities || {};
  out.push(
    result('streaming', '4.2', 'Streaming declared', 'recommended', caps.streaming ? 'pass' : 'warn',
      caps.streaming ? 'capabilities.streaming is true.' : 'capabilities.streaming is not true.',
      caps.streaming ? undefined : 'Recommended when a skill usually takes more than 10 seconds: register a streaming handler and set card.capabilities.streaming = True.'),
  );
  out.push(
    result('push', '4.3', 'Push notifications declared', 'recommended', caps.pushNotifications ? 'pass' : 'warn',
      caps.pushNotifications ? 'capabilities.pushNotifications is true.' : 'capabilities.pushNotifications is not true.',
      caps.pushNotifications ? undefined : 'Recommended for long-running tasks: set card.capabilities.push_notifications = True; A2AServer then accepts push subscribers.'),
  );

  return out;
}

/** Normalise a user-entered agent URL to its origin-relative base. */
export function baseUrlOf(input) {
  const u = new URL(input.trim());
  u.hash = '';
  u.search = '';
  return u.toString().replace(/\/+$/, '');
}

/**
 * 3.1 Agent card reachable: fetch /.well-known/agent-card.json, falling back
 * to /.well-known/agent.json on 404. Returns {card, result}.
 */
export async function fetchCard(base, token, fetchImpl = fetch) {
  const headers = {Accept: 'application/json', 'A2A-Version': '0.3'};
  if (token) headers.Authorization = `Bearer ${token}`;
  const tried = [];
  for (const path of ['/.well-known/agent-card.json', '/.well-known/agent.json']) {
    let res;
    try {
      res = await fetchImpl(base + path, {headers, mode: 'cors'});
    } catch (err) {
      return {
        card: null,
        result: result('reachable', '3.1', 'Agent card reachable', 'required', 'fail',
          `The browser could not fetch ${base + path}. The agent is unreachable, or its CORS policy does not allow this site.`,
          `Allow this origin in the agent's cors_origins, or check it from a terminal: curl -fsSL ${base}/.well-known/agent-card.json. You can also paste the card JSON here instead.`),
      };
    }
    tried.push(`${path} → ${res.status}`);
    if (res.status === 404) continue;
    if (!res.ok) {
      return {
        card: null,
        result: result('reachable', '3.1', 'Agent card reachable', 'required', 'fail',
          `${base + path} returned HTTP ${res.status}.`,
          res.status === 401 || res.status === 403 ? 'The card should be public. If it is not, add a bearer token above.' : 'Serve the card with HTTP 200.'),
      };
    }
    try {
      const card = await res.json();
      return {
        card,
        result: result('reachable', '3.1', 'Agent card reachable', 'required', 'pass',
          `Loaded ${path}${path.endsWith('agent.json') ? ' (legacy path; serve agent-card.json too)' : ''}.`),
      };
    } catch {
      return {
        card: null,
        result: result('reachable', '3.1', 'Agent card reachable', 'required', 'fail', `${base + path} did not return valid JSON.`),
      };
    }
  }
  return {
    card: null,
    result: result('reachable', '3.1', 'Agent card reachable', 'required', 'fail',
      `Neither well-known path exists (${tried.join(', ')}).`, 'Serve the card at /.well-known/agent-card.json.'),
  };
}

/** 4.1 Health endpoint (recommended). */
export async function checkHealth(base, token, fetchImpl = fetch) {
  const headers = token ? {Authorization: `Bearer ${token}`} : {};
  try {
    const res = await fetchImpl(`${base}/health`, {headers, mode: 'cors'});
    return result('health', '4.1', 'Health endpoint', 'recommended', res.ok ? 'pass' : 'warn',
      res.ok ? 'GET /health returned 200.' : `GET /health returned HTTP ${res.status}.`,
      res.ok ? undefined : 'A2AServer serves /health automatically; check a proxy is not blocking it.');
  } catch {
    return result('health', '4.1', 'Health endpoint', 'recommended', 'skip',
      'Could not reach /health from the browser, which is usually CORS.');
  }
}
