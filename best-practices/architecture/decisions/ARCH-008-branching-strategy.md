# ARCH-008 — Branching strategy

Status: pending          <!-- pending | decided -->
Decided-by:
Date:
Choice:                  <!-- keep-existing | trunk | environment-branches | gitflow -->
ADR:

## Question
How do branches flow from a ticket to production, and which branch do pull requests target?

## Project facts (AI fills, with sources)
| Fact | Value | Source |
|---|---|---|
| Existing branches and how they are used | | `git branch -r`, interview |
| Delivery model (ARCH-006); DevOps Center requires environment branches | | guardrails.project.yaml |
| Team profile and number of people merging | | guardrails.project.yaml |
| Release rhythm (continuous, sprint, scheduled train); versions in flight | | discovery |
| Git provider and CI | | discovery |

## Options
See `../branching-environments.md` § ARCH-008 Branching strategy.

## AI proposal
<!-- Existing model works → keep-existing. Otherwise facts + signals only; the named human chooses (PR-15). -->
