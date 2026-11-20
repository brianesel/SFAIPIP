# Workflow 01 — Evaluation (existing org)

**Purpose:** a scored, evidence-backed picture of the org before any change. Read-only.
**Entry:** G0. **Exit:** scores + wiki reviewed → 03 Alignment.

## Steps
| # | Step | Who | Guardrails | How checked |
|---|---|---|---|---|
| 1 | Mode pick: count objects, Apex lines, Flows, integrations | AI | HG-08, PR-02 | read-only queries; counts sourced |
| 2 | Retrieve metadata into a DX project (read-only); org listed in `orgs.evaluation_readonly` | AI / dev | HG-08, HG-11 | `tools/org_guard.py` blocks every write to that org |
| 3 | Rule coverage: inventory installed rules, generate config from the analyzer map | AI | PR-14 | `tools/rule_map.py inventory`, `generate`, `coverage` |
| 4 | Scan: Code Analyzer with `Recommended` + `Project` selectors, Python ≥3.10 for Flow rules | AI | HG-01, HG-02, HG-03, HG-04, HG-05 | `sf code-analyzer run … --rule-selector Recommended --rule-selector Project` → `docs/wiki/_data/code-analyzer.json` |
| 5 | Triage analyzer hits (false positives, reachability) | AI drafts, dev confirms | PR-02, AI-02 | each counted finding has file + reason |
| 6 | Inventory + business process map (Execution Map) | AI | AI-02, PR-02 | names taken from retrieved source only |
| 7 | Fill `results.json` per rubric check with evidence | AI | PR-02 | missing evidence = not scored, never 0 |
| 8 | Propose judged levels (0/50/100) with reasons | AI | PR-03, AI-01 | `approved_by` left empty for the human |
| 9 | Score with project config | AI | PR-07 | `tools/score.py --config guardrails.project.yaml` (refuses gate overrides) |
| 10 | Write the wiki: verdict first, per aspect and per process | AI | AI-06, PR-02 | confidence tag on every claim |
| 11 | Review scores + wiki with the team | tech lead + PM | PR-03, AI-01 | judged scores approved before anything goes to the customer |

## Outputs
`docs/wiki/` (index, aspect pages, process pages, findings) · `docs/wiki/_data/scores.*` + history.
