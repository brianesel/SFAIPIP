# Workflow 03 — Alignment

**Purpose:** turn baseline guardrails + evaluation into project-specific guardrails the team can follow.
**Entry:** evaluation reviewed (01) or discovery draft (02). **Exit gate:** G1.

## Steps
| # | Step | Who | Guardrails | How checked |
|---|---|---|---|---|
| 1 | Walk the scorecard: worst pillar gaps, failed gates | tech lead + PM | PR-03 | only approved scores used |
| 2 | Per concern: current vs target pattern, fitted to team size | AI drafts, tech lead decides | PR-06, AI-01 | `docs/wiki/pattern-register.md` |
| 3 | Migration decision per gap (now / when touched / leave) + effort range | AI drafts, team decides | PR-06 | `docs/design/migration-plan.md` |
| 4 | Agree overrides (non-gate checks) and waivers (gates, existing code) | tech lead + approver | PR-07 | `tools/status.py` refuses gate overrides, incomplete or expired waivers |
| 5 | Agree capacity split (feature / migration / boy scout) | PM | PR-06 | `capacity_split` in `guardrails.project.yaml` |
| 6 | ADR per override and target pattern | AI drafts | PR-06, AI-01 | ADR ids referenced in the project file |
| 7 | Project rules → analyzer rules: built-in where it exists, else AI drafts a custom rule with fixtures; test; tech lead approves | AI drafts, tech lead approves | PR-14, AI-01 | `tools/rule_map.py generate`, `test`, `coverage` (`processes/analyzer-rules.md`) |
| 8 | Architecture decision cards (`best-practices/architecture/decisions/`, copied to `docs/decisions/`): AI fills project facts and a proposal; named human chooses | AI drafts, tech lead / approver decides | PR-15, AI-01 | `architecture` block; `tools/status.py` blocks G1 while any card is `pending` |
| 9 | Org policy: production, evaluation-readonly and write-allowed sandboxes | tech lead | HG-11 | `orgs` block; `tools/org_guard.py verify <alias>` |
| 10 | Approver signs project guardrails | approver | G1, AI-01 | `approval` block; `tools/status.py` |

## Outputs
`guardrails.project.yaml` (approved) · migration plan · pattern register · ADRs.
