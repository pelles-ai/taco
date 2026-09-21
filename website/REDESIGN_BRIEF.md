# TACO website: redesign brief

_Written September 2026 as a decision document. It records where the site is, what the stalled overhaul branch contains, what comparable open-source standard sites do well, and a recommended path. It is a brief, not a spec: nothing here is implemented yet._

## 1. Where things stand

### The site on `main` (what deploys today)

- Docusaurus 3.9.2, classic preset, single `docsSidebar`, one blog post (v0.3 announcement, March 2026).
- 18 doc pages: why / intro / core concepts, 4 getting-started guides, task types, agent-card extensions, 7 schema pages, SDK, CLI, security, examples.
- Homepage: 9 centered sections (hero, problem, standardization table, where TACO fits, three pillars, how it works, architecture diagram, quick start, stats, principles, audience paths, CTA). About 7,600 px tall on desktop.
- Identity: navy `#0f172a` + gold `#EAB308`, self-hosted Inter and JetBrains Mono, dark mode default.
- Known drift: navbar badge is hard-coded `v0.2` and JSON-LD says `0.2.5` while PyPI is at `v0.3.9`. No search. "Spec" in the navbar links out to GitHub.
- Deploy: GitHub Pages workflow on push to `main`.

### The stalled work: `feat/website-overhaul`

19 commits between 24 May and 1 June 2026. No pull request was ever opened. Merge base is the current `main` head, so it still merges cleanly, and it builds green today (verified locally).

It is really two projects in one branch:

**(a) Content and infrastructure expansion, 17 commits, 24 to 28 May.** Very substantial and mostly mergeable.

| Area | What was added |
|---|---|
| Information architecture | Sidebar regrouped into Overview / Concepts / Build / Cookbook / Case Studies / Reference / Protocol & Community |
| Content | 5 cookbook recipes, 3 case studies (labeled illustrative), 8 persona pages under `/for/*`, 5 numbered spec documents + conformance spec, 9 ADRs, roadmap, ecosystem, compare, standards alignment, glossary, RFP template, best practices, pitfalls, protocol stack explainer, 6 more blog posts |
| Reference | Auto-generated per-symbol SDK reference (10 pages, `scripts/gen-sdk-reference.py`), changelog mirrored from repo root at build time |
| Interactive | Pyodide sandbox (`/sandbox`), live conformance runner (`/conformance`), schema explorer + relationship graph, registry filter demo, task-type browser, sequence diagrams in MDX |
| Infrastructure | Local search, per-page OG images (satori + sharp), SDK version read from the latest git tag, last-updated stamps, "Was this page helpful?" footer, `/static/schemas/*.json` published |

**(b) A visual identity experiment, 2 commits, 28 May and 1 June.** "Design overhaul" then "editorial poster redesign": Fraunces serif everywhere (including docs body), near-black ground with vermilion and cobalt, numbered `01`–`10` section markers, a T/A/C/O poster tile in the hero. This is where the work stopped, and it is the unresolved part.

### Verified issues in the overhaul branch

Found by building the branch and rendering it at 1440 px and 390 px in both themes.

1. **Mobile overflow.** The homepage scrolls horizontally on a 390 px viewport (document width 443 px). Cause: the architecture diagram SVG. `main` does not have this bug.
2. **External runtime dependencies.** Fraunces is loaded from Google Fonts, which reverses the existing self-hosted font decision. Pyodide loads from jsDelivr at runtime. Both are fine to keep if chosen deliberately; they were not called out.
3. **Homepage length.** About 14,000 px on desktop, nearly double today's, with 10 numbered sections plus a CTA. The numbering implies a sequence the content does not have.
4. **Navbar density.** Nine items plus search, version badge and GitHub: Docs, SDK, Cookbook, For, Sandbox, Conformance, Spec, Community, Blog.
5. **Status contradiction.** The spec index labels all five specs "Stable 1.0" while the protocol is v0.3, the announcement bar says "active development", and the roadmap lists the v1 wire cutover as in flight. A vendor reading both will trust neither.
6. **Claims that must be true.** A blog post is titled "Five lessons from running a 3-hop agent chain in production" and the case studies say they are "composed from patterns we've seen in early deployments". If these are not backed by real deployments, reword before publishing. The registry demo uses invented company names; label it "sample data" more loudly.
7. **Weight.** `custom.css` grew from 1,652 to 6,162 lines. The build now needs `sharp` (native module) and `satori`.
8. **Docs body in a serif.** Reading long reference pages and code-heavy content in Fraunces is a taste call, and no comparable protocol site does it. Worth a deliberate decision rather than an inherited one.

## 2. The goal, stated plainly

The site has one job: make TACO credible and adoptable to three readers who arrive with different questions.

| Reader | Their question | What convinces them |
|---|---|---|
| Python developer | Can I have an agent talking in ten minutes? | Install line, real payload above the fold, sandbox, SDK reference, conformance check |
| Platform vendor (Procore-type PM, architect) | Is this neutral, stable, and will it still exist in two years? | Spec with versions and status, governance and change process, roadmap with dates, conformance suite, who else is on board |
| Construction person (GC, sub, owner) | What does this do for my RFI, estimate, change order? | One plain-language page per role, a workflow drawn as a handoff between named agents, vocabulary they already use |

TACO is a **domain standard on top of a generic protocol**, the same shape as FHIR on HTTP+JSON for healthcare. That means the site should borrow more from standards sites (FHIR, OpenTelemetry, MCP, A2A, buildingSMART) than from developer-tool landing pages (Vite, Bun). Dev-tool sites sell speed with benchmarks; standards sites sell trust with status, governance and adopters.

Success looks like:

- A developer reaches a running agent from the homepage in under ten minutes without leaving the site.
- A vendor can find spec, conformance and governance within two clicks of the homepage.
- A GC understands what TACO does from one page that contains no code.
- Every number on the site (version, task-type count, schema count) comes from one source of truth and is never hand-edited.

## 3. What the best open-source standard sites do

Research covered three groups: protocol and standards sites, admired developer-tool sites, and open-source AEC projects. Most protocol and AEC domains were blocked by this environment's network policy, so those findings come from the sites' public source repositories and search snippets, and first screens should be re-verified in a normal browser.

### Protocol and standards sites

- **Two front doors, one site.** A plain-language homepage plus a Specification section that is the normative artifact with permanent per-version URLs (MCP uses dates, OpenAPI uses `/oas/v3.2.0`) and a `latest` alias. TACO already has both halves in the overhaul branch; they need the URL discipline.
- **Explicit relationship to neighbours.** Every agent-protocol site has an "X and MCP / A2A" page and an "Is / Is Not" list. A2A's own "What A2A Is Not" section is the model. TACO needs "TACO and A2A", "TACO and MCP", and "TACO and IFC / BIM" pages, and should describe itself as a construction-domain A2A extension so it can be listed in A2A's extension registry.
- **Status and maturity page (OpenTelemetry).** Per message type and per SDK: Stable / Beta / Draft. This is the single most credible thing a young standard can publish, and it resolves issue 5 above.
- **Implementations registry, data-driven (OTel registry, AsyncAPI tools, FHIR IG registry, Open Banking directory).** A JSON file rendered as a filterable grid, each entry badged "conformant / self-declared / in progress". buildingSMART's honesty about vendor self-reporting is the tone to copy.
- **Governance page and roadmap with a "last updated" date and linked issues (A2A, AsyncAPI).** Name the steering group even if it is small. State the change process (the overhaul's spec index already sketches an RFC flow).
- **Spec status header (W3C ReSpec style).** Status, publish date, previous version, editors, link to the test suite, at the top of every spec document.
- **Audience-split value props (MCP: developers / apps / end-users).** TACO's three readers, in that order, each with its own CTA.
- **Code-first hero element (CloudEvents, AsyncAPI).** A real `rfi-v1` or `change-order-v1` payload visible above the fold.
- **SDK row in the header, not a single GitHub icon (A2A).** Even with one SDK today, the pattern signals intent.
- **LLM-ready docs.** `llms.txt` exists on `main`; add "copy page as markdown" (MCP) and keep URLs predictable. Agents will read the spec more often than humans.
- **Own the namespace.** agentprotocol.ai lapsed and was taken over by a third-party explainer. Keep taco-protocol.com the canonical spec host.

### Open-source AEC and domain-standard sites

- **FHIR's persona intros** are the closest analogue to the overhaul's `/for/*` pages: executive summary, developer intro, clinical intro, architect intro, all one click from the landing. Keep the `/for/*` pages; add a developer intro that opens with a JSON resource and the nine operations, as FHIR does.
- **Speckle** wins the dual audience by leading with outcomes ("faster bids, design reviews") and pushing the GraphQL story to docs. Named firms (Arup, Grimshaw) and per-integration pages ("Speckle for Power BI") are the trust pattern; "TACO for Procore" and "TACO for Autodesk" pages would map directly.
- **That Open Company and IfcOpenShell** are code-forward and have no non-developer layer at all: what TACO should avoid.
- **buildingSMART** shows the certified vs self-declared distinction for implementations, and the Validation Service as a credibility tool. The overhaul's `/conformance` page is already this; it should be linked from the spec header and from registry badges.
- **GS1's three-verb model** (Identify / Capture / Share) repeated everywhere: TACO's equivalent is already latent as Define / Discover / Communicate or Task types / Schemas / Discovery. Pick one and repeat it.
- **Open Banking** puts live ecosystem counts on the hero. TACO should not fake this; publish the count once there is one, and until then publish the honest "who is shipping" list the overhaul's ecosystem page already has.
- **Construction readers expect their vocabulary**: RFI, submittal, takeoff, change order, CSI division, sub, GC, owner. Every task-type page should open with a one-paragraph job-site scenario before the schema.
- **Visual character.** No site in this space uses job-site photography well; most use UI screenshots, schema diagrams or 3D viewers. Schematic handoff diagrams with schema names on the arrows (the overhaul's sequence diagrams) are the right differentiator.
- Other projects worth watching: OpenAEC Foundation (open-aec.com, IFCX), the opensource.construction directory (a ready pattern for a registry), Bonsai. No other construction-specific agent ontology was found, which supports TACO's positioning.

### Developer-tool landing pages

Sites reviewed: Astro, Vite, Bun, Tailwind, Zod, Effect, Biome, Supabase, Prisma, Turborepo, the Docusaurus showcase and Starlight. The common anatomy in 2026:

- **Hero formula.** One-sentence category claim, one-sentence "what it is", two CTAs (Get started, Docs or GitHub), install command with copy button, and a release pill above the headline ("v4.0 RC", "3.x is out") to signal liveness. Every site does this; TACO's `main` already does most of it.
- **"What is X?" section immediately after the hero** (Astro's intro, Effect's annotated mental model). Protocols need this more than tools do.
- **Pain → solution pairs** (Effect's problem statement) beat feature lists for mixed audiences: "Procore's RFI doesn't fit Autodesk's RFI" → "one typed `rfi-v1`". The overhaul's problem section is halfway there.
- **Input → output demo** (Biome, Tailwind): raw RFI or schedule JSON on the left, the TACO-typed A2A message on the right. This is TACO's most honest demo and it needs no benchmark.
- **Two-tier features** (Vite): first "what it defines" (task types, schemas, discovery), then "what you build on it" (SDK, sidecars, adapters).
- **Bento of one-liners for non-developers** (Supabase's product grid): map to construction domains (preconstruction, documents, field, supply chain) rather than to code.
- **An explicit "works with AI agents" section** (Effect, Turborepo, Prisma): TACO's native story. Include an LLM quick-start page.
- **Proof: real third-party data or none.** Astro charts HTTP Archive data; Biome auto-generates rule counts. For a standard, counters computed from `spec/` are the honest substitute. Avoid benchmark heroes (Bun, Biome); TACO has no speed story.
- **Closing CTA repeats the hero button and install command** (Astro, Vite, Effect).
- **Docs table stakes:** grouped sidebar (Start / Concepts / SDK / Reference), search, version dropdown, edit-on-GitHub, last-updated, package-manager tabs. The overhaul covers all but the version dropdown.
- **Docs differentiator in 2026:** per-page "Copy as Markdown / Open in Claude or ChatGPT", `.md` twins of every page, `llms.txt` and `llms-full.txt`, an MCP server link (Zod, Bun, Prisma all advertise this in plain text). Docusaurus community plugins deliver all of it (`docusaurus-plugin-llms-txt`, `docusaurus-plugin-copy-page-button`).
- **Heavily customised Docusaurus is possible without leaving theme-classic:** React Native, Jest, Hasura, Relay, WebdriverIO and Ionic are the showcase proofs. Most are classic theme plus custom CSS, which is exactly TACO's setup.
- **Starlight trade-off:** faster, zero-JS default and a cleaner base theme, but no first-class versioning and no built-in blog. Since TACO is a versioned protocol with a PyPI SDK, stay on Docusaurus.

## 4. Options

**Option A. Merge the content, keep the current identity.** Land commits 1 to 17 of the overhaul in reviewable pieces, drop or park the two identity commits, fix the verified issues on the way. Fastest path to a much better site. Risk: the homepage stays visually generic.

**Option B. Merge the content and commit to a new identity.** As A, then resolve the identity properly instead of inheriting the poster experiment. Note that the current experiment (near-black, one vermilion accent, serif display, numbered sections) is a widely recognisable template look in 2026, and the taco logo is gold, so the switch also orphans the brand mark.

**Option C. Change platform** (Astro Starlight, Mintlify, Fumadocs). Not recommended now. The content is the moat, Docusaurus is not the bottleneck, and the overhaul is already deeply invested in Docusaurus plugins and swizzles.

**Recommendation: A, then a scoped identity decision.** Merge in phases, fix the eight issues, and treat identity as its own small PR that compares two or three directions on the homepage only. My suggested direction: keep navy + gold (it is the logo) and make it distinctive through construction-document conventions rather than fashion: drawing title blocks, sheet and revision numbering, CSI division numbers as real structure, spec-section numbering where the content actually is a sequence. That is a detail only this subject can own.

## 5. Proposed sequence

### Phase 0: turn the branch into reviewable PRs (one to two weeks)

Split `feat/website-overhaul` by its own commit labels. Each PR builds green, is under about 3,000 lines, and carries its fix list.

| PR | Overhaul commits | Fixes to carry |
|---|---|---|
| 1. Infrastructure | `ce10bd8` phase 1 (version from git tag, OG metadata, search, a11y), `320e926` OG images, `489dd55` changelog + page footers | Decide on `sharp` in CI; keep fonts self-hosted |
| 2. IA and core content | `f18c1fd` phase 3 IA + roadmap/ecosystem/compare, `b859e52` explainer, `a4d280a` glossary + standards, `65ce230` ADRs + best practices + scoping | Spec status labels: Draft / Provisional per current reality, not Stable 1.0 |
| 3. Cookbook and reference | `6202933` cookbook, `4383980` SDK reference, `bebe3af` cookbook enrichment + pitfalls + ADRs | Verify generated reference matches `sdk/` at v0.3.9 |
| 4. Persona pages | `a30017e` /for/*, `9973e9c` and `ec5c544` trade pages | Persona nav as one "For" dropdown; remove Sandbox and Conformance from top nav, link them from Build |
| 5. Interactive | `c73a323` registry filter + Pyodide sandbox, `43052d2` schema explorer, `0b9b7b7` conformance runner | Fix mobile SVG overflow; label registry data as sample; accept or replace the Pyodide CDN |
| 6. Case studies and blog | `9973e9c`, `ec5c544`, `bebe3af`, `65ce230` narrative parts | Confirm every production claim or reword; consider dating posts at publish time |
| 7. Identity (decision first) | `8919f52`, `81a231e`, `2fb49de` | Do not merge as-is; use as one of the compared directions |

### Phase 1: homepage rewrite (one week)

Target: seven sections, under 8,000 px, no horizontal scroll at 390 px, both themes.

1. **Hero.** One literal sentence ("The shared vocabulary construction AI agents use to hand work to each other"), install line with copy, three CTAs by reader (Build an agent / Read the spec / See it for my trade), and a real payload or a three-agent handoff diagram instead of a logo poster.
2. **Is / is not.** TACO and A2A and MCP in one strip; the overhaul's stack explainer, compressed.
3. **Three pillars tied to readers.** Task types, schemas, discovery, each pointing to the browser, explorer and registry demo.
4. **One recipe, drawn.** GC → estimator → supplier sequence diagram with schema names on the arrows, linking to the cookbook.
5. **Try it.** Registry filter demo, plainly labeled sample data, with the sandbox link.
6. **Status and ecosystem.** Maturity table (from the new status page) and the honest "who is shipping" list. Counters computed from `spec/`, never typed.
7. **Get involved.** Governance in two sentences, roadmap link, discussions, star.

### Phase 2: standards-grade pages (two weeks)

- `/docs/status`: maturity per task type, schema and SDK, generated from a JSON file.
- `/ecosystem` becomes a registry: JSON-driven grid, badges for conformant / self-declared, GitHub issue form to submit.
- Spec status header component on every `SPEC-00x` page; permanent `/spec/v0.3/...` URLs with a `latest` alias.
- Governance page: who decides, how a change is proposed, release cadence.
- "Copy page as markdown" on docs pages; refresh `llms.txt` from the sidebar at build time.

### Phase 3: identity (one week, after the above is live)

Two or three homepage-only mockups compared side by side, then one PR. Whatever is chosen is applied to docs typography only if it reads well on the SDK reference and schema pages.

## 6. Decisions needed

1. Keep navy + gold or adopt a new identity? (Recommendation: keep, evolve.)
2. Are the production and "early deployments" claims true as written, or should they be reworded before the blog posts and case studies go live?
3. Spec status labels: adopt Draft / Provisional / Stable and label SPEC-001 to 005 honestly?
4. External runtime dependencies: accept Google Fonts and the Pyodide CDN, or self-host?
5. Accept `sharp` + `satori` in the build for OG images, or generate them offline and commit the PNGs?
6. Is a Status page and a data-driven registry worth doing before there are external implementations? (Recommendation: yes for status, and publish the registry with honest zero-to-few entries.)
