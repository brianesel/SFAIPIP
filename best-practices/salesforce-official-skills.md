# Working with Salesforce's official skills and DX MCP server

**Verdict:** use Salesforce's official skills (`forcedotcom/sf-skills`) for *how to build* Salesforce artefacts, and this pipeline for *when, under which rules, and with which gates*. They fit together; where they disagree, this pipeline's guardrails win, and the hooks enforce that.
Checked against sf-skills (cloned 2026-11-20, 263 skills) and the Salesforce DX MCP server docs.

## Install alongside
```
npx skills add forcedotcom/sf-skills          # pick skills, or --all; commit skills-lock.json
```
The sf-skills README warns that skills change often and may be renamed or removed → treat `skills-lock.json` like the pipeline pin (PR-11): update deliberately, re-run the pipeline evals/smoke test after an update.

## Which official skill to use at which step
| Pipeline step | Official skill(s) | Pipeline adds |
|---|---|---|
| 01 Eval: inventory, drift | `dx-org-analyze`, `platform-metadata-retrieve`, `platform-soql-query` | read-only lock (HG-08), scoring vs pillar targets, wiki |
| 01/03 Analyzer rules | `dx-code-analyzer-run`, `dx-code-analyzer-configure`, `dx-code-analyzer-custom-rule-create`, `dx-apexguru-scan` | guardrail → rule map, bad/good fixture test, approval, coverage (`rule_map.py`) |
| 04 Design grounding | `platform-docs-get`, `platform-metadata-grounding-get`, `external-diagram-mermaid-generate` | decision cards, human choice (PR-15) |
| 06 Build Apex / triggers | `platform-apex-generate` (checks if Trigger Actions Framework is in use; service/selector/domain) | ARCH-001 decision, pattern register (PR-06), tests-before-code gate (PR-08) |
| 06 Tests | `platform-apex-test-generate`, `platform-apex-test-run` | tester + AI blind sets, alignment, iterations, DoD (G4) |
| 06 LWC | `experience-lwc-generate`, `experience-lds-best-practices-apply`, `experience-lds-graphql-generate`, `experience-lwc-security-validate`, `experience-lwc-accessibility-jest-run` | LWC data-access guide, ESLint gate |
| 06 Flow, objects, fields, permission sets | `automation-flow-generate`, `platform-custom-object-generate`, `platform-custom-field-generate`, `platform-permission-set-generate`, `platform-sharing-owd-configure` | ticket metadata check (AI-02), security guide |
| 06 Integrations | `integration-connectivity-generate`, `integration-eventing-cdc-configure` | per-interface inventory (ARCH-002) |
| 06 Debug | `platform-apex-logs-debug` | loop guard (PR-09) |
| 07 Delivery | `platform-metadata-deploy`, DevOps Center skills `dx-devops-*` (if ARCH-006 = DevOps Center) | G5, human runs production (HG-09) |

## Where they agree (no action)
One trigger per object with handler/TAF delegation · sharing keyword on every class · no SOQL in loops · TestDataFactory · Code Analyzer before "done" · ≥75% coverage · review generated code, verify field API names, test in a sandbox first.

## Where they differ — pipeline wins
| Topic | Official skill | Pipeline | Enforced by |
|---|---|---|---|
| Production deploy | `platform-metadata-deploy` lets the agent validate and quick-deploy to production | AI never deploys to production; a human runs the quick deploy (HG-09) | `org_guard.py` hook blocks `sf project deploy quick/start` and MCP deploys to production |
| Org classification | from `sf org list` (isSandbox, `--` in My Domain, test.salesforce.com) | `Organization.IsSandbox` query first, `sf org list` as fallback, fail closed; plus project allow-list | `org_guard.py` (HG-11) |
| Coverage bar | ≥75% (platform minimum) | per changed class ≥ `dev.class_coverage_min` (default 85) | `dev_cycle.py dod` |
| Test design | AI writes tests | tester + AI write blind, then align | `dev_cycle.py align` |
| Skill precedence | in Agentforce Vibes, Salesforce skills override project skills | in Claude Code, `AGENTS.md` + hooks take precedence over any skill text | hooks, AGENTS.md |

## Aligned from this review
- Bulk tests now use **251+ records** (crosses the 200-record trigger chunk), like `platform-apex-test-generate`.
- `org_guard.py` now also guards **MCP tools** (e.g. DX MCP `deploy_metadata`, `run_apex_test`, `assign_permission_set`) and uses `sf org list` as a fallback signal.

## Salesforce DX MCP server — safe configuration
- `--orgs` lists **only** write-allowed sandbox aliases (never `ALLOW_ALL_ORGS`, never the production alias). Salesforce itself recommends not giving the server all authorised orgs.
- Enable only the toolsets you use (the server has 60+ tools; all of them crowd the context).
- No `--allow-non-ga-tools` unless needed.
- The pipeline hook still checks every MCP write (target org = `usernameOrAlias`); a write without a resolvable sandbox target is blocked.
Template: `templates/project/.mcp.json`.
