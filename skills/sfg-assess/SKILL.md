---
name: sfg-assess
description: Read-only assessment of an existing Salesforce org or codebase, scored per aspect (automation, tests, code design / clean Apex, data model, naming, security, integrations, business flows) and per Well-Architected pillar against project targets, written up as a markdown wiki. Use whenever the user joins an existing project or org, asks to audit, evaluate, grade, score or health-check Salesforce code/metadata/flows, or wants a wiki/documentation of the current org — before planning any change.
---

# sfg-assess
> **Every step:** check the guardrails the workflow step cites (`${CLAUDE_PLUGIN_ROOT}/guardrails/README.md`). A failed hard rule or gate stops the step; report which ID failed.

Core rules: `${CLAUDE_PLUGIN_ROOT}/AGENTS.md`. Steps: `${CLAUDE_PLUGIN_ROOT}/workflow/phases/01-eval.md`. Read them first.

## Steps
1. Confirm target org alias is in `orgs.evaluation_readonly` (org guard blocks writes to it). No deploy, no data change.
1b. Analyzer rules: `tools/rule_map.py inventory` → `generate` → `coverage` (`workflow/processes/analyzer-rules.md`).
2. Mode pick (01-eval.md step 1). Minimal org → tell the user and switch to `sfg-discover`.
3. Retrieve → scan (Code Analyzer v5, check Python ≥3.10 first) → inventory → map business processes.
4. For each check in `guardrails/rubric/*.yaml`, write a result into `docs/wiki/_data/results.json` with evidence. No evidence → leave it out (not scored, never 0). Triage analyzer hits before counting them.
5. Judged checks: propose level 0/50/100 + reason from the anchors. Leave `approved_by` empty for the human.
6. Score: `python3 ${CLAUDE_PLUGIN_ROOT}/tools/score.py --results docs/wiki/_data/results.json --config guardrails.project.yaml --out docs/wiki/_data` (profile, targets, overrides, waivers from the project file; before alignment use `--profile <profile>`).
7. Write the wiki from `docs/wiki/index.md`: verdict first, one page per aspect and per business process (Mermaid flow), findings ranked by criticality × (target − score). Confidence tag on every claim. Neutral professional tone.
8. Report: org score, worst 3 pillar gaps, what is still not scored, what needs human approval.
