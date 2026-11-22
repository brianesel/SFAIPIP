# Workflow

How work moves from intake to production. Every step names the guardrails it checks (IDs from `../guardrails/registry.yaml`); `tools/check_docs.py` fails if a step cites none.

| File | Use it for |
|---|---|
| `daily-guide.md` | setup, daily / weekly routine, who does what |
| `project-map.md` | the whole flow, gates G0–G5, which workflow when |
| `phases/00-intake.md` … `07-delivery.md` | step-by-step workflow per phase |
| `phases/discovery-question-bank.yaml` | must-decide questions (discovery, requirements) |
| `processes/change-control.md` | scope / requirement changes, any phase after G1 |
| `processes/rituals.md` | cadence: daily, weekly, sprint, release |
| `processes/tracker-setup.md` | markdown tickets or Jira fields, validators, automation |
| `processes/analyzer-rules.md` | map guardrails to analyzer rules; generate, test, approve custom rules |
| `processes/automated-pipeline.md` | design (draft): agent pipeline from request to PR, testers, tech-lead review, impact diff |
| `processes/system-map.md` | design (draft): living process, feature and automation map; search; kept current per ticket |
