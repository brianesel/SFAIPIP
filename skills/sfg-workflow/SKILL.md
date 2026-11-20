---
name: sfg-workflow
description: Entry point and router for the SF AI development pipeline (intake → evaluation or discovery → alignment → requirements + design → tickets/refinement → dev), with change control running throughout. Use whenever the user starts or resumes a Salesforce project, asks "where are we", "what's next", "which phase", "can we start building", or mentions project guardrails, migration plan, pattern register, alignment or gates G0–G3.
---

# sfg-workflow
> **Every step:** check the guardrails the workflow step cites (`${CLAUDE_PLUGIN_ROOT}/guardrails/README.md`). A failed hard rule or gate stops the step; report which ID failed.

Read `${CLAUDE_PLUGIN_ROOT}/workflow/project-map.md` and `${CLAUDE_PLUGIN_ROOT}/AGENTS.md`.

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/tools/status.py --project .` and report the first failing gate with its problems.
2. Route to the phase doc for that gate:
   - G0 → `workflow/phases/00-intake.md`
   - existing org, no scores yet → skill `sfg-assess`
   - new/minimal org → skill `sfg-discover`
   - G1 → `workflow/phases/03-alignment.md` (fill `guardrails.project.yaml`, migration plan, pattern register)
   - G2 → `workflow/phases/04-requirements.md` + `sfg-discover` design loop
   - G2 passed, tickets not Ready → skill `sfg-refine` (`workflow/phases/05-refinement.md`)
   - Ready ticket picked up → skill `sfg-dev` (`workflow/phases/06-dev.md`)
   - Done tickets to ship → `workflow/phases/07-delivery.md` (humans run production steps)
3. For a daily routine question ("what should I do today?") → `workflow/daily-guide.md`.
4. A scope or requirement change at any point → skill `sfg-change`.
5. Never mark a gate passed yourself. Approvals are made by the named human approver.
