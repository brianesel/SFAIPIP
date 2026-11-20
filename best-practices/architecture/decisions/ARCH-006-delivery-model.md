# ARCH-006 — Delivery model (how metadata moves to production)

Status: pending          <!-- pending | decided -->
Decided-by:
Date:
Choice:                  <!-- keep-existing | A devops-center | B cli-ci | C unlocked-packages | D commercial-tool -->
ADR:

## Question
How do changes move from development to production?

## Project facts (AI fills, with sources)
| Fact | Value | Source |
|---|---|---|
| Current model (change sets, DevOps Center, CLI/CI, packages, tool) and how well it works | | interview / evaluation |
| Git provider (GitHub, Bitbucket, GitLab, Azure DevOps) | | discovery |
| Team mix (admins vs developers), team profile | | guardrails.project.yaml |
| Number of orgs, sandboxes available | | discovery |
| Compliance needs (audit trail, rollback, segregation of duties) | | discovery |
| Existing licences (e.g. a DevOps tool) | | discovery |

## Options
See `../devops-packaging.md` § Options.

## AI proposal
<!-- Existing model works → keep-existing. None / change sets only → no proposal: facts + trade-offs, ask the named human. -->
