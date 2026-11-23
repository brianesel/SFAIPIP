---
name: sfg-setup
description: Guided setup of a Salesforce project for the SF AI development pipeline — copies the project files, asks the project facts, the branching strategy and the sandbox strategy and fills guardrails.project.yaml, logs in to the orgs, and retrieves the baseline metadata read-only. Use when the user says "set up the project", "init the project", "new project", "onboard this org", "connect the org", "retrieve the metadata", or runs /sfg-setup. The manual alternative is the README "Start a project" steps.
---

# sfg-setup
> **Every step:** check the guardrails it cites (`${CLAUDE_PLUGIN_ROOT}/guardrails/README.md`). A failed hard rule stops the step; report which ID failed.

Same tool as the terminal (`tools/setup_project.py`); this skill only asks the questions in chat and runs it. Safe to rerun.

1. **Folder.** The project is the current folder. If it is not the Salesforce project's repo (no `sfdx-project.json`, no `.git`, not what the user meant), ask for the folder and use it as `<project>` below. If there is no `.git`, suggest `git init` first so the pre-commit gate is installed.
2. **Ask** (PR-01: only gaps, at most 4 questions per round; read `guardrails.project.yaml` first and offer filled values as defaults). Never invent aliases or names (AI-02).
   - Round 1: `path` (existing-org | new-org) · `team_profile` (solo | small | multi-team) · `devs` · `admins`
   - Round 2: `approver` (customer, signs G1/G2) · `pm` · `tech_lead`
   - Round 3: `source_alias` (org to retrieve the baseline from) · `source_kind` (production | sandbox) · `source_url` (My Domain URL, optional) · other `production` aliases
   - Round 4, the team's decision (ARCH-008/009; show the options and signals from `${CLAUDE_PLUGIN_ROOT}/best-practices/architecture/branching-environments.md`, never pick for them): `branching_strategy` (trunk | environment-branches | gitflow | keep-existing | pending) · `sandbox_strategy` (lean | standard | governed | keep-existing | pending) · `decided_by` (the named human who chose; required unless both are pending)
   - Round 5: `dev_aliases` · the stage aliases the sandbox strategy needs (`integration_alias`, `uat_alias`, `staging_alias`) · `write_allowed` (default: dev + integration; never UAT, staging or production) · `base_branch` (default from the branching strategy: trunk → main, environment-branches → integration, gitflow → develop)
   - Only if needed: extra `standard_objects` for the manifest.
   Record a strategy only as the user's own answer; "not sure" → `pending`. Do not ask for or set the other architecture decisions or approval (AI-01, PR-15).
3. **Write** the answers to `<project>/.sfg/setup-answers.yaml` (keys above; lists as YAML lists; no passwords or tokens) and run:
   `python3 ${CLAUDE_PLUGIN_ROOT}/tools/setup_project.py <project> --answers <project>/.sfg/setup-answers.yaml --no-login --no-retrieve`
   It stops with HG-08/HG-09 if a write-allowed alias is production or under evaluation, with HG-11 if it is a UAT or staging sandbox, and if a strategy has no named decider; ask the user to correct it.
4. **Log in.** For each alias the tool reports as not logged in, give the user the command and let them run it in their terminal, signing in in their browser:
   `sf org login web --alias <alias> --instance-url <https://login.salesforce.com | https://test.salesforce.com | My Domain URL>`
   Never type, ask for or store credentials. Continue when the user says it is done (`sf org display --target-org <alias>` succeeds).
5. **Retrieve** (read-only, HG-08, HG-12) only after the user agrees: run step 3's command without `--no-retrieve`. It checks the limit reserve, retrieves `manifest/baseline-package.xml` through `sf-safe`, and generates the automation map. Report types that refused `*` and propose listing them by name. If it prints "Retrieve skipped", show the user the listed problems and the manual commands it prints; do not work around them.
6. **Report:** what was filled (incl. the branch and sandbox chain in `delivery.environments` and the recorded ARCH-008/009 cards), which orgs are logged in, what was retrieved, the `doctor.py` result, and what is still for humans (architecture decision cards, UAT personas, approval). Next: `sfg-workflow` ("where are we?").

Installed from Claude Code's plugin copy, the project's `CLAUDE.md` and pre-commit hook point at that copy; for a stable path, run setup from a clone (README "Install").
