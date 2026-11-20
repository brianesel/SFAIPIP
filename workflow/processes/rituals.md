# Process — Rituals and cadence

| Ritual | Cadence | Input | Output | Guardrails |
|---|---|---|---|---|
| Status check | daily | `tools/status.py` | first failing gate | G0, G1, G2 |
| Weekly report | Monday | `tools/weekly_report.py` | `docs/reports/weekly-<date>.md` | G3, PR-07 |
| Refinement (≤ 1 h) | weekly | failing / not-ready tickets | next 1–2 sprints Ready | G3, PR-04 |
| CR triage + change board | weekly / on demand | open CRs | decisions, re-baseline | PR-05 |
| Sprint planning | per sprint | Ready tickets, capacity split | sprint scope | PR-10 |
| Sprint review | per sprint | Done tickets | demo, new CRs | G4, PR-05 |
| Release | per release | Done tickets | `phases/07-delivery.md` | G5 |
| Re-assess + ratchet | per release / quarterly | `tools/score.py --config` | score trend, tighter thresholds, waiver review | PR-07, PR-11 |
| Baseline feedback | per release | overrides seen in ≥ 2 projects | proposal to change this package | PR-11 |
