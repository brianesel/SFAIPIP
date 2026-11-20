# Well-Architected

- Salesforce Well-Architected now has **five pillars**: Trust, Reliability, Operational Excellence, Resource and Cost Optimization, Fairness, plus an Agentic Enterprise lens. The older Trusted / Easy / Adaptable model is legacy.
- **Score against targets, not 100.** Pillars trade off (more reliability costs more; stronger controls add complexity). Each project sets targets per pillar in discovery (profiles in `../guardrails/rubric/pillars.yaml`).
- **One primary pillar per check.** Every rubric check is tagged once, so it shows in both the aspect view (what to fix) and the pillar view (what kind of risk).
- **Fairness is N/A** with no UI, customer-facing output or agents; add accessibility and explainability checks when it applies.
- **Agents meet the same bar** as any solution, plus agent-specific checks (action approval, data access during reasoning, escalation path).
- Hard gates (HG-01…HG-10) are the non-negotiable part of the Trust and Reliability pillars.
