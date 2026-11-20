---
name: sfg-discover
description: Discovery → Planning → Brainstorm loop for Salesforce work, repeated until the design is signed off. Use whenever a new Salesforce project, new org, minimally customised org, new feature, object, automation, integration or agent is about to be built — even if the user just says "let's build X", "start the project", "new feature", "plan this". Asks all must-decide questions before any build; the build gate blocks force-app writes until sign-off.
---

# sfg-discover
> **Every step:** check the guardrails the workflow step cites (`${CLAUDE_PLUGIN_ROOT}/guardrails/README.md`). A failed hard rule or gate stops the step; report which ID failed.

Core rules: `${CLAUDE_PLUGIN_ROOT}/AGENTS.md`. Phase details: `${CLAUDE_PLUGIN_ROOT}/workflow/phases/02-discovery.md`. Read them first.

## Loop
1. **Discovery.** Load `workflow/phases/discovery-question-bank.yaml`. Keep questions whose `applies_when` matches. Read `docs/design/discovery.md` + notes; drop answered ones. Ask max 4 gaps per round (use tappable options where answers are choices). Log answers with confidence tag + source.
2. **Planning.** 2–3 options per must-decide area, each rated per pillar (+/0/−). Recommend one with the deciding reason. Write ADRs.
3. **Brainstorm.** Red-team from security, end user, admin, CFO views. Findings change the plan or become accepted risks.
4. New gap found → back to 1. Else update `docs/design/design-signoff.md` and ask the named approver to approve.
5. Check: `python3 ${CLAUDE_PLUGIN_ROOT}/tools/gate_check.py --project .` must print APPROVED before any build.

## Architecture choices
When the design touches triggers or integrations, read `${CLAUDE_PLUGIN_ROOT}/best-practices/architecture/` and fill the matching `docs/decisions/ARCH-*.md` card: project facts with sources, options, your proposal and the deciding fact. Present it and stop — a named human chooses (PR-15).

## Never
- Write to `force-app/` before sign-off (the hook blocks it; don't work around it).
- Mark an item decided on your own assumption. Assumptions stay `open` or `[med]`-tagged.
- Approve the sign-off yourself. Only the human approver edits Status/Approved-by.
