# ARCH-001 — Trigger framework

Status: pending          <!-- pending | decided | n/a -->
Decided-by:
Date:
Choice:                  <!-- A | B | C | D | keep-existing -->
ADR:

## Question
Which trigger framework does this project use for Apex trigger logic?

## Why it matters
Changing frameworks later means touching every trigger. The choice sets how bypass, ordering with Flows and recursion work for years.

## Project facts (AI fills from evaluation / discovery, with sources)
| Fact | Value | Source |
|---|---|---|
| Framework already in the org | | inventory |
| Busiest objects + automation density (quantity · volume · sprawl) | | Execution Map |
| Flows and Apex on the same objects? | | Execution Map |
| Team profile, admins building Flows? | | guardrails.project.yaml |
| Packaged / ISV app? | | discovery |

## Options
See `../trigger-framework.md` § Options: A minimal handler · B metadata-driven actions · C fflib domain layer · D in-house.

## AI proposal
<!-- Framework exists and is consistent → propose keep-existing.
     No framework yet → NO proposal: list the facts above and the trade-offs of A, B, C for this project, then ask the named human. -->

## Decision
The named human fills Status/Decided-by/Date/Choice and copies the choice to `guardrails.project.yaml → architecture.trigger_framework`.
