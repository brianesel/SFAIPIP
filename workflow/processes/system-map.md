# Process — System map (design, draft)

**Status:** built 2026-11-23 (`tools/system_map.py`: generate, query, search, lint, questions; schema `guardrails/schemas/system-map-schema.yaml`). Apex field-write detection is a simple parse [med] (open decision 1); the code-graph link is not built (use a code-graph tool alongside). Owner: tech lead.

**Verdict:** every project keeps one living map of the org in three linked layers: processes (how users work), features (what exists and which tests prove it), automation (what fires, in which order, writing which fields). The automation layer is generated from retrieved metadata and never hand-edited. People write only what metadata cannot show: purpose and how users work. The map is seeded by evaluation (01), grows with every ticket, and is checked in CI so it cannot drift.

## 1. Why
| Need | Today | With the map |
|---|---|---|
| Know what a feature is and who uses it | spread over tickets, people's heads, the old ticket system | one feature entry linked to processes and roles |
| Know what proves a feature works | `traceability.md` per requirement, not per feature | feature → automated tests + UAT cases, generated |
| Find what fires on a record | read every flow, trigger and rule by hand | one lookup per object and event |
| Judge the impact of a change | dependency API + guesswork | component → features → processes → tests to re-run |
| Give agents context | rebuilt for every ticket | read from the map (context pack, section 7 of `automated-pipeline.md`) |

## 2. Layers
| Layer | Answers | Contents | Made by |
|---|---|---|---|
| **Process** (`PROC-nn`) | how do users work? | process → ordered steps → role / persona per step → features used per step | written: discovery, intake, UAT recordings; reviewed by the process owner |
| **Feature** (`FEAT-nn`) | what exists, what proves it works? | purpose (one line) · processes and steps that use it · REQ / tickets · components · automated tests · UAT cases and recordings · owner · status | generated from tickets, `agreed.yaml` and test sources; purpose and owner written |
| **Automation** (API names) | what fires, in which order, writing what? | per object and event: execution order, field writers, entry points, dependencies | generated from retrieved metadata only (AI-02) |

**Automation layer detail**
| View | Content | Source | Confidence |
|---|---|---|---|
| Execution order | per object and event (create / update / delete / undelete): before-save flows, before triggers, validation rules, after triggers, after-save flows, async paths, in Salesforce's order of execution | flow metadata (trigger type, object, entry conditions), triggers, validation rules | [high] for record-triggered automation · [med] for order between multiple flows on the same object without trigger order set |
| Field writers | for each field: every flow element, Apex assignment, workflow field update, formula dependency that writes or reads it | flow XML, Apex parse, workflow metadata | [high] flows and workflow · [med] Apex (dynamic field references are missed) |
| Entry points | how each automation starts: UI (LWC, Aura, quick action), API (Apex REST, invocable), schedule, platform event, email service | metadata | [high] |
| Dependencies | component ↔ component references | Tooling API `MetadataComponentDependency` + parse | [high] exists · [med] coverage of all types |

The existing Execution Map from evaluation (01, step 6) becomes the first version of this layer.

## 3. Layout in a project
```
docs/wiki/map/
  index.md                  generated: entry page, links to every process, feature, object
  processes/PROC-nn-<slug>.md   written (frontmatter + text)
  features/FEAT-nn-<slug>.md    frontmatter generated + one written purpose line
  objects/<Object>.md           generated: execution order, field writers, entry points
docs/wiki/_data/map/
  map.json                  generated: full index for agents and search
  generated-at.yaml         commit sha + org alias + retrieve date the automation layer was built from
```
Pages are generated from frontmatter and `map.json`. Written text lives only in process pages and the feature purpose line, so regeneration never overwrites human text.

## 4. Entry formats
Schema file `guardrails/schemas/system-map-schema.yaml` (new). Shapes:

```yaml
# processes/PROC-03-order-to-cash.md (frontmatter)
id: PROC-03
name: Order to cash
owner: <process owner>
steps:
  - {n: 1, name: Create quote, role: Sales rep, features: [FEAT-12]}
  - {n: 2, name: Approve discount, role: Sales manager, features: [FEAT-14]}
source: <person · date · discovery log / recording>
```
```yaml
# features/FEAT-14-discount-approval.md (frontmatter)
id: FEAT-14
purpose: Discounts above the threshold need manager approval before the quote can be sent.   # written
aliases: [discount approval, price exception, margin approval]                                # written; helps full-text search
owner: <person>
status: live            # planned | in_progress | live | retired
processes: [PROC-03#2]
req: [REQ-021]
tickets: [SF-118, SF-131]
components: [{type: flow, name: <API name>}, {type: apexclass, name: <API name>}]
tests:   {automated: [<Class.method>], uat: [SF-131/C-07], recordings: [<path>]}
```
Every name must exist in retrieved metadata or the source tree; `system_map.py lint` rejects unknown names (AI-02).

## 5. Search
`tools/system_map.py query` (new) answers the common questions in one call, for people and agents:

| Question | Query |
|---|---|
| What writes this field? | `query writes Opportunity.<Field>` |
| What fires when a record of this object is updated? | `query fires Case update` |
| Which features use this component? | `query used-by <API name>` |
| Which tests prove this feature? | `query tests FEAT-14` |
| Which processes are affected if this changes? | `query impact <API name>` → features → processes → tests |
| Where is this process step implemented? | `query step PROC-03#2` |

**Search approach (decided 2026-11-23): structured query + full-text search, no RAG.**
The map is structured, linked data. Exact queries return every match or none; similarity search returns what looks closest and can silently miss one of several field writers, which is a missed regression in impact analysis.

| Content | Search method | Why |
|---|---|---|
| Automation and feature layers (IDs, API names, links, field writers) | `system_map.py query` only | completeness matters; never similarity |
| Written text: process pages, feature purposes, discovery log, old-ticket export | `aliases:` in frontmatter + full-text search (`system_map.py search "<words>"`, SQLite FTS5 or ripgrep) | catches different words for the same thing at no extra infrastructure |
| Same written text, only if full-text search measurably misses | embeddings as a candidate finder; facts then come from the structured links | added on evidence, never decides an impact |

| | RAG | Structured + full-text |
|---|---|---|
| Completeness | approximate, misses are invisible | complete or empty |
| Freshness | re-embedding is one more index that can fall behind | regenerated per ticket, CI-checked |
| Infrastructure | vector store, embedding pipeline, chunking, tuning | one script + files in git |
| Data handling | metadata and process text go to an embedding provider unless self-hosted | stays in the repo |
| Audit | hard to explain why a result came back | every answer points to a file and line |

**Evidence gate:** keep a question set in `docs/wiki/_data/map/questions.yaml`: 20–30 real questions with known answers (for example "what runs when an order is cancelled?"). Run it against query + full-text search when the map changes shape. Add embeddings for written text only when failures caused by wording are a meaningful share. The set doubles as a regression test for the map.

**Reconsider RAG when** [med]: a large free-text history is imported (thousands of old tickets), one search must span several projects or orgs, or business users ask questions in chat instead of agents running queries.

**Relation to the code graph:** a code-graph index (for example codebase-memory) covers Apex call chains well; flows, validation rules and field writes are metadata it does not model [med]. Use the code graph for Apex calls, the map for everything else; `query impact` may call both.

## 6. Steps
| # | Step | Who | Guardrails | How checked |
|---|---|---|---|---|
| 1 | Seed the automation layer from the evaluation retrieve (existing org) or from source (new org) | AI | AI-02, PR-02, HG-08 | `system_map.py generate`; `generated-at.yaml` names the source |
| 2 | Seed process pages from the evaluation process map or discovery log | AI drafts, process owner confirms | PR-02, AI-01 | every step has a source and a role |
| 3 | Seed features only for the most critical processes; the rest grow per ticket | AI drafts, tech lead confirms | PR-02, AI-01 | `system_map.py lint` |
| 4 | Per ticket, before intake: read map entries for the likely area into the context pack | orchestrator | PR-02 | `context.md` cites map entries |
| 5 | Per ticket, before the PR: regenerate the automation layer; propose feature and process updates for touched components | orchestrator + AI | AI-02, PR-12, AI-01 | map diff in the PR; human approves written parts |
| 6 | CI on every PR: every changed component maps to ≥ 1 feature; generated layer matches source; no unknown names | CI | PR-12, AI-02, G4 | `system_map.py lint --changed` |
| 7 | Release: feature status → live; retired components → features `retired` | AI drafts, release approver confirms | PR-12, AI-01 | lint shows no live feature pointing to deleted components |

## 7. Rules
- Generated files are never edited by hand; fix the source or the generator.
- Written text has a source and an owner; AI drafts it, a human confirms it (AI-01, PR-02).
- A name that is not in metadata or source is an error, not a guess (AI-02).
- The map describes the org as built; intended future behaviour belongs in requirements and tickets.
- Traceability (`docs/delivery/traceability.md`, PR-12) stays the requirement → ticket → test → release view; the feature map is the feature view of the same data. Both are generated from the tickets, so they cannot disagree.

## 8. Relation to what exists
| Existing | Becomes |
|---|---|
| Evaluation wiki process pages (01, step 10) | seed for the process layer |
| Execution Map (01, step 6) | first version of the automation layer |
| `docs/delivery/traceability.md` | unchanged; generated from the same ticket data |
| Pattern register | linked from features (which pattern a feature follows), not duplicated |
| Context pack (`automated-pipeline.md` section 7) | reads the map first, falls back to live lookups |

## 9. Build order
| Phase | Scope | Done when |
|---|---|---|
| A | schema, `system_map.py generate` for the automation layer, `query writes` / `fires` | one sample org's objects have generated pages; answers match a manual check on 5 fields |
| B | feature and process entries, `lint`, CI check, pipeline update step | a ticket's PR shows a map diff; CI fails on an unmapped component |
| C | `query impact`, `search` (full-text), question set, code-graph link, impact tester uses feature → tests | impact report names affected processes and the tests it re-ran; question set passes |

## 10. Open decisions
| # | Question | Default if not decided |
|---|---|---|
| 1 | Apex field-write detection: simple parse or Apex language server / PMD AST | PMD AST via Code Analyzer [med: needs a spike] |
| 2 | Where process owners review written pages: PR review or a rendered portal | PR review |
| 3 | Seed scope for large orgs: top N processes by criticality | top 5 |
| 4 | Pass level for the question set before embeddings are considered | ≥ 90 % answered correctly [low: set after the first run] |
