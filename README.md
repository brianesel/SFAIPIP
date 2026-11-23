# SF AI development pipeline — v0.15

Guardrails, best practices, workflows and an automated agent pipeline for AI-assisted Salesforce development, from intake to production. Tool-neutral core (markdown, YAML, Python); Claude Code adapter included.

**What it gives you:** rules every AI tool follows (`AGENTS.md`, `guardrails/`), guidance on what good looks like (`best-practices/`), phase workflows with gates G0–G5 (`workflow/`), and `tools/pipeline.py`, which takes a request to a reviewed pull request with Claude agents: intake → agreed tests → dev loop with independent testers and a tech-lead review → PR. Humans approve every decision; machine checks stop unsafe actions.

## Layout
| Folder | What |
|---|---|
| `guardrails/` | `registry.yaml` (every rule with an ID) · `README.md` (generated index) · `analyzer-map.yaml` (guardrail → verified Code Analyzer rules) · `rubric/` (scoring, per structure level) · `schemas/` (ticket, test case, review, impact, system map) |
| `best-practices/` | Well-Architected, clean Apex (simplicity first, comment rule), testing, patterns + migration, requirements + tickets, AI-assisted development · **`build/`**: one guide per metadata area (Flows, Apex, access, objects & fields, validation rules & formulas, Lightning pages, LWC, reports, integration metadata, Agentforce) · **`architecture/`**: trigger framework, API & integration, async, error handling + logging, data model / LDV, security + sharing, configuration, LWC data access, DevOps + packaging, structure level, with decision cards ARCH-001…007 |
| `workflow/` | `daily-guide.md` · `project-map.md` · `phases/00–07` (each step cites its guardrails) · `processes/`: change control, rituals, tracker setup, analyzer rules, **automated pipeline**, **system map** |
| `tools/` | see [Tools](#tools) |
| `agents/` | pipeline roles: intake, test designer, developer, functional tester, impact tester, UAT tester, tech-lead reviewer |
| `templates/project/` | files copied into each project (`guardrails.project.yaml`, docs skeleton, decision cards) |
| `ci/` | `github-actions.yml` (PR gates) · `pipeline-run.yml` (optional: run the pipeline from a GitHub issue) · pre-commit |
| `.claude-plugin/`, `skills/`, `hooks/` | Claude Code adapter: skills per phase, hooks for the org guard and build gate |
| `tests/` | end-to-end pipeline tests with a fake agent, plus tool tests |
| `calibration/` | tuning scores on known orgs |
| `AGENTS.md` | rules for any AI tool |
| `CREDITS.md` | the books, frameworks, docs and people this package builds on |

## Where commands run
Two folders, used in every example below:
| Folder | What it is | Example |
|---|---|---|
| **package** | your clone of this repo (tools, guardrails, guides) | `~/sf-ai-dev-pipeline` |
| **project** | the Salesforce project's own git repo, where `sfdx-project.json` and `force-app/` live | `~/projects/acme-sf` |

Commands marked **Claude Code** are typed into a Claude Code session. Commands marked **terminal** run in a shell; the tools read the project from the current folder (or `--project <dir>`), so `cd` into the project first unless the step says otherwise.

## Install (Claude Code)
Once per machine.

1. **Claude Code, any folder** — add this repo as a plugin marketplace and install the plugin (format `plugin@marketplace`; both are named `sf-ai-dev-pipeline`):
   ```
   /plugin marketplace add brianesel/SFAIPIP
   /plugin install sf-ai-dev-pipeline@sf-ai-dev-pipeline
   ```
   Claude Code keeps its own copy; skills and hooks run the tools from there. That is enough if you only work inside Claude Code.
2. **Terminal, any folder** — clone the package if you run the tools from a terminal (the commands below) or want the project's pre-commit build gate. `init_project.py` writes the package path into the project's `CLAUDE.md` and pre-commit hook, so run it from a clone that stays put, not from Claude Code's plugin copy:
   ```bash
   git clone https://github.com/brianesel/SFAIPIP.git ~/sf-ai-dev-pipeline
   ```
   With a clone you can install the plugin from it instead (`/plugin marketplace add ~/sf-ai-dev-pipeline`), so plugin and tools are the same version.
3. **Terminal, any folder** — check the machine (Python, PyYAML, Salesforce CLI, Code Analyzer, …); every ❌ prints its fix:
   ```bash
   python3 ~/sf-ai-dev-pipeline/tools/doctor.py
   ```

What the plugin adds to every Claude Code session:
| Part | What it does |
|---|---|
| Skills `sfg-workflow`, `sfg-assess`, `sfg-discover`, `sfg-refine`, `sfg-testgen`, `sfg-dev`, `sfg-change`, `sfg-pipeline` | phase workflows; `sfg-workflow` finds the current phase and routes to the right one |
| Hook on shell and MCP calls | `org_guard.py`: blocks writes to production, orgs under evaluation and non-allowed orgs, and any org command below the limit reserve |
| Hook on file writes | `gate_check.py`: blocks writing `force-app/` before design sign-off or before the ticket's agreed test set is valid |

Other AI tools: skip the plugin, point the tool at `AGENTS.md`, and run `sf` through `~/sf-ai-dev-pipeline/tools/sf-safe`.

## Start a project
Once per project.

1. Read `workflow/daily-guide.md` in the package (setup + routine).
2. **Terminal, any folder** — copy the project files into the project (creates the folder if needed; never overwrites). Run `git init` in the project first if it is new, so the pre-commit gate is installed:
   ```bash
   python3 ~/sf-ai-dev-pipeline/tools/init_project.py ~/projects/acme-sf
   ```
3. **Editor, project folder** — fill `guardrails.project.yaml`: team profile, roles, orgs (`production`, `write_allowed` sandboxes), `orgs.limits`, architecture decisions incl. `structure_level` (ARCH-007), UAT personas.
4. **Terminal, project folder** — check the project setup:
   ```bash
   cd ~/projects/acme-sf
   python3 ~/sf-ai-dev-pipeline/tools/doctor.py --project .
   ```
5. **Terminal, project folder** — retrieve the baseline metadata (read-only) and build the automation map. The project must be a Salesforce DX project (`sfdx-project.json`; create one with `sf project generate` if it has none). First add the standard objects the org customises to `manifest/baseline-package.xml`.
   ```bash
   cd ~/projects/acme-sf
   python3 ~/sf-ai-dev-pipeline/tools/org_limits.py show <alias>
   sf project retrieve start --manifest manifest/baseline-package.xml --target-org <alias>
   python3 ~/sf-ai-dev-pipeline/tools/system_map.py generate
   ```
   Check the retrieve output for types that refused `*` and list those by name (`sf org list metadata --metadata-type <Type> --target-org <alias>`). Use `~/sf-ai-dev-pipeline/tools/sf-safe` instead of `sf` if your AI tool has no org-guard hook.
6. **Claude Code, started in the project folder** (`cd ~/projects/acme-sf && claude`) — ask "where are we?"; `sfg-workflow` routes to the right phase.

## Automated pipeline
Runs on your machine; GitHub only receives the pushed branch and the PR. Design: `workflow/processes/automated-pipeline.md`.

**Terminal, project folder** (or ask Claude Code, started in the project folder, to "run the pipeline for STORY-12"):
```bash
cd ~/projects/acme-sf
python3 ~/sf-ai-dev-pipeline/tools/pipeline.py run STORY-12 --request "Sales rep needs an invoice from a closed-won opportunity"
```

Run it again after each human step; `python3 ~/sf-ai-dev-pipeline/tools/pipeline.py status STORY-12` (same folder) shows where it stands. Exit codes: `0` PR open · `3` waiting for a human · `1` stopped (see `docs/tests/<KEY>/escalation.md` in the project).

| Stage | What happens | Human stop |
|---|---|---|
| Intake | context pack (related tickets, history, execution order, field writers, dependencies) → intake agent asks only the gaps, ≤ 4 per round, until the ticket is Ready (G3) | answer `questions.md` |
| Test design | AI writes `ai.yaml` without seeing the tester's set (AI-03); tester writes `tester.yaml`, or converts recordings with `recording_to_cases.py`; `align` merges into `agreed.yaml`, every case `proposed` | accept / reject cases in `agreed.yaml` |
| Characterization + baseline | AI proposes tests that pin down today's behaviour next to the ticket; iteration 0 writes them; the impact tester records all local tests + a record snapshot | accept / reject `characterization.yaml` |
| Dev loop | developer implements → functional tester, impact tester and tech-lead reviewer run in parallel → UAT tester runs uat cases as a persona user → verdict; **every iteration is committed and pushed, failing ones too** | approve impacts in `impact-approvals.yaml` (optional; unapproved impacts go back to the developer) |
| Stops | loop guard (same case failing 3 iterations, PR-09), no progress twice (AI-04), AC wrong (change request), org limits (HG-12), run budget | resolve `escalation.md` |
| PR | system map updated and linted → pre-PR Done check → `gh pr create` with evidence (tests, review, impacts, API usage, map diff) | review, merge, set the ticket Done |

Agents never approve, sign off, change acceptance criteria, mark a test pass without evidence or set a ticket Done (AI-01, AI-05). The orchestrator checks this in code, not only in prompts: test files the developer touches are reverted and escalated, checkers that change code are escalated, the tester's set is moved out of the tree while the AI writes its own.

Optional: `ci/pipeline-run.yml` runs the same pipeline from a GitHub issue (label `pipeline`, comment `/pipeline continue`).

## Safety guards
| Guard | What it stops | Where |
|---|---|---|
| Build gate | writing `force-app/` before design sign-off (G2) or before the ticket's agreed test set is valid (PR-08) | `gate_check.py` hook |
| Org guard | any write to production (HG-09), to an org under evaluation (HG-08), or to an org that is not a verified, write-allowed sandbox (HG-11) | `org_guard.py` hook · `sf-safe` for other tools |
| Limit reserve | any org command, reads included, when a daily limit (API requests, async Apex) falls below the reserve: 50 % default, 80 % production; unreadable limits are blocked (HG-12) | `org_guard.py` + `org_limits.py` |
| Run budget | a pipeline run using more org API requests than `orgs.limits.run_budget` | `pipeline.py` |

## Tools
| Tool | Use |
|---|---|
| `init_project.py`, `doctor.py`, `status.py` | start a project, check setup, gate status G0–G1 |
| `gate_check.py`, `ticket_lint.py`, `dev_cycle.py` | build gate (G2), ticket Ready (G3), dev loop and Done (G4) |
| `org_guard.py`, `sf-safe`, `org_limits.py` | prod guard, sandbox lock, limit reserve; `org_limits.py show <alias>` |
| `pipeline.py`, `context_pack.py` | orchestrator; what is known about a ticket's area |
| `impact.py` | baseline and per-iteration impact report; `check` for unapproved impacts |
| `system_map.py` | generate the automation map; `query writes / fires / used-by / tests / step / impact`; `search`; `lint --changed`; `questions` |
| `recording_to_cases.py` | Chrome DevTools Recorder / Playwright recordings → draft tester cases |
| `uat.py` | run Playwright specs as a persona (one-time login URL, never printed) and import results |
| `score.py`, `rule_map.py`, `weekly_report.py`, `check_docs.py` | assessment scoring, analyzer rule coverage, weekly report, workflow ↔ guardrail consistency |

## Status per phase
| Phase | Workflow | Automated checks |
|---|---|---|
| 00 Intake | ✅ | `status.py` (G0) |
| 01 Evaluation | ✅ | `score.py` (+ project config, structure level, waivers, history) · analyzer scripts ⏳ |
| 02 Discovery loop | ✅ | `gate_check.py` (G2) |
| 03 Alignment | ✅ | `status.py` (G1, incl. decision cards ARCH-001…007) |
| 04 Requirements | ✅ | `gate_check.py` (G2) |
| 05 Refinement | ✅ | `ticket_lint.py` (G3) |
| 06 Dev + test loop | ✅ | `dev_cycle.py` (G4), hooks · automated: `pipeline.py` |
| 07 Delivery | ✅ workflow | release scripts ⏳ (CI + human for G5 now) |

**Not yet proven on a real org:** the pipeline is tested end to end with a fake agent (`tests/`); the agent prompts still need tuning on the first real tickets. The Apex code graph (apex-ls) is audited but not integrated; the system map uses a text-reference scan for Apex.

## Keep it consistent
For changes to this package itself; **terminal, package folder** (`cd ~/sf-ai-dev-pipeline`).
- After editing workflows or guardrails: `python3 tools/check_docs.py --write-index` — fails if a step cites no guardrail or a guardrail is missing from a phase it applies to.
- Tests: `python3 -m unittest discover tests`

## Requirements
- Python 3.10+, PyYAML
- Salesforce CLI + Code Analyzer v5 (Java 11+, Node 18+)
- Pipeline: Claude Code CLI (`claude`), git with a remote, GitHub CLI (`gh`, signed in) for the PR
- UAT: Node + Playwright, persona users in the sandbox (`sf org login web --alias <persona-alias>`)

## Credits
Built on the work of Pablo Gonzalez (*Clean Apex Code*), Robert C. Martin (*Clean Code*), Martin Fowler, Kevin O'Hara, Mitch Spano, Andrew Fawcett and the Apex Enterprise Patterns community, Jonathan Gillespie, Salesforce's documentation and architect teams, and others. Full list: [`CREDITS.md`](CREDITS.md).
