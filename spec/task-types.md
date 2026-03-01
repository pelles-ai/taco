# CAIP Task Types

Task types are the verbs of the CAIP ecosystem. Each task type defines a category of work that an agent can advertise and execute.

> **Schema status:** Fully defined schemas include `bom-v1` and `rfi-v1`. Placeholder schemas (structure not yet defined) include `estimate-v1`, `schedule-v1`, `quote-v1`, and `change-order-v1`. All other output schemas listed below are planned but do not yet have schema files. Contributions welcome.

## Preconstruction

| Task Type | Description | Typical Input | Output Schema |
|-----------|-------------|---------------|---------------|
| `takeoff` | Quantity takeoff from construction documents | Plan sheets (PDF, DWG, RVT) | `bom-v1` |
| `estimate` | Cost estimation from a bill of materials | `bom-v1` | `estimate-v1` |
| `bid-leveling` | Compare and normalize bids from multiple subs | Multiple `estimate-v1` | `bid-comparison-v1` |
| `value-engineering` | Identify cost reduction opportunities | `bom-v1` + `estimate-v1` | `ve-suggestions-v1` |
| `scope-review` | Analyze scope of work for gaps and overlaps | Spec documents, `bom-v1` | `scope-report-v1` |
| `plan-comparison` | Detect changes between drawing revisions | Two sets of plan sheets | `plan-delta-v1` |

## Document Management

| Task Type | Description | Typical Input | Output Schema |
|-----------|-------------|---------------|---------------|
| `rfi-generation` | Flag design conflicts and generate RFIs | Plan sheets, `bom-v1` | `rfi-v1` |
| `rfi-response` | Draft a response to an RFI | `rfi-v1` | `rfi-response-v1` |
| `submittal-review` | Review submittals for spec compliance | Submittal documents, specs | `submittal-review-v1` |
| `spec-compliance-check` | Verify materials/methods against specs | `bom-v1`, spec documents | `compliance-report-v1` |
| `change-order-analysis` | Analyze impact of proposed changes | Change order docs, `bom-v1`, `schedule-v1` | `change-order-v1` |
| `drawing-markup` | Annotate drawings with findings | Plan sheets | Marked-up plan sheets |

## Field + Coordination

| Task Type | Description | Typical Input | Output Schema |
|-----------|-------------|---------------|---------------|
| `schedule-coordination` | Build or update project schedules | `bom-v1`, `estimate-v1`, constraints | `schedule-v1` |
| `material-procurement` | Source materials and get pricing | `bom-v1` | `quote-v1` |
| `clash-detection` | Identify spatial conflicts between trades | BIM models, `bom-v1` from multiple trades | `clash-report-v1` |
| `safety-compliance` | Check plans/site for safety compliance | Site data, plan sheets | `safety-report-v1` |
| `progress-tracking` | Monitor construction progress vs schedule | Site photos/scans, `schedule-v1` | `progress-report-v1` |
| `punch-list` | Generate deficiency lists from inspections | Inspection data, photos | `punch-list-v1` |

## Adding New Task Types

New task types can be proposed via GitHub issue. A proposal should include:
1. Task type name (kebab-case)
2. Description
3. Project phase (preconstruction, document management, field/coordination)
4. Expected input and output schema references
5. At least one real-world use case
