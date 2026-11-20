---
name: sfg-change
description: Change control for Salesforce projects using SF AI development pipeline. Use whenever scope, a requirement, a priority, a deadline or a guardrail changes — "customer wants X instead", "new requirement", "can we add", "drop this feature", "move the date" — including mid-sprint requests. Creates a change request with impact analysis and routes the decision by size.
---

# sfg-change
> **Every step:** check the guardrails the workflow step cites (`${CLAUDE_PLUGIN_ROOT}/guardrails/README.md`). A failed hard rule or gate stops the step; report which ID failed.

Read `${CLAUDE_PLUGIN_ROOT}/workflow/processes/change-control.md`.

1. Draft `CR-nnn` from `docs/delivery/change-request.md`. Use `to-or-not-to-ticket` (type: Change request) if available.
2. Impact analysis: REQs, tickets, tests, ADRs, guardrails (override/waiver/targets), migration plan, effort range, date, risk. Tag every estimate.
3. Fill CR fields (`effort_days`, `scope_pct`, `design_change`, `guardrail_change`, `new_process`) and run `ticket_lint.py` — it checks size + decider against the routing rule. Do not decide yourself.
4. Mid-sprint: only critical (prod-down/legal) enters, with an equal-effort swap recorded.
5. After approval: bump requirements version, sign-off revision, traceability, re-run DoR on affected tickets. Large → back to phase 2 (and alignment if guardrails change).
6. Rejected/deferred CRs stay in the log with reason.
