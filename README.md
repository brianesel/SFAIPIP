# SF AI development pipeline — v0.15

Guardrails, best practices and workflows for AI-assisted Salesforce development, from intake to production. Tool-neutral core (markdown, YAML, Python); Claude adapter included.

## Layout
| Folder | What |
|---|---|
| `guardrails/` | `registry.yaml` (every rule with an ID) · `README.md` (generated index) · `analyzer-map.yaml` (guardrail → verified Code Analyzer rules) · `rubric/` (scoring) · `schemas/` (ticket + test-case fields) |
| `best-practices/` | Well-Architected, clean Apex, testing, patterns + migration, requirements + tickets, AI-assisted development, **`build/`**: one guide per metadata area (Flows, Apex, permissions & access, objects & fields, validation rules & formulas, Lightning pages & UI, LWC, reports & dashboards, integration metadata, Agentforce), **`architecture/`**: trigger framework, API & integration, async, error handling + logging, data model / LDV, security + sharing, configuration, LWC data access, DevOps + packaging, with decision cards ARCH-001…006 |
| `workflow/` | `daily-guide.md` · `project-map.md` · `phases/00–07` (each step cites its guardrails) · `processes/` (change control, rituals, tracker setup) |
| `tools/` | init, status, gate check, **org guard (prod guard + sandbox lock + limit reserve) + `sf-safe`**, **org limits**, **rule map (analyzer rules)**, score, ticket lint, dev cycle, **pipeline orchestrator, context pack, impact diff, system map, recording converter, UAT runner**, weekly report, doc check |
| `templates/project/` | files copied into each project |
| `ci/` | GitHub Actions (PR gates incl. system map lint; `pipeline-run.yml` starts the pipeline from an issue label) + pre-commit |
| `calibration/` | tuning scores on known orgs |
| `.claude-plugin/`, `skills/`, `hooks/`, `agents/` | Claude adapter (agents = pipeline roles) |
| `tests/` | `python3 -m unittest discover tests` — pipeline end to end with a fake agent |
| `AGENTS.md` | rules for any AI tool |

## Install (Claude Code)
```
/plugin marketplace add <path-or-git-repo-of-this-package>
/plugin install sf-ai-dev-pipeline@sf-ai-dev-pipeline
```
Check everything: `python3 tools/doctor.py --project <project-dir>`

## Start
1. Read `workflow/daily-guide.md` (setup + routine).
2. `python3 tools/init_project.py <project-dir>`
3. In Claude: "where are we?" → `sfg-workflow` routes to the right phase.

## Status per phase
| Phase | Workflow | Automated checks |
|---|---|---|
| 00 Intake | ✅ | `status.py` (G0) |
| 01 Evaluation | ✅ | `score.py` (+ project config, waivers, history) · analyzer scripts ⏳ |
| 02 Discovery loop | ✅ | `gate_check.py` (G2) |
| 03 Alignment | ✅ | `status.py` (G1) |
| 04 Requirements | ✅ | `gate_check.py` (G2) |
| 05 Refinement | ✅ | `ticket_lint.py` (G3) |
| 06 Dev + test loop | ✅ | `dev_cycle.py` (G4), hook: tests before code · automated: `pipeline.py` (phases 1–3) |
| 07 Delivery | ✅ workflow | release scripts ⏳ (CI + human for G5 now) |

## Keep it consistent
After editing workflows or guardrails: `python3 tools/check_docs.py --write-index` — fails if a step cites no guardrail or a guardrail is missing from a phase it applies to.

## Requirements
Python 3.10+, PyYAML. Salesforce CLI + Code Analyzer v5 (Java 11+, Node 18+).
