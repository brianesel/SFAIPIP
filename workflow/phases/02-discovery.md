# Workflow 02 — Discovery loop (new or minimal org)

**Purpose:** answer every must-decide question, then plan and challenge the design. Loop until signed off.
**Entry:** G0. **Exit:** design draft → 03 Alignment, then G2 in 04 Requirements.

## Steps
| # | Step | Who | Guardrails | How checked |
|---|---|---|---|---|
| 1 | Read existing notes/docs; drop already-answered questions | AI | PR-02 | answers cite source |
| 2 | Ask must-decide gaps from `discovery-question-bank.yaml`, ≤ 4 per round | AI | PR-01 | open items stay `open` in the sign-off |
| 3 | Log answers: `Q-ID · answer · [tag] · source` | AI | PR-02 | `docs/design/discovery.md` |
| 4 | Plan: 2–3 options per area, pillar impact (+/0/−), recommendation | AI drafts, tech lead decides | AI-01 | ADRs written as Proposed |
| 5 | Brainstorm: red-team as security, end user, admin, CFO | AI + team | PR-01 | findings → plan change or accepted risk |
| 6 | New gap found → back to step 2; else update `design-signoff.md` | AI | PR-01, G2 | `tools/gate_check.py --project .` |
| 7 | Approver signs (Status, Approved-by, Date) | approver | G2, AI-01 | AI never edits approval fields |

## Outputs
`docs/design/discovery.md` · `docs/design/design-signoff.md` · ADRs.
