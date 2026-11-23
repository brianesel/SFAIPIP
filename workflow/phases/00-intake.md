# Workflow 00 — Intake

**Purpose:** set up the project so every later step can check its guardrails.
**Entry:** a new or inherited Salesforce project. **Exit gate:** G0.

## Steps
| # | Step | Who | Guardrails | How checked |
|---|---|---|---|---|
| 1 | Create the project repo from templates | tech lead | PR-11 | `tools/init_project.py <dir>` writes the baseline pin; `tools/setup_project.py <dir>` (skill `sfg-setup`) also asks the project facts and logs in to the orgs |
| 2 | Pin the pipeline version (`baseline: sf-ai-dev-pipeline@x.y.z`) | tech lead | PR-11 | `tools/status.py` |
| 3 | Set team profile (solo · small · multi-team) and skills | PM + tech lead | G0 | `tools/status.py` |
| 4 | Name roles: approver, PM, tech lead, change board | PM | G0, AI-01 | `tools/status.py`; AI never fills the approver |
| 5 | Pick the path by measurement: existing org → 01 Eval; new/minimal org → 02 Discovery | tech lead | G0 | mode pick counts in 01-eval step 1 |

## Outputs
`guardrails.project.yaml` (baseline, path, team, roles) · `AGENTS.md` · `CLAUDE.md` · git pre-commit gate.
