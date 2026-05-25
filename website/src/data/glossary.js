/**
 * Bidirectional glossary entries.
 *
 * audience:
 *   'construction' — explains a construction term to a developer reader
 *   'protocol'     — explains a TACO/A2A/MCP term to a construction reader
 *   'both'         — common ground (e.g. "Project")
 *
 * Keep entries short. Link to the deep doc for each.
 */

export const TERMS = [
  // ---- Construction ----
  {
    id: 'rfi',
    term: 'RFI',
    full: 'Request for Information',
    audience: 'construction',
    short:
      'A formal question from a builder to a designer when something on the drawings is unclear, conflicting, or missing.',
    long:
      'In construction, every project generates dozens of RFIs — usually a PDF or portal entry asking the architect/engineer to clarify how a detail should be built. In TACO, an RFI is a typed artifact (`rfi-v1`) that auditor agents emit and responder agents consume.',
    aliases: ['Request for Information'],
    seeAlso: [
      {label: 'rfi-v1 schema', href: '/docs/schemas/rfi-v1'},
      {label: 'RFI Round-trip recipe', href: '/docs/cookbook/rfi-round-trip'},
    ],
  },
  {
    id: 'bom',
    term: 'BOM',
    full: 'Bill of Materials',
    audience: 'construction',
    short:
      'An itemized list of every material and quantity needed to build something — the typed handoff between takeoff and estimating.',
    long:
      'Line items (description, quantity, unit, size, material), grouped by trade and CSI division. In TACO, a BOM is the `bom-v1` schema — the input that estimators and supplier agents both consume.',
    aliases: ['Bill of Materials'],
    seeAlso: [
      {label: 'bom-v1 schema', href: '/docs/schemas/bom-v1'},
      {label: 'GC → Estimator → Supplier', href: '/docs/cookbook/gc-estimator-supplier-chain'},
    ],
  },
  {
    id: 'takeoff',
    term: 'Takeoff',
    full: 'Quantity takeoff',
    audience: 'construction',
    short:
      'The act of measuring quantities off a set of drawings to produce a BOM.',
    long:
      'Historically done by hand or in spreadsheets, increasingly automated by AI agents that read PDF or DWG drawings. In TACO, takeoff is the canonical `takeoff` task type that produces a `bom-v1`.',
    aliases: ['Quantity takeoff'],
    seeAlso: [
      {label: 'Task types', href: '/docs/task-types'},
      {label: 'bom-v1 schema', href: '/docs/schemas/bom-v1'},
    ],
  },
  {
    id: 'submittal',
    term: 'Submittal',
    full: 'Material/method submittal',
    audience: 'construction',
    short:
      'A document a subcontractor sends to the GC/architect proposing a specific product or method, for review before installation.',
    long:
      'Used to confirm a product meets the spec before it arrives on site. TACO models this as the `submittal-review` task type; schema for the response is planned (`submittal-review-v1`).',
    seeAlso: [{label: 'Task types', href: '/docs/task-types'}],
  },
  {
    id: 'change-order',
    term: 'Change Order',
    full: 'Change Order',
    audience: 'construction',
    short:
      'A formal modification to the project — usually scope, cost, or schedule — agreed between owner and GC after the contract is signed.',
    long:
      'TACO models this as `change-order-v1` and the `change-order-analysis` task type. A change-order agent typically reads the current `estimate-v1` and `schedule-v1` and emits a typed delta.',
    seeAlso: [
      {label: 'change-order-v1 schema', href: '/docs/schemas/change-order-v1'},
      {label: 'Change Order Impact recipe', href: '/docs/cookbook/change-order-impact'},
    ],
  },
  {
    id: 'csi-masterformat',
    term: 'CSI MasterFormat',
    full: 'CSI MasterFormat',
    audience: 'construction',
    short:
      'The standard numbering system that organizes construction specs into divisions (01–49). Division 23 is HVAC; division 26 is electrical.',
    long:
      'TACO Agent Cards use CSI division numbers (`csiDivisions: ["22", "23"]`) to advertise what scope a trade agent covers, so a registry query can filter by exact spec area.',
    aliases: ['MasterFormat'],
    seeAlso: [
      {label: 'Agent Card Extensions', href: '/docs/agent-card-extensions'},
      {label: 'Standards alignment', href: '/docs/standards'},
    ],
  },
  {
    id: 'omniclass',
    term: 'OmniClass',
    full: 'OmniClass Construction Classification System',
    audience: 'construction',
    short:
      'A multi-axis classification system for the built environment — covering products, processes, properties, and more.',
    long:
      'Where CSI MasterFormat covers specs, OmniClass covers everything. TACO uses MasterFormat for its primary trade scoping today; OmniClass references are planned for object-level identifiers.',
    seeAlso: [{label: 'Standards alignment', href: '/docs/standards'}],
  },
  {
    id: 'ifc',
    term: 'IFC',
    full: 'Industry Foundation Classes',
    audience: 'construction',
    short:
      'The buildingSMART open BIM data model — how design tools exchange 3D building information without vendor lock-in.',
    long:
      'TACO is agent-protocol, not file-format — it does not replace IFC. A clash-detection agent that reads IFC files is a perfectly valid TACO agent; the IFC stays the input.',
    seeAlso: [{label: 'Standards alignment', href: '/docs/standards'}],
  },
  {
    id: 'cobie',
    term: 'COBie',
    full: 'Construction-Operations Building Information Exchange',
    audience: 'construction',
    short:
      'A spreadsheet-based standard for handing project data from construction to facilities operations.',
    long:
      'TACO and COBie operate at different layers — COBie is the operational handoff format; TACO is the protocol agents speak during construction. They can co-exist; an end-of-project agent can emit a COBie spreadsheet.',
    seeAlso: [{label: 'Standards alignment', href: '/docs/standards'}],
  },
  {
    id: 'iso-19650',
    term: 'ISO 19650',
    full: 'ISO 19650 (BIM information management)',
    audience: 'construction',
    short:
      'International standard for organizing information about buildings and civil works using BIM throughout the project lifecycle.',
    long:
      'TACO is agent-to-agent communication, not document control. Projects subject to ISO 19650 can still use TACO agents — the agents just need to produce ISO 19650-conformant outputs when required.',
    seeAlso: [{label: 'Standards alignment', href: '/docs/standards'}],
  },
  {
    id: 'gc',
    term: 'GC',
    full: 'General Contractor',
    audience: 'construction',
    short:
      'The contractor responsible for delivering the project — coordinates all trade subs, manages schedule and budget, interfaces with the owner.',
    long: 'TACO has a dedicated landing page for this audience.',
    aliases: ['General Contractor'],
    seeAlso: [{label: 'For General Contractors', href: '/for/general-contractor'}],
  },
  {
    id: 'sub',
    term: 'Sub',
    full: 'Subcontractor',
    audience: 'construction',
    short:
      'A specialty trade contractor (mechanical, electrical, drywall, etc.) hired by the GC to do a specific scope.',
    aliases: ['Subcontractor'],
    seeAlso: [{label: 'For Subcontractors', href: '/for/subcontractor'}],
  },
  {
    id: 'trade',
    term: 'Trade',
    full: 'Construction trade',
    audience: 'construction',
    short:
      'A construction discipline — mechanical, electrical, plumbing, structural, etc. A TACO agent declares its trade so registries can filter discovery.',
    seeAlso: [
      {label: 'Agent Card Extensions', href: '/docs/agent-card-extensions'},
      {label: 'Trade enum', href: '/docs/sdk-reference/enums'},
    ],
  },
  {
    id: 'clash-detection',
    term: 'Clash detection',
    full: 'Clash detection',
    audience: 'construction',
    short:
      'Finding spatial conflicts between trades — a duct that runs through a beam, a pipe that intersects an electrical conduit.',
    long:
      'Typically done in BIM coordination tools (Navisworks, BIM 360). TACO models this as `clash-detection` task type; schema (`clash-report-v1`) is planned.',
    seeAlso: [{label: 'Task types', href: '/docs/task-types'}],
  },
  {
    id: 'punch-list',
    term: 'Punch list',
    full: 'Punch list',
    audience: 'construction',
    short:
      'The list of remaining items to fix or finish before a project is considered complete.',
    long: 'TACO models this as `punch-list` task type; schema (`punch-list-v1`) is planned.',
    seeAlso: [{label: 'Task types', href: '/docs/task-types'}],
  },
  {
    id: 'bim',
    term: 'BIM',
    full: 'Building Information Modeling',
    audience: 'construction',
    short:
      'Coordinated 3D digital model of a building, carrying geometry plus metadata about every component.',
    long:
      'BIM tools (Revit, Navisworks, IFC, ArchiCAD) are common TACO agent dependencies — a clash-detection or takeoff agent typically reads BIM internally and emits typed TACO artifacts externally.',
    aliases: ['Building Information Modeling'],
  },
  {
    id: 'value-engineering',
    term: 'Value engineering',
    full: 'Value engineering',
    audience: 'construction',
    short:
      'Systematically looking for cost reductions in the design — alternate materials, simplified details, scope adjustments.',
    long: 'TACO models this as `value-engineering` task type; agents read a `bom-v1` + `estimate-v1` and return suggestions.',
    seeAlso: [{label: 'Task types', href: '/docs/task-types'}],
  },
  {
    id: 'bid-leveling',
    term: 'Bid leveling',
    full: 'Bid leveling',
    audience: 'construction',
    short:
      'Normalizing bids from multiple subs into apples-to-apples comparisons — accounting for different scope assumptions, alternates, and exclusions.',
    long: 'TACO models this as `bid-leveling`; the planned `bid-comparison-v1` schema is the typed output.',
    seeAlso: [{label: 'Task types', href: '/docs/task-types'}],
  },

  // ---- Protocol ----
  {
    id: 'agent',
    term: 'Agent',
    full: 'Agent (TACO/A2A)',
    audience: 'protocol',
    short:
      'A software process that exposes its capabilities via the A2A protocol and can be discovered and called by other agents.',
    long:
      'An agent can be fully AI-driven, a thin wrapper around an existing platform (sidecar), or a hard-coded service. TACO does not care what is inside — only that the agent advertises typed capabilities and produces typed outputs.',
    seeAlso: [
      {label: 'Core Concepts', href: '/docs/core-concepts'},
      {label: 'Build a custom agent', href: '/docs/getting-started/build-agent'},
    ],
  },
  {
    id: 'agent-card',
    term: 'Agent Card',
    full: 'Agent Card',
    audience: 'protocol',
    short:
      'A JSON document an agent serves at `/.well-known/agent-card.json` that describes who it is, what trade and skills it has, and how to reach it.',
    long:
      'The unit of discovery. A registry of TACO agents is just a list of Agent Cards. The `x-construction` extension is what makes a TACO Agent Card different from a plain A2A one.',
    seeAlso: [
      {label: 'Agent Card Extensions', href: '/docs/agent-card-extensions'},
      {label: 'ConstructionAgentCard', href: '/docs/sdk-reference/agent-cards'},
    ],
  },
  {
    id: 'a2a',
    term: 'A2A',
    full: 'Agent-to-Agent Protocol',
    audience: 'protocol',
    short:
      'The Linux Foundation protocol that defines how AI agents talk to each other — Agent Cards, JSON-RPC messages, task lifecycle, streaming, authentication.',
    long:
      'A2A is the transport. It is domain-agnostic — it does not know what construction is. TACO is the construction vocabulary that sits on top of A2A.',
    aliases: ['Agent-to-Agent'],
    seeAlso: [
      {label: 'A2A, MCP, and TACO', href: '/docs/protocol-stack'},
      {label: 'A2A Protocol (external)', href: 'https://a2a-protocol.org'},
    ],
  },
  {
    id: 'mcp',
    term: 'MCP',
    full: 'Model Context Protocol',
    audience: 'protocol',
    short:
      'Anthropic\'s open protocol that lets an LLM-driven agent reach external tools and data sources (databases, APIs, file systems).',
    long:
      'MCP is vertical (agent → tools); A2A is horizontal (agent → agent). A TACO agent typically uses MCP internally to talk to its data sources and A2A externally to talk to other agents.',
    aliases: ['Model Context Protocol'],
    seeAlso: [
      {label: 'A2A, MCP, and TACO', href: '/docs/protocol-stack'},
      {label: 'Model Context Protocol (external)', href: 'https://modelcontextprotocol.io'},
    ],
  },
  {
    id: 'taco',
    term: 'TACO',
    full: 'The A2A Construction Open-standard',
    audience: 'protocol',
    short:
      'A construction-specific ontology built on the A2A protocol — task types, data schemas, agent discovery, and security scopes.',
    seeAlso: [
      {label: 'Why TACO', href: '/docs/why-taco'},
      {label: 'Introduction', href: '/docs/intro'},
    ],
  },
  {
    id: 'task',
    term: 'Task',
    full: 'Task (A2A)',
    audience: 'protocol',
    short:
      'A unit of work in A2A. Has a lifecycle (`submitted` → `working` → `completed`/`failed`/`canceled`), a list of inbound messages, and a list of outbound artifacts.',
    seeAlso: [{label: 'Core Concepts', href: '/docs/core-concepts'}],
  },
  {
    id: 'task-type',
    term: 'Task type',
    full: 'Task type',
    audience: 'protocol',
    short:
      'A named construction workflow that an agent declares it can perform — `takeoff`, `estimate`, `rfi-generation`, `change-order-analysis`, etc.',
    long:
      'TACO defines 18 task types. An agent advertises its supported task types in its Agent Card skills; the registry can filter by task type.',
    seeAlso: [{label: 'Task types', href: '/docs/task-types'}],
  },
  {
    id: 'skill',
    term: 'Skill',
    full: 'Skill (A2A)',
    audience: 'protocol',
    short:
      'One capability advertised in an Agent Card — has an id, a task type, an optional input schema, and an output schema.',
    seeAlso: [
      {label: 'Core Concepts', href: '/docs/core-concepts'},
      {label: 'ConstructionSkill', href: '/docs/sdk-reference/agent-cards'},
    ],
  },
  {
    id: 'schema',
    term: 'Schema',
    full: 'TACO data schema',
    audience: 'protocol',
    short:
      'A typed JSON shape for a construction artifact — `bom-v1`, `rfi-v1`, `estimate-v1`, `quote-v1`, `schedule-v1`, `change-order-v1`.',
    long:
      'TACO schemas are JSON Schema Draft 2020-12. The Python SDK ships Pydantic models that round-trip with them.',
    seeAlso: [{label: 'Data Schemas', href: '/docs/schemas/'}],
  },
  {
    id: 'registry',
    term: 'Registry',
    full: 'Agent Registry',
    audience: 'protocol',
    short:
      'A directory of TACO agents that can be queried by trade, CSI division, task type, or trust tier.',
    long:
      'Today the SDK ships an in-memory registry with optional JSON-file persistence. A publicly hosted registry is on the roadmap.',
    seeAlso: [
      {label: 'AgentRegistry', href: '/docs/sdk-reference/registry'},
      {label: 'Roadmap', href: '/docs/roadmap'},
    ],
  },
  {
    id: 'sidecar',
    term: 'Sidecar',
    full: 'Agent sidecar',
    audience: 'protocol',
    short:
      'A thin wrapper that exposes an existing platform (Procore, ACC, custom system) as a TACO agent without modifying the platform itself.',
    long:
      'The sidecar translates incoming A2A messages into the platform\'s native API and shapes the responses into typed TACO artifacts. The platform stays untouched.',
    seeAlso: [
      {label: 'Integrate Your Platform', href: '/docs/getting-started/integrate-platform'},
      {label: 'For Platform Vendors', href: '/for/platform-vendor'},
    ],
  },
  {
    id: 'trust-tier',
    term: 'Trust tier',
    full: 'Trust tier',
    audience: 'protocol',
    short:
      'A verification level for an agent in the TACO registry: 0 unverified, 1 org-verified (domain ownership), 2 cert-attested (e.g., SOC2 confirmed).',
    seeAlso: [{label: 'Security', href: '/docs/security'}],
  },
  {
    id: 'json-rpc',
    term: 'JSON-RPC',
    full: 'JSON-RPC 2.0',
    audience: 'protocol',
    short:
      'A simple remote-procedure-call protocol over JSON, used as A2A\'s primary message format.',
    long: 'TACO agents speak JSON-RPC at `/` (or specific `message:send` paths in v1). You rarely need to construct JSON-RPC by hand if you use `TacoClient`.',
  },
  {
    id: 'sse',
    term: 'SSE',
    full: 'Server-Sent Events',
    audience: 'protocol',
    short:
      'A one-way HTTP streaming format. A2A uses SSE for `message/stream` so callers can watch a task\'s progress as it works.',
    aliases: ['Server-Sent Events'],
  },
  {
    id: 'oauth2',
    term: 'OAuth 2.0',
    full: 'OAuth 2.0',
    audience: 'protocol',
    short:
      'The industry standard for delegated authentication. A2A supports five auth schemes; OAuth 2.0 is the recommended one for multi-org TACO deployments.',
    seeAlso: [{label: 'Security', href: '/docs/security'}],
  },
  {
    id: 'json-schema',
    term: 'JSON Schema',
    full: 'JSON Schema (Draft 2020-12)',
    audience: 'protocol',
    short:
      'The standard for describing the structure of JSON data. TACO\'s schemas are JSON Schema 2020-12 — published at `/schemas/{name}.json`.',
    seeAlso: [{label: 'Data Schemas', href: '/docs/schemas/'}],
  },

  // ---- Both ----
  {
    id: 'project',
    term: 'Project',
    full: 'Project (construction)',
    audience: 'both',
    short:
      'A specific job — a building, a renovation, an infrastructure scope. Most TACO schemas carry a `projectId` so multi-agent workflows can reason about which job they belong to.',
  },
  {
    id: 'workflow',
    term: 'Workflow',
    full: 'Workflow',
    audience: 'both',
    short:
      'A multi-step process — in construction, often "takeoff → estimate → procurement → schedule". In TACO, workflows are composed by orchestrators calling multiple agents in sequence or parallel.',
    seeAlso: [{label: 'Cookbook', href: '/docs/cookbook/'}],
  },
];

export const AUDIENCE_LABEL = {
  construction: 'Construction',
  protocol: 'Protocol',
  both: 'Both',
};
