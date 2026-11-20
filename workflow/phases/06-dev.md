# Workflow 06 — Dev + test loop

**Purpose:** implement → test → feedback, repeated until every acceptance criterion passes. Tests are agreed before code.
**Entry:** G3 (ticket Ready). **Exit gate:** G4 per ticket.

```
Test design ─► Implement ─► Test ─► Feedback ─┬─ code defect ──► Implement
                                               ├─ test wrong ───► Test design (tester + dev agree)
                                               ├─ AC wrong ─────► change request, loop pauses
                                               └─ all AC pass ──► Done check (G4)
```

## Steps
| # | Step | Who | Guardrails | How checked |
|---|---|---|---|---|
| 1 | Start: G0–G3 pass, ticket → in_progress, test folder | dev | G3 | `tools/dev_cycle.py start <KEY>` |
| 2 | Tester writes `tester.yaml` from AC | tester | PR-08 | schema `guardrails/schemas/test-case-schema.yaml` |
| 3 | AI writes `ai.yaml` without reading the tester set | AI | AI-03, AI-02 | separate files; skill rule |
| 4 | Align: both / tester-only / AI-only / gaps → decide each case | tester + dev | PR-08, AI-01 | `dev_cycle.py align <KEY>` then `--check` |
| 5 | Implement, following the ticket pattern | dev + AI | PR-08, PR-06, HG-06, HG-07, HG-03 | hook blocks force-app until agreed tests valid; review |
| 6 | Write the automated tests named in `agreed.yaml` | dev + AI | HG-04, HG-05 | Code Analyzer; `dod` checks methods exist |
| 7 | Run tests in dev/QA sandbox, import results | dev + AI | HG-09, HG-11, AI-05 | `tools/org_guard.py` hook allows only verified write-allowed sandboxes; `dev_cycle.py import-apex` |
| 8 | Static scan of changed files with project rules | AI | HG-01, HG-02, HG-10 | `--rule-selector Recommended --rule-selector Project` → `code-analyzer.json`, 0 sev 1–2 |
| 9 | Manual/UAT cases with evidence | tester | AI-05 | evidence required per case |
| 10 | Feedback: classify each failure | team | PR-05, AI-04 | `dev_cycle.py report <KEY>` |
| 11 | Loop guard: same case failing 3 iterations → escalate | AI + tech lead | PR-09, AI-04 | ⛔ in report |
| 12 | Boy scout only inside touched code, within budget | dev | PR-10 | PR review |
| 13 | Done check | dev | G4, PR-12 | `dev_cycle.py dod <KEY>` (+ CI on PR) |
| 14 | PR review; reviewer sets `reviewed_by`, `pr`, `status: done` | reviewer | G4, AI-01, AI-05 | AI never sets done |

## Outputs
Code + tests in force-app · `docs/tests/<KEY>/` (agreed set, iterations, results) · Done ticket.
