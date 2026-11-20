# Patterns and migration

## Current vs target pattern
| Layer | Rule |
|---|---|
| Hard gates (security, limits) | always the baseline; never copy a bad pattern |
| Structure inside an existing area | follow the current pattern (two paradigms on one object = unclear execution order) |
| Structure in a new, separable area | target pattern (strangler fig) |
| No pattern exists | target pattern for new code |
| Style | consistent locally |
Max two patterns per concern (legacy + target). Never a second trigger on an object.

## Target pattern fits the team
| Team | Target pattern | Review |
|---|---|---|
| 1–2 devs | trigger handler + service; no heavy frameworks | 1 independent AI review + async human |
| 3–6 devs | handler + service + selector; DI at external boundaries | 1 human + AI |
| 7+ / multi-team | full layering (fflib-style), module boundaries, coupling checks | 2 humans |

## Migration decisions
`priority = criticality × (target − score) × change_frequency / migration_effort`
`effort = components × base effort × risk (coverage < 75% ×1.5, no tests ×2, double-write ×1.3) × familiarity (×1.3 if new pattern)` — multipliers are defaults until calibrated.
| Decision | When |
|---|---|
| now | hard-gate risk, or hot area + low score |
| when touched | default |
| leave | stable, cost > value within ~12 months |
