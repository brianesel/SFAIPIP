# ARCH-009 — Sandbox strategy

Status: pending          <!-- pending | decided -->
Decided-by:
Date:
Choice:                  <!-- keep-existing | lean | standard | governed -->
ADR:

## Question
Which sandboxes sit between development and production, of which type, and which of them may the AI write to?

## Project facts (AI fills, with sources)
| Fact | Value | Source |
|---|---|---|
| Edition and sandbox licences (Developer, Developer Pro, Partial Copy, Full) | | Setup → Sandboxes, contract |
| Existing sandboxes, their use and last refresh | | Setup → Sandboxes |
| Integrations needing a prod-like endpoint; LDV; performance tests | | integration inventory, data model |
| UAT personas and data needs (sample vs full copy) | | guardrails.project.yaml → uat |
| Compliance: data masking, segregation of duties | | discovery |

## Options
See `../branching-environments.md` § ARCH-009 Sandbox strategy.

## AI proposal
<!-- Existing chain works → keep-existing. Otherwise facts + signals only; the named human chooses (PR-15). -->
