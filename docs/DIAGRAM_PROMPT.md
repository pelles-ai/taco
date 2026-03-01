# CAIP Diagram Generation — Claude Code Prompt

Use this prompt with Claude Code to generate the architecture diagrams for the CAIP repo.
The diagrams should be generated as SVG files in `docs/diagrams/`.

---

## Prompt

Generate SVG architecture diagrams for the CAIP (Construction Agent Interoperability Protocol) repository. Place them in `docs/diagrams/`. Use a clean, modern style with rounded rectangles, clear labels, and the color palette below. No drop shadows or gradients — keep it flat. Use a sans-serif font (Inter or system sans-serif). All text should be crisp and readable at both full size and scaled down in a README.

### Color Palette

Use these colors consistently across all diagrams:

- Preconstruction agents: fill `#EDE9FE`, stroke `#8B5CF6`
- Document Management agents: fill `#DBEAFE`, stroke `#3B82F6`
- Field/Coordination agents: fill `#D1FAE5`, stroke `#22C55E`
- External Parties agents: fill `#FFE4E6`, stroke `#EF4444`
- Supply Chain agents: fill `#FFF7ED`, stroke `#F59E0B`
- Orchestration agents: fill `#CCFBF1`, stroke `#06B6D4`
- CAIP layer: fill `#FEF9C3`, stroke `#EAB308`, bold border
- Registry: fill `#DBEAFE`, stroke `#3B82F6`
- Data schemas (labels on arrows/connections): color `#15803D`, italic
- Input/output nodes: fill `#FED7AA` (input), fill `#BBF7D0` (output), stroke matching
- Background: white
- Text: `#1E1E1E` primary, `#6B7280` secondary/annotations

### Diagram 1: `caip-overview.svg`

**Title:** "CAIP — How It Works"

This is the main architecture diagram. Layout:

**Center band:** A prominent horizontal bar representing the CAIP layer. Label: "CAIP — shared task types, data schemas, agent discovery". Below it, a smaller box: "Agent Registry (discovery by trade, skill, CSI division)".

**Above the CAIP bar** — three zones side by side, each containing agent boxes:

1. **Preconstruction** zone (purple tones):
   - Takeoff Agent, Estimating Agent, Bid Leveling Agent, Scope Review Agent, Plan Compare Agent
   - Arrow down to CAIP bar labeled "bom-v1, estimate-v1"

2. **Document Management** zone (blue tones):
   - RFI Agent, Submittal Agent, Spec Check Agent, Change Order Agent, Markup Agent
   - Arrow down to CAIP bar labeled "rfi-v1, submittal-v1"

3. **Field + Coordination** zone (green tones):
   - Schedule Agent, Procurement Agent, Clash Detection, Safety Agent, Progress Tracking
   - Arrow down to CAIP bar labeled "schedule-v1, quote-v1"

**Below the CAIP bar** — three zones side by side:

4. **External Parties** zone (red tones):
   - Architect Agent, Engineer Agent, Inspector Agent
   - Arrow up to CAIP bar

5. **Supply Chain** zone (orange tones):
   - Supplier Agent, Manufacturer Agent, Logistics Agent
   - Arrow up to CAIP bar

6. **Orchestration** zone (teal tones):
   - GC Orchestrator Agent (wider box)
   - Annotation: "Discovers agents, delegates tasks, assembles deliverables"
   - Arrow up to CAIP bar

**Bottom text:**
- "Every agent is built by a different company. None share internals."
- "They interoperate because they share a language: CAIP."
- "Open spec | Open schemas | Open SDK"

### Diagram 2: `caip-agent-chain.svg`

**Title:** "Agent Composition — Typed Schema Flow"

A horizontal pipeline showing how agents chain together via typed schemas:

```
[Plan Sheets] → [Takeoff Agent] →bom-v1→ [Estimating Agent] →estimate-v1→ [Supplier Agent] →quote-v1→ [Bid Package]
                      │                        │
                      ▼                        ▼
                 [RFI Agent] →rfi-v1→ [Architect Agent]     [Schedule Agent]
                                    (input-required:         (consumes bom-v1 +
                                     human review)           estimate-v1)
```

- Main flow is horizontal, left to right
- Branching flows go downward
- Schema labels (bom-v1, estimate-v1, etc.) on arrows in green italic
- Annotations in gray for the human-in-the-loop and schedule consumption notes

### Diagram 3: `caip-agent-card.svg`

**Title:** "Construction Agent Card — Extended Fields"

A visual showing an Agent Card JSON structure with callout annotations:

Left side: a dark-background code block showing a sample Agent Card JSON:
```json
{
  "name": "Pelles Mechanical Takeoff Agent",
  "url": "https://api.pelles.ai/a2a",
  "version": "1.0.0",
  "capabilities": { "streaming": true },
  "x-construction": {
    "trade": "mechanical",
    "csiDivisions": ["23", "22"],
    "projectTypes": ["commercial", "healthcare"],
    "dataFormats": {
      "input": ["pdf", "dwg", "rvt"],
      "output": ["bom-json", "csv", "pdf"]
    },
    "integrations": ["procore", "acc"]
  },
  "skills": [{
    "id": "generate-bom",
    "x-construction": {
      "taskType": "takeoff",
      "outputSchema": "bom-v1"
    }
  }]
}
```

Right side: annotation callout boxes with arrows pointing to relevant JSON sections:
1. "Identity — who is this agent?" → name/url fields
2. "Trade + CSI Division — discoverable by trade" → x-construction.trade
3. "Input/Output formats" → dataFormats
4. "Platform integrations" → integrations
5. "Skills with typed schemas" → skills.x-construction

### Diagram 4: `caip-a2a-relationship.svg`

**Title:** "CAIP + A2A — Ontology, Not Fork"

A layered diagram showing the relationship:

```
┌─────────────────────────────────────────────────────┐
│  CAIP (ontology layer)                               │
│  Construction task types, data schemas, discovery    │
├─────────────────────────────────────────────────────┤
│  A2A Protocol (transport + lifecycle)                │
│  Agent Cards, Tasks, Messages, Artifacts             │
├─────────────────────────────────────────────────────┤
│  HTTP / JSON-RPC / SSE                               │
│  Standard web infrastructure                         │
└─────────────────────────────────────────────────────┘
```

- Three stacked layers, CAIP on top (yellow), A2A in middle (purple), HTTP at bottom (gray)
- Side annotation: "A generic A2A client can talk to any CAIP agent — it just ignores the x-construction fields"
- Side annotation: "A CAIP-aware client gets richer discovery, typed schemas, and trade-specific filtering"

### Generation Notes

- Use Python with `svgwrite` or raw SVG XML — whichever produces cleaner output
- Target width: 1200px for overview diagrams, 900px for smaller ones
- Make sure text is actual SVG `<text>` elements (not paths) so it's searchable/selectable
- Test that the SVGs render correctly in GitHub markdown preview
- Also export PNG versions at 2x resolution for docs that don't support SVG
