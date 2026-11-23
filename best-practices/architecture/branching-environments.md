# Branching and environments

**Verdict:** every project records two choices before G1: how branches flow (ARCH-008) and which sandboxes sit between development and production (ARCH-009). Both depend on the delivery model (ARCH-006), team size and sandbox licences, so a named human chooses (PR-15); `setup_project.py` / skill `sfg-setup` asks them. The result lives in `guardrails.project.yaml` (`architecture.branching_strategy`, `architecture.sandbox_strategy`, `delivery`) and in `docs/decisions/ARCH-008-*.md`, `ARCH-009-*.md`.
Confidence: sandbox and DevOps Center facts [verified, Salesforce Help release 264, 2026-11-23]; branching models [high, sources below].

## Non-negotiables (any choice)
1. One ticket = one short-lived branch `feature/<KEY>` from the branch PRs target (`dev.base_branch`), merged by pull request after the gates (`../../workflow/phases/06-dev.md`).
2. Production deploys only from the release branch or a release tag, validated first and run by a human (HG-09).
3. The AI writes only to development and integration sandboxes listed in `orgs.write_allowed` (HG-11). UAT, staging and production are deployed by humans or CI on a human's approval.
4. Hotfixes branch from what is in production and are merged back into every open line the same day (`devops-packaging.md` rule 1).
5. Each environment is listed once in `delivery.environments` with its alias, sandbox type and branch, in promotion order.

## ARCH-008 Branching strategy — options
| | A. Trunk-based | B. Environment branches | C. GitFlow-lite |
|---|---|---|---|
| Idea | short-lived feature branches merge into `main`; releases are tags on `main` | one long-lived branch per pipeline stage (`integration` → `uat` → `main`); changes are merged forward stage by stage | `develop` collects features; `release/*` branches stabilise a release; `main` = production; `hotfix/*` from `main` |
| PRs target (`dev.base_branch`) | `main` | first stage branch (`integration`) | `develop` |
| Fits | small teams, frequent releases, CLI/CI delivery (ARCH-006 B) | DevOps Center (ARCH-006 A), which works this way: each pipeline stage has a branch, feature branches start from the first stage branch and changes are merged into later stage branches as they are promoted [verified, Salesforce Help "Source Control Branches"] | scheduled releases with more than one version in flight, multi-team |
| Main risk | needs strong CI and feature toggles for unfinished work | stage branches drift when someone fixes a stage directly; cherry-picks | merge overhead; long-lived `develop` |

Signals to show the human (not a verdict): DevOps Center → B (its model); solo/small team with CI → A; scheduled release trains or parallel versions → C. Matches ARCH-007 loosely: lean → A, standard → A or B, enterprise → B or C.

## ARCH-009 Sandbox strategy — options
Stages after the developer's own sandbox, in promotion order:
| | A. Lean | B. Standard | C. Governed |
|---|---|---|---|
| Chain | dev → UAT → production | dev → integration → UAT → production | dev → integration → UAT → staging → production |
| Development | Developer sandbox per person | Developer sandbox per person | Developer sandbox per person (or per team) |
| Integration / QA | — | Developer Pro | Developer Pro |
| UAT | Partial Copy (or Developer Pro) | Partial Copy | Partial Copy |
| Staging (prod-like validate, performance) | — | — | Full |
| Fits | solo/small, low change volume | most projects | regulated, integrations or LDV, release trains |

Sandbox facts that decide what is possible [verified, Salesforce Help release 264]:
- Refresh intervals: Developer 1 day, Developer Pro 1 day, Partial Copy 5 days, Full 29 days ("Refresh Your Sandbox").
- Developer and Developer Pro copy metadata only; Partial Copy adds a data sample defined by a sandbox template; only Full sandboxes support performance testing, load testing and staging ("Sandbox Types and Templates").
- Included licences differ by edition: Enterprise Edition includes 25 Developer and 1 Partial Copy sandbox and no Developer Pro or Full; Unlimited and Performance include 100 Developer, 5 Developer Pro, 1 Partial Copy and 1 Full ("Sandbox Licenses and Storage Limits by Type"). Check the org's licences before choosing C.
- DevOps Center development environments are source-tracked Developer or Developer Pro sandboxes, one per team member; pipeline stages use sandboxes such as integration, UAT and staging ("Lifecycle Center Environments").

## Branch per stage (written to `delivery.environments` by setup)
| Stage | A. Trunk-based | B. Environment branches | C. GitFlow-lite |
|---|---|---|---|
| dev | `feature/<KEY>` | `feature/<KEY>` | `feature/<KEY>` |
| integration | `main` | `integration` | `develop` |
| uat | release tag on `main` | `uat` | `release/*` |
| staging | release tag on `main` | `staging` | `release/*` |
| production | release tag on `main` | `main` | `main` |

## Anti-patterns
Long-lived feature branches · fixing a stage branch or sandbox directly without merging back · developing in the UAT or Full sandbox · a sandbox chain the licences don't cover · AI write access to UAT, staging or production · production personal data in development sandboxes without masking.

## How it is checked
`status.py` G1: `architecture.branching_strategy` and `sandbox_strategy` not pending. `org_guard.py`: AI writes only to `orgs.write_allowed`. `pipeline.py`: branches `feature/<KEY>` from `dev.base_branch` and opens the PR against it.

## Sources
- Salesforce Help (release 264): "Refresh Your Sandbox" — https://help.salesforce.com/s/articleView?id=platform.data_sandbox_refresh.htm&type=5; "Sandbox Types and Templates" — https://help.salesforce.com/s/articleView?id=platform.create_test_instance.htm&type=5; "Sandbox Licenses and Storage Limits by Type" — https://help.salesforce.com/s/articleView?id=platform.data_sandbox_environments.htm&type=5
- Salesforce Help (release 264), DevOps Center (shown as Lifecycle Center): "Source Control Branches" — https://help.salesforce.com/s/articleView?id=platform.devops_center_basics_source_control_branches.htm&type=5; "Plan Your Pipeline" — https://help.salesforce.com/s/articleView?id=platform.devops_center_pipeline_plan.htm&type=5; "Lifecycle Center Environments" — https://help.salesforce.com/s/articleView?id=platform.devops_center_environments_overview.htm&type=5
- Trunk-based development — trunkbaseddevelopment.com (Paul Hammant)
- GitFlow — "A successful Git branching model" (Vincent Driessen, 2010), nvie.com
