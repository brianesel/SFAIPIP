# DevOps and packaging

**Verdict:** Git is the source of truth, every change moves through a pull request and the pipeline gates, and production gets only validated builds. *How* metadata moves (delivery model) is a human decision (ARCH-006): keep the existing model if it works; if none exists, ask.
Confidence: product facts [verified from Salesforce docs and vendor sources, 2026-11]; feature lists change — re-check before choosing.

## Non-negotiables (any model)
1. Version control is the source of truth; nothing is changed directly in production except documented emergency fixes, which are back-ported the same day.
2. Every change = ticket + branch + pull request + CI gates (ticket lint, DoD, Code Analyzer, validate deploy) — see `../../workflow/phases/06-dev.md` and `07-delivery.md`.
3. Environments: developer sandboxes or scratch orgs → integration/QA sandbox → UAT/staging (full or partial copy) → production. Only verified sandboxes are write-allowed for AI (HG-11). The project's branching and sandbox chain: ARCH-008/009 in `branching-environments.md`.
4. Production deploys only from a validated job (validate, then quick deploy), run by a human (HG-09).
5. Destructive changes are explicit, reviewed, and in the rollback plan (PR-13).
6. Manual post-deploy steps (activation, permission assignment, data) are listed in the release notes, scripted where possible.
7. Sandbox data: seed scripts; no production personal data in lower environments without masking.
8. One API version policy for the codebase, bumped deliberately (see v67.0 notes in `security-sharing.md`).

## Options (ARCH-006 delivery model)
| | A. DevOps Center | B. Source-driven with Git + Salesforce CLI + CI (this package's default tooling) | C. Unlocked packages (+ org-dependent variant) | D. Commercial DevOps tool |
|---|---|---|---|---|
| Idea | Salesforce's free change-set replacement: work items promoted through pipeline stages, Git managed behind a UI | developers/AI commit to Git; CI validates and deploys with `sf project deploy` | metadata grouped into versioned packages; Git is the source of truth; installable per org | vendor platform for compare, deploy, rollback, backups |
| Best for | admin-heavy teams moving off change sets | dev-heavy teams; works with this pipeline's scripts and gates directly | larger orgs wanting modular, versioned internal apps | many orgs, compliance, need for rollback/compare UI |
| Limits to know | Git providers limited (GitHub, Bitbucket); no rollback; work tracking inside DevOps Center | you own the scripts and CI | needs dependency design; untangling an existing "happy soup" org takes time; org-dependent packages ease the start | licence cost; vendor dependency |
| AI fit | AI works in Git branches; promotion in the UI | best: AI + gates in the same repo | good once package boundaries exist | depends on the tool's API/CLI |

**Package policy:** an existing model that works → keep-existing; none or change sets only → **always ask** (fill ARCH-006 with facts, no default). Moving off change sets is recommended in any case.

## Anti-patterns
Change sets as the long-term model · building in production · long-lived feature branches · CI that only runs on release day · untracked manual steps · copying production data with personal information into dev sandboxes.

## Sources
Salesforce DX Developer Guide — Unlocked Packages (incl. org-dependent); Salesforce Ben and Gearset articles on DevOps Center (2022–2026); this package's `ci/` and delivery workflow.
