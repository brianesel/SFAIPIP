# Daily guide

## 1. One-time setup (≈ half a day)
1. Put this package in a company git repo; tag versions. Projects pin one (`baseline: sf-ai-dev-pipeline@x.y.z`).
2. Per machine: Python 3.10+, `pip install pyyaml`, Salesforce CLI, `sf plugins install code-analyzer`, Java 11+, Node 18+, Claude Code (`npm install -g @anthropic-ai/claude-code`).
3. Claude Code: `/plugin marketplace add <package path or git repo>` → `/plugin install sf-ai-dev-pipeline@sf-ai-dev-pipeline` → restart the session.
4. `python3 <pkg>/tools/doctor.py` — all machine checks ✅.
5. Smoke test in a scratch project: (a) ask Claude to write a file in `force-app/` → blocked by the build gate; (b) ask it to run `sf project deploy start -o <prod alias>` → blocked by the org guard.
6. Tracker: markdown tickets first; Jira later (`processes/tracker-setup.md`).
7. CI: copy `../ci/github-actions.yml` into project repos.
8. Calibrate scoring on 2 orgs you know (`../calibration/README.md`).

## 2. Every day
| Who | Start of day | During the day |
|---|---|---|
| Everyone | `tools/status.py` or ask Claude "where are we?" | scope changes → "new change request" (never edit approved tickets) |
| PM / BA | open CRs, failing tickets | meeting notes → Claude drafts REQs / CR candidates → review → lint |
| Tech lead | escalations (⛔ loop guard) | pattern questions → pattern register; approve judged scores |
| Tester | tickets entering dev | write `tester.yaml` before seeing the AI set; record manual results with evidence |
| Dev | own active ticket: `dev_cycle.py report <KEY>` | only Ready tickets; tests agreed before code |
| Claude | — | drafts, runs checks, flags; never approves, never deploys to prod |

## 3. Per ticket (dev loop)
`dev_cycle.py start <KEY>` → tester + AI cases (blind) → `align` → decide → `align --check` → implement → run tests → `import-apex` → `report` → repeat → `dod` → PR review.

## 4. Weekly, sprint, release
See `processes/rituals.md`. Monday: `tools/weekly_report.py` drives refinement and CR triage.

## 5. Commands
| Command | When |
|---|---|
| `tools/doctor.py [--project <dir>]` | setup check, any time something seems off |
| `tools/setup_project.py <dir>` (or skill `sfg-setup`) | new project, guided: facts, org login, baseline retrieve |
| `tools/init_project.py <dir>` | new project, copy files only |
| `tools/status.py` | anytime: gates G0–G2 |
| `tools/score.py --results … --config guardrails.project.yaml --out docs/wiki/_data` | evaluation, re-assess |
| `tools/ticket_lint.py [--org <alias>]` | writing tickets, before refinement (G3) |
| `tools/dev_cycle.py start / align / import-apex / report / dod <KEY>` | dev loop (G4) |
| `tools/weekly_report.py` | Monday |
| `tools/check_docs.py` | after editing this package's workflows or guardrails |
| `tools/org_guard.py verify <alias>` | before adding an org to `orgs.write_allowed` |
| `tools/sf-safe <sf args>` | AI tools without hooks: guarded `sf` |
| `tools/rule_map.py inventory / generate / test / coverage` | evaluation, alignment, new project rule, analyzer upgrade |
