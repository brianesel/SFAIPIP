---
name: sfg-dev
description: Implement a Salesforce ticket in the guarded loop implement → test → feedback until all acceptance criteria pass, then check Definition of Done. Use whenever the user asks to build, implement, code, develop, fix or continue a ticket, run tests, check results, "next iteration", "is it done", or "DoD" — only after tickets are Ready (G3).
---

# sfg-dev
> **Every step:** check the guardrails the workflow step cites (`${CLAUDE_PLUGIN_ROOT}/guardrails/README.md`). A failed hard rule or gate stops the step; report which ID failed.

Read `${CLAUDE_PLUGIN_ROOT}/workflow/phases/06-dev.md`, the ticket, `docs/wiki/pattern-register.md`, and `guardrails.project.yaml`.

1. **Start**: `python3 ${CLAUDE_PLUGIN_ROOT}/tools/dev_cycle.py start <KEY>`. Not ✅ → stop, report why.
2. **Test design first**: skill `sfg-testgen`. No production code before `align <KEY> --check` passes (the hook enforces it when `dev.require_agreed_tests: true`).
3. **Implement**: follow the ticket `pattern` (current vs target per pattern register). Hard gates always: bulk-safe, CRUD/FLS (`WITH USER_MODE`), no hardcoded IDs, sharing declared. Write the automated tests named in `agreed.yaml`. Minimal diff; boy scout only inside touched methods.
4. **Test**: run in a write-allowed, verified sandbox (the org guard blocks anything else; never work around it): `sf apex run test --class-names <TestClasses> --code-coverage --result-format json --output-dir .sfg/run --target-org <sandbox>`, then `dev_cycle.py import-apex <KEY> --file <json>`. Run Code Analyzer on changed files → `docs/tests/<KEY>/code-analyzer.json`. Ask the tester for manual/UAT results.
5. **Feedback**: `dev_cycle.py report <KEY>`. Classify each failure: code defect → fix code · test wrong → propose change, tester + dev agree · AC wrong/unclear → `sfg-change`, stop the loop · env/data → fix setup.
6. **Loop guard**: ⛔ in the report (same case failing 3 iterations) → stop, summarize attempts + key error, ask tech lead + PM. Do not keep trying.
7. **Done**: `dev_cycle.py dod <KEY>`. Remaining human steps: PR review, then `reviewed_by`, `pr`, `status: done` set by the reviewer, traceability row.

Never: change acceptance criteria, mark cases pass without evidence, deploy to production, or set `status: done` yourself.
