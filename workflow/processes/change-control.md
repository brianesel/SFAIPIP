# Process — Change control (runs from G1 to the end)

Scope and requirements will change. Every change is visible, assessed and agreed.

## Steps
| # | Step | Who | Guardrails | How checked |
|---|---|---|---|---|
| 1 | Capture the change as a CR ticket, linked to affected REQ/tickets | AI drafts, PM confirms | PR-05, PR-04 | `tools/ticket_lint.py` (type cr) |
| 2 | Impact analysis: REQs, tickets, tests, ADRs, guardrails, migration plan, effort, date, risk | AI drafts | PR-02, PR-12 | template `docs/delivery/change-request.md` |
| 3 | Size + route by rule (small → PM+TL · medium → change board · large → approver) | AI | PR-05 | `ticket_lint.py` checks size/decider vs rule |
| 4 | Decide | named decider | AI-01 | AI never decides |
| 5 | Re-baseline: REQ version, sign-off revision, traceability, re-lint affected tickets | AI | PR-12, G3 | `ticket_lint.py` |
| 6 | Large or guardrail-changing CR → back to 04 Requirements (and 03 Alignment) | PM | G2, G1 | `tools/status.py` |

## Rules
- Mid-sprint: only critical changes (prod-down, legal), with an equal-effort swap recorded.
- Rejected or deferred CRs stay in the log with reason.
