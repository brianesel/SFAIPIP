---
name: sfg-refine
description: Break approved Salesforce requirements into epics, stories and tasks with detailed specs and bring them to Definition of Ready. Use whenever the user wants to generate tickets, create the backlog, break down requirements, write specs, refine stories, plan a sprint or check if a ticket is ready — after design sign-off (G2).
---

# sfg-refine
> **Every step:** check the guardrails the workflow step cites (`${CLAUDE_PLUGIN_ROOT}/guardrails/README.md`). A failed hard rule or gate stops the step; report which ID failed.

Read `${CLAUDE_PLUGIN_ROOT}/workflow/phases/05-refinement.md`. Check G2 first with `status.py`; if not passed, stop and route to `sfg-workflow`.

1. Per REQ in `docs/design/requirements.md`: propose Epic → Stories → Tasks (one technical unit each). Show the breakdown before creating anything.
2. For every ticket create/update: if the `to-or-not-to-ticket` skill is available, use it (repeat search, challenge, template, explicit yes before writing). Otherwise follow the same rules from refinement.md and output paste-ready text.
3. Fill the spec per refinement.md "Spec content", using exact metadata names from the org and the pattern register.
4. Ticket fields follow `guardrails/schemas/ticket-schema.yaml` (front matter in `docs/tickets/*.md`, or Jira fields per `workflow/processes/tracker-setup.md`). Start from `docs/tickets/_EXAMPLE-*.md`.
5. Run `python3 ${CLAUDE_PLUGIN_ROOT}/tools/ticket_lint.py --project .` (add `--org <alias>` when available). Fix every ✗. A ticket is Ready (G3) only when lint says ✅ ready. Never mark `status: ready` to make it pass.
6. Update `docs/delivery/traceability.md` (REQ → tickets → tests).
7. Never put a ticket in a sprint that fails lint.
