---
name: sfg-testgen
description: Generate the AI test case set for a Salesforce ticket blind to the tester's set, then align both into an agreed set. Use whenever a ticket is about to be implemented, or the user asks for test cases, test design, test scenarios, QA cases, "generate tests", "compare with the tester's cases", or "align test cases".
---

# sfg-testgen
> **Every step:** check the guardrails the workflow step cites (`${CLAUDE_PLUGIN_ROOT}/guardrails/README.md`). A failed hard rule or gate stops the step; report which ID failed.

Read `${CLAUDE_PLUGIN_ROOT}/workflow/phases/06-dev.md` §1 and `${CLAUDE_PLUGIN_ROOT}/guardrails/schemas/test-case-schema.yaml`.

## Generate (blind)
1. **Do not open `docs/tests/<KEY>/tester.yaml`** before `ai.yaml` is written. Independence is the point.
2. Inputs: the ticket (AC list = AC-1, AC-2 …, metadata, access, pattern, hard_gate_risk, migration_items), the pattern register, related code in force-app (read-only).
3. Per AC cover: happy + negative. Add per risk: bulk (trigger/flow, 251+ records to cross the 200-record chunk boundary), permission (access ≠ none, `System.runAs`), boundary, null_input (public methods), regression (migration items, touched shared code), integration (callouts → mock).
4. One behavior per case. Given/When/Then concrete (record counts, field values). Level: unit (logic via DI/stubs) or integration (DML, sharing, bulk). Automated cases name `Class.method`.
5. Write `ai.yaml` (ids A-01 …). Validate with `dev_cycle.py align <KEY>` once the tester's file exists.

## Align
1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/tools/dev_cycle.py align <KEY>` and show `alignment.md`.
2. For each tester-only / AI-only case propose accept or reject with a one-line reason. **The tester and dev decide**; you only propose.
3. After their decisions: `align <KEY> --check` must say ✅ valid.
