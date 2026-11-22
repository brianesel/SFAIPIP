# Structure level

**Verdict:** how many layers and seams the code gets is a project decision, not a per-ticket habit. Three levels: **Lean**, **Standard**, **Enterprise**. The level follows from who maintains the code over its life, automation density, lifetime, integrations and data volume, and packaging, not from today's team size alone. A named human picks it on decision card ARCH-007; the AI fills the facts and may propose (PR-15). Within the level, the simplest option wins (`../clean-apex.md`). Hard rules apply at every level.
Confidence: level contents [med] (our synthesis of common Salesforce practice; tune per project); drivers [high].

## Non-negotiables (any level)
| # | Rule | Checked by |
|---|---|---|
| 1 | Hard rules hold: bulk-safe, CRUD/FLS, sharing declared, no hardcoded IDs or secrets, one trigger per object | HG-01–HG-07; Code Analyzer; tech-lead review |
| 2 | Code goes where the level says; mixing levels in new code needs an ADR | PR-06; tech-lead review |
| 3 | Nothing above the level without a reason: no interface, selector, unit of work or setting the level does not call for, unless a second real use or a test seam needs it | `design.speculative_generality`; tech-lead review |
| 4 | Changing level is an ADR plus a change request; the pattern register marks the new level as target for new areas | PR-05, PR-06, PR-15 |

## Levels
| | **Lean** | **Standard** | **Enterprise** |
|---|---|---|---|
| Typical fit | solo / small team, low–medium automation density, few integrations | small or growing team, busy objects, several integrations, handover expected | multi-team, ISV / packaged, existing fflib codebase |
| Trigger (ARCH-001 signal, not the decision) | minimal handler (A) | handler with metadata bypass (A or B) | domain layer (C) |
| SOQL | in the service; moves to a selector when a second class needs the same query | selectors for shared or busy objects | selectors for all objects |
| DML | in the service | in the service; unit of work where several objects are written together | unit of work |
| Interfaces / DI | callouts and true test seams only (Stub API, `@TestVisible`) | callouts, time, user context, selectors on busy objects | all data access and external systems |
| Service layer | one service per business capability when logic is shared | services per capability | services + domain + selectors |
| Rubric effect | `design.layering`, `design.di_seams` use Lean targets | default targets | full targets |

## Drivers (AI fills these on the card, with sources)
| Driver | Pushes towards more structure when | Source |
|---|---|---|
| Who maintains it over its life | handover to a customer team or another partner; several maintainers | discovery, contract |
| Team now | `team_profile: multi-team`; several devs per object | `guardrails.project.yaml` |
| Automation density | several automations per object, batch / integration volume, cascades into ~5+ related objects | Execution Map (01) |
| Expected lifetime | core process for years, not a short campaign | discovery |
| Integrations and data volume | callouts in core logic; LDV objects | integration inventory, `data-model-ldv.md` |
| Packaging | managed / unlocked package, ISV | ARCH-006 |
| AI-written share | most code written by agents: consistent, predictable placement helps agents and reviewers; argues for at least Lean done consistently, not for more layers | team practice |

## Package policy
| Project facts | What happens |
|---|---|
| Existing org with a consistent structure | propose the level that matches it (keep-existing, PR-06); human confirms |
| Existing org, inconsistent | show the facts; propose a level for new areas plus migration items; human decides |
| New org | AI proposes a level from the drivers, with reasons; human decides |

## Anti-patterns
fflib and full layering on a solo, low-density project · interfaces with one implementation that is not a test seam · a selector class per object "for consistency" on Lean · no structure at all on a multi-team project · changing level ticket by ticket · using the level to excuse a hard-rule breach.

## How it is checked
Card ARCH-007 decided before G1 (`tools/status.py` blocks a pending `architecture.structure_level`) · `tools/score.py` applies the level's rubric targets · tech-lead review checks placement and over-building per ticket.
