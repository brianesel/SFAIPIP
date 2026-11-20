# Workflow 07 — Delivery (release to production)

**Purpose:** move Done work to production safely, verify it, and learn from it.
**Entry:** tickets at G4. **Exit gate:** G5 (release approved), then post-release checks.
Status: workflow defined; release scripts are a later version — checks below are CI + human for now.

## Steps
| # | Step | Who | Guardrails | How checked |
|---|---|---|---|---|
| 1 | Release scope = Done tickets only; list REQ/CR per ticket | PM | PR-12, PR-05 | traceability shows every ticket at G4 |
| 2 | Build the release from merged PRs, using the project's delivery model (ARCH-006) | dev + AI | PR-12, AI-01 | manifest / package version reviewed by tech lead |
| 3 | Full Code Analyzer on the release scope | AI | HG-01, HG-02, HG-03, HG-10 | 0 sev 1–2 (or valid waiver) |
| 4 | Validate deploy to staging/UAT with local tests | dev | HG-09, HG-11 | `sf project deploy validate --test-level RunLocalTests`; staging must be a verified write-allowed sandbox |
| 5 | UAT sign-off on release scope | customer approver | G5, AI-01 | signed UAT record |
| 6 | Rollback plan + pre-deploy snapshot (metadata + affected data) | dev | PR-13 | snapshot location in release notes |
| 7 | Change window approved (CAB / approver) | approver | G5 | approval recorded |
| 8 | Deploy to production with the validated job (quick deploy) | dev (human runs it, outside the AI session) | HG-09, AI-01 | `sf project deploy quick --job-id …`; `tools/org_guard.py` blocks it inside AI sessions |
| 9 | Post-deploy: activate Flows, assign permission sets, smoke tests | dev + tester | HG-09, AI-04 | smoke test results with evidence |
| 10 | Release notes + wiki + pattern register updated | AI drafts | AI-06, PR-12 | reviewed by PM |
| 11 | Hypercare: monitor errors, incidents → tickets | team | PR-05 | issues go through ticket/CR rules |
| 12 | Re-assess + ratchet thresholds; check waivers; baseline feedback | tech lead | PR-11 | `tools/score.py --config`, weekly report |

## Outputs
Release manifest · validated + deployed release · release notes · updated wiki · score trend.
