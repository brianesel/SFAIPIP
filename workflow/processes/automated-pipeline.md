# Process — Automated agent pipeline (design, draft)

**Status:** draft for review, 2026-11-22. Nothing below is built yet. Owner: tech lead.

**Verdict:** a Python orchestrator script (`tools/pipeline.py`) drives a ticket from request to pull request through seven agents. The script owns the flow; Claude agents do the work inside each step. It reuses the 06 Dev + test loop, the gates and the hooks that already exist, and adds four things: recordings as a test source, separate tester roles with different access, an impact diff against a baseline, and an AI tech-lead review on every iteration. Every iteration is committed and pushed, failing ones included. Humans keep every approval: test set, impacts, waivers, escalations, the PR and Done (AI-01).

## 1. Goals and non-goals
| Goal | How |
|---|---|
| Ask everything relevant before building | intake agent asks gaps only, ≤ 4 questions per round, until the ticket passes G3 |
| Tests exist before code | agreed test set valid before production code (PR-08); hook already blocks force-app writes |
| Tests from written cases or a recording | recording converter writes `tester.yaml` |
| AI proposes extra cases, nothing written down until approved | new case status `proposed`; only `accepted` cases count |
| Prove the feature works and nothing else changed | functional, impact and UAT testers plus tech-lead review, every iteration |
| Full history, including bad attempts | commit + push every iteration on the ticket branch |
| Human approves the result | `gh pr create`; reviewer approves, merges and sets Done |

Non-goals: deploying to production (HG-09), changing acceptance criteria (PR-05, AI-05), running without a stop condition (PR-09, AI-04).

## 2. Flow
```
Request ─► Context pack (draft) ─► Intake agent ─► ticket Ready (G3) ─► Context pack (full)
        ─► Test source: tester.yaml (written)  or  recording ─► tester.yaml
        ─► AI cases, blind (ai.yaml) ─► align ─► HUMAN approves agreed.yaml  (proposed → accepted/rejected)
        ─► Characterization tests proposed ─► HUMAN accepts
        ─► Baseline run (before any code change) ─► baseline.yaml
        ┌► Dev agent implements ─► commit + push  "<KEY> iter-N …"
        │   ─► in parallel: functional-tester · impact-tester · uat-tester · tech-lead-reviewer
        │   ─► Verdict
        │        ├─ blocking finding or unapproved impact ─► findings to dev agent ─┘
        │        ├─ AC wrong / unclear ──────────────► change request, loop pauses (PR-05)
        │        ├─ loop guard fires ────────────────► stop, escalate to human tech lead (PR-09, AI-04)
        │        └─ all pass, no open blocking item ─► dod (G4)
        └──────────────────────────────────────────── ─► gh pr create ─► HUMAN review, merge, Done
```

## 3. Orchestrator
**Decision (2026-11-23):** the orchestrator is deterministic Python code, not an LLM following a skill. Approval points, the loop guard and the Done check must hold every time, so they are code, not instructions a model may skip.

| Aspect | Design |
|---|---|
| Entry points | `pipeline.py run <KEY>` (start or continue) · `pipeline.py status <KEY>` · `pipeline.py approve <KEY> <stop>` only records that a human-edited approval file exists; it never approves on its own |
| State | `docs/tests/<KEY>/pipeline.yaml`: current step, iteration, loop-guard counters, last verdict, waiting-on. Committed with each iteration, so state is in git |
| Calling agents | one agent per step, fresh context, run headless through Claude Code (`claude -p`) or the Claude Agent SDK, with the agent's tool list and org alias [med: exact CLI flags / SDK calls verified at build time] |
| After every agent step | the script checks the output with code: file exists, schema valid, `dev_cycle.py` / `ticket_lint.py` exit code. An agent saying "done" is not evidence |
| Approval points | the script writes what it is waiting for into `pipeline.yaml`, prints it, and exits. `run` again continues once the approval file is valid. Waiting costs nothing |
| Parallel checks | the four checkers run as parallel subprocesses; the verdict waits for all four |
| Loop guard | counters in `pipeline.yaml`; at the limit the script stops and escalates (PR-09, AI-04). No flag to bypass it |
| Git | the script commits and pushes each iteration and opens the PR (`gh pr create`). Prerequisite: `gh` CLI installed and authenticated [verified: not installed on the author's machine 2026-11-23] |
| Hooks | `org_guard.py` and `gate_check.py` stay in Claude Code hooks, so they fire inside every agent call [med: confirm hooks load in headless runs] |
| From chat | optional thin skill `sfg-pipeline` that only runs `pipeline.py` and shows its output |

**Alternatives considered:** LLM-driven skill (rejected: can skip steps or miscount); GitHub Spec Kit (its process duplicates ours and checks done by self-assessment; its workflow engine could run our steps, but adds a young dependency for what is a few hundred lines of code); LangGraph / Temporal (not needed while state lives in git files; revisit for many parallel unattended tickets).

## 4. Agents
Each agent runs with fresh context, its own tool list and its own org alias. Definitions live in `.claude/agents/<name>.md` [med: per-agent tool lists exist in Claude Code; per-agent hooks need checking against current docs before build].

| Agent | Job | Access | Never |
|---|---|---|---|
| `intake` | reads the context pack, turns the request into a Ready ticket | read repo + org metadata (read-only) | invent metadata names (AI-02) |
| `test-designer` | recording → `tester.yaml` draft; blind `ai.yaml`; alignment proposal; characterization tests for neighbouring components | read ticket, recording, force-app | open `tester.yaml` before `ai.yaml` is written (AI-03) |
| `developer` | implements, writes the agreed automated tests, commits | edit force-app, `sf` on dev sandbox via org guard | edit `agreed.yaml`, weaken tests, deploy outside verified sandboxes (HG-11) |
| `functional-tester` | runs Apex/Jest tests and Code Analyzer, executes agreed integration cases | `sf` on dev sandbox as admin-like user, read code | edit code under test, mark pass without evidence (AI-05) |
| `impact-tester` | diffs regression results and record snapshots against baseline | same as functional + baseline files | accept an impact |
| `uat-tester` | runs `level: uat` cases through the UI as a persona user | browser / Playwright only, persona login | run `sf`, read source code, use admin users |
| `tech-lead-reviewer` | reviews the iteration diff against guardrails, rubrics, patterns, build guides | read-only: Read, Grep, git diff, Code Analyzer output | edit code, grant waivers, approve the PR |

## 5. Steps
| # | Step | Who | Guardrails | How checked |
|---|---|---|---|---|
| 1 | Draft context pack from the request: likely area, related tickets in `docs/tickets/`, history export if any | orchestrator | PR-02, AI-02 | `context.md` written; every item sourced |
| 2 | Capture request; ask gaps (≤ 4 per round) until the ticket is Ready | intake agent, requester answers | PR-01, PR-02, AI-02, G3 | `tools/ticket_lint.py` |
| 3 | Full context pack from the Ready ticket's `metadata`: dependencies, same-object automation, field writers, git and audit history, covering tests | orchestrator | PR-02, AI-02, HG-11 | `context.md` complete; org reads only, writes blocked by org guard |
| 4 | Start: branch `feature/<KEY>`, scaffold `docs/tests/<KEY>/`, `pipeline.yaml` | orchestrator | G3, PR-08 | `dev_cycle.py start <KEY>` |
| 5 | Test source: written `tester.yaml`, or recording converted to a `tester.yaml` draft that the tester confirms | tester, test-designer | PR-08, AI-01 | schema `test-case-schema.yaml` |
| 6 | AI writes `ai.yaml` blind | test-designer | AI-03, AI-02 | separate files; skill rule |
| 7 | Align; AI-only and changed cases stay `proposed` until a human decides | test-designer proposes, tester + dev decide | PR-08, AI-01 | `dev_cycle.py align <KEY> --check` |
| 8 | Characterization tests for neighbouring components, `category: regression`, status `proposed` until accepted | test-designer proposes, tester + dev decide | PR-08, AI-01, AI-03 | `align <KEY> --check` |
| 9 | Baseline run before any code change: full local tests + accepted characterization tests + regression and UAT suites + record snapshot | functional + impact tester | HG-11, AI-05 | `baseline.yaml` committed |
| 10 | Implement per pattern and build guide; write agreed automated tests | developer | PR-06, HG-01, HG-02, HG-03, HG-06, HG-07, PR-10 | gate hook; review in step 12 |
| 11 | Commit + push the iteration, pass or fail | developer | PR-12 | commit message format, push succeeded |
| 12 | Parallel checks: functional, impact, UAT, tech-lead review | four agents | HG-04, HG-05, HG-10, HG-11, AI-05, PR-05 | `results/iter-N.yaml`, `impact/iter-N.yaml`, `review/iter-N.yaml` |
| 13 | Verdict: merge all findings, classify, route | orchestrator | PR-05, PR-09, AI-04 | `dev_cycle.py report <KEY>` |
| 14 | Loop guard: stop and escalate when it fires | orchestrator → human tech lead | PR-09, AI-04 | ⛔ in report |
| 15 | Update system map: regenerate the automation layer, propose feature and process updates for touched components | orchestrator + AI, human confirms written parts | AI-02, PR-12, AI-01 | `system_map.py lint --changed` |
| 16 | Done check | orchestrator | G4, HG-10, PR-12 | `dev_cycle.py dod <KEY>` |
| 17 | Open PR with evidence pack | orchestrator | AI-01, AI-06 | `gh pr create` |
| 18 | Human review, merge, set `reviewed_by`, `pr`, `status: done` | reviewer | G4, AI-01, AI-05 | AI never sets Done |

## 6. Human approval points
The pipeline stops and waits at each of these. Nothing continues on silence.

| Stop | Who decides | Record |
|---|---|---|
| Intake questions | requester / PM | ticket |
| Test set (incl. every `proposed` case) | tester + dev | `agreed.yaml` |
| Out-of-scope impact | human tech lead or PM | `impact-approvals.yaml` |
| Waiver for a hard rule finding | per PR-07 | `guardrails.project.yaml` waivers |
| Disputed tech-lead finding (after one rebuttal round) | human tech lead | `review/iter-N.yaml` |
| Loop guard | human tech lead + PM | `iterations.md` |
| AC wrong or unclear | change-request decider | CR ticket (`change-control.md`) |
| Pull request | reviewer | GitHub PR |

## 7. Context without ticket history
The pipeline must work when the historical ticket system is not reachable. Old tickets mainly explain why things are the way they are; the org and the repo show what exists and how it behaves, and the pipeline reads those directly.

**Context pack** (`docs/tests/<KEY>/context.md`, built by `tools/context_pack.py`, read by intake, test-designer, developer and tech-lead reviewer):

| Content | Source | Confidence |
|---|---|---|
| Map entries for the area: processes, features, tests, execution order, field writers | system map (`system-map.md`); live lookups below fill gaps | [high] where the map covers the area |
| Components that reference each touched component | Tooling API `MetadataComponentDependency` | [high] exists · [med] coverage of all metadata types |
| Flows, triggers, validation rules on the same objects, and which fields each writes | Execution Map from the evaluation phase, else retrieved metadata | [high] if evaluation ran |
| Recent setup changes in the area | Setup Audit Trail (about the last 180 days) | [high] |
| Why touched files changed | `git log` / `git blame` of touched files | [high] only if org source is already in git |
| Tests that cover touched components | existing Apex / Jest tests | [high] |
| Patterns and known constraints | `docs/wiki/pattern-register.md`, assessment wiki, ADRs | [high] |
| Related earlier tickets | `docs/tickets/`, plus a one-time history export under `docs/wiki/` if one exists | [high] |

The draft pack is built from the request; the full pack after the ticket is Ready, from its `metadata` list. Intake asks only what the pack cannot answer, for example "Flow X sets this field on close; is that still wanted?". All org access here is read-only.

**Characterization tests:** before any change, the test-designer proposes tests that pin down how neighbouring components behave today, without judging whether that behaviour is right. They fill the gaps in existing coverage so the impact diff has something to compare. They follow the proposed-case rule: nothing counts until the tester and dev accept it.

**Limit that stays:** the pipeline can detect that behaviour changed, but without the history it cannot tell whether the old behaviour was deliberate. That judgement stays with the human who approves impacts (AI-01).

**Building history from now on:** every ticket the pipeline runs lives in `docs/tickets/` with traceability to tests and release (PR-12), so the repo becomes the ticket history. A one-time export of the old system (CSV is enough) can be added under `docs/wiki/` whenever someone with access provides it.

## 8. Test sources and proposed cases
**Written:** tester writes `tester.yaml` as today.

**Recording:** `tools/recording_to_cases.py` (new) converts a recording into a `tester.yaml` draft, one case per recorded flow, steps as given/when, assertions as then.

| Format | Fit | Confidence |
|---|---|---|
| Chrome DevTools Recorder JSON export | structured steps and selectors; best default | [high] |
| Playwright codegen script or trace | structured; also replayable by the UAT tester | [high] |
| Screen video + narration | frames + transcript, AI interprets; tester must check every case | [med] |

A recording shows what was done, not always what was expected. The converter marks a `then` it inferred rather than saw asserted, and the tester confirms the draft before it counts as `tester.yaml`.

**Proposed cases:** schema change in `guardrails/schemas/test-case-schema.yaml`: `agreed_extra_fields.status` becomes `proposed | accepted | rejected`. `align --check` fails while any case is `proposed`. Testers and `dod` use only `accepted`.

## 9. Impact detection
| Layer | Method | Output |
|---|---|---|
| Behaviour | rerun the baseline set (incl. accepted characterization tests) each iteration; any case whose outcome changed is an impact | test flips |
| Data | run regression scenarios, snapshot touched records; compare field values outside the ticket's fields | unexpected field changes |
| Static | dependency lookup of every changed component (Tooling API `MetadataComponentDependency`) | components that may be affected [high: object exists; coverage of all types needs checking] |
| Scope | changed files vs ticket `metadata` list | out-of-ticket changes |

The impact tester uses the system map to choose what to re-run (component → features → their tests) and to name the business process each impact touches.

Each impact is classified as `in_scope` (explained by an AC), `approved` (entry in `impact-approvals.yaml`) or `unapproved`. Only `unapproved` blocks. Agents never write `impact-approvals.yaml` (AI-01).

## 10. Tech-lead review
Runs every iteration, read-only, fresh context, without the developer's reasoning.

| Check | Source | Blocking |
|---|---|---|
| Hard rules HG-01–HG-07 | `guardrails/registry.yaml` | yes |
| Code Analyzer severity 1–2 clean | HG-10, `code-analyzer.json` | yes (waiver only per PR-07) |
| Correct pattern for the area | PR-06, `docs/wiki/pattern-register.md` | yes |
| Build guide non-negotiables per touched type | `best-practices/build/*` | yes |
| Tests not weakened: assertions removed, cases skipped, `agreed.yaml` changed | HG-05, PR-08, AI-05 | yes |
| Tester evidence present for every pass | AI-05 | yes |
| Out-of-ticket changes not explained | PR-05 (cross-check with impact tester) | yes, unless approved |
| Every changed component mapped to a feature; generated map current | PR-12, AI-02, `system_map.py lint --changed` | yes |
| Simplicity: same AC and hard rules possible with clearly fewer classes, layers or lines; anything above the structure level (ARCH-007) without a second use or test seam | `clean-apex.md`, `structure-level.md`, `design.speculative_generality` | major, simpler alternative named |
| Comments that restate code; required why-comments missing (`SYSTEM_MODE`, `without sharing`, suppressions) | `clean-apex.md` § Comments, HG-01, HG-06 | minor; missing required why-comment is blocking |
| Touched code not worse | PR-10 | major |
| Clean-code rubric | `guardrails/rubric/code-design.yaml`, `tests.yaml` | minor |

Output `review/iter-N.yaml`, schema `guardrails/schemas/review-schema.yaml` (new): per finding `id, rule, file, line, severity, evidence, fix, status (open | fixed | disputed | waived)`. The developer may dispute once with a reason; unresolved disputes go to the human tech lead.

## 11. Verdict rules
| Condition | Route |
|---|---|
| Any agreed case of an AC fails | developer (code defect) or test-designer (test wrong; human decides) |
| Any `unapproved` impact | developer, or human for approval |
| Any open blocking review finding | developer |
| AC wrong or unclear | change request, loop pauses |
| Env or data problem | fix setup, rerun without counting a dev iteration |
| Same case fails 3 iterations, or same problem after 2 attempts | stop, escalate (PR-09, AI-04) |
| All accepted cases pass with evidence, no unapproved impact, no open blocking finding | `dod`, then PR |

## 12. Git and PR
- Branch `feature/<KEY>` from `main`. One commit per iteration, pushed right away.
- Commit message: `<KEY> iter-N: <pass>/<total> pass, <blocking> blocking [PASSING|FAILING]`. Results, impact and review files for that iteration go in the same commit, so each commit carries its own evidence.
- CI runs on the PR only (`ci/github-actions.yml` triggers on `pull_request`). Iteration pushes do not need CI to pass.
- Merge with a merge commit, not squash, so the failed attempts stay in `main` history.
- PR body: AC table with final status, iteration history (one line per commit), impact report and approvals, final tech-lead review, UAT evidence, waivers used.

## 13. Access model
- Org aliases per role in `guardrails.project.yaml`: `dev` (developer), `qa` (functional + impact), `uat_personas` (one alias or login per persona). All must be in `orgs.write_allowed` and verified sandboxes (HG-11); `org_guard.py` stays the only gate.
- UAT personas: sandbox users with exactly the target profile and permission sets. Credentials sit in the environment or a secret store and the browser session uses them; agents never type or print passwords.
- UAT tester is black-box: no source read, no `sf` CLI.

## 14. Files added or changed
| Path | Change |
|---|---|
| `tools/pipeline.py` | new orchestrator script (section 3) |
| `skills/sfg-pipeline/SKILL.md` | optional thin skill that runs `pipeline.py` from chat |
| `.claude/agents/*.md` | seven agent definitions |
| `tools/dev_cycle.py` | `baseline`, `import-impact`, `import-review`; `report` merges all; `dod` checks impacts + review |
| `tools/recording_to_cases.py` | new |
| `tools/context_pack.py` | new: builds `context.md` (section 7) |
| `tools/system_map.py`, `guardrails/schemas/system-map-schema.yaml` | new; see `system-map.md` |
| `guardrails/schemas/test-case-schema.yaml` | `proposed` status |
| `guardrails/schemas/review-schema.yaml`, `impact-schema.yaml` | new |
| `workflow/phases/06-dev.md` | add baseline, parallel checks, review steps |
| `docs/tests/<KEY>/` | `context.md`, `pipeline.yaml`, `baseline.yaml`, `impact/`, `review/`, `impact-approvals.yaml` |

## 15. Build phases
| Phase | Scope | Done when |
|---|---|---|
| 1 | `tools/pipeline.py`, context pack (repo sources + dependency API), agent definitions, `proposed` status, tech-lead review, commit-per-iteration, PR step | one example ticket runs end to end with functional tests only |
| 2 | baseline + impact diff, characterization tests, system map phases A–B, full context pack (Execution Map, audit trail), recording converter | an injected out-of-scope change is caught and blocks |
| 3 | UAT personas + Playwright; trigger `pipeline.py` from a GitHub Action | UAT cases run as a persona with evidence; pipeline runs from an issue label |

## 16. Open decisions
| # | Question | Default if not decided |
|---|---|---|
| 1 | Agent calls: `claude -p` subprocess or Claude Agent SDK | `claude -p` [med: fewer dependencies; switch to SDK if output parsing gets fragile] |
| 2 | Primary recording format | Chrome DevTools Recorder JSON |
| 3 | Who approves impacts: human tech lead, PM, or either | human tech lead |
| 4 | Persona credentials store | local env file outside the repo for phase 1–2; secret store for phase 3 |
