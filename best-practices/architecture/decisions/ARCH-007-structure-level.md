# ARCH-007 — Structure level

Status: pending          <!-- pending | decided | n/a -->
Decided-by:
Date:
Choice:                  <!-- lean | standard | enterprise | keep-existing -->
ADR:

## Question
How much structure (layers, selectors, unit of work, interfaces) does this project's new code use?

## Why it matters
Too little structure makes a large, long-lived codebase hard to change safely; too much makes a small one slow to build and hard to read. Changing level later touches every new area.

## Project facts (AI fills from evaluation / discovery, with sources)
| Fact | Value | Source |
|---|---|---|
| Who maintains the code after delivery, and for how long | | discovery, contract |
| Team profile and devs per busy object | | guardrails.project.yaml |
| Structure already in the org (selectors, services, fflib, none) | | inventory |
| Busiest objects + automation density | | Execution Map |
| Integrations in core logic; LDV objects | | integration inventory, data model |
| Packaged / ISV | | ARCH-006, discovery |
| Expected lifetime of the solution | | discovery |

## Options
See `../structure-level.md` § Levels: Lean · Standard · Enterprise.

## AI proposal
<!-- Consistent existing structure → propose keep-existing.
     Otherwise propose one level with the two or three facts that decide it, and name what would change the proposal. -->

## Decision
The named human fills Status/Decided-by/Date/Choice and copies the choice to `guardrails.project.yaml → architecture.structure_level`. ARCH-001 (trigger framework) reads this choice as a signal but is decided separately.
