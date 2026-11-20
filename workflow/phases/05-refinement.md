# Workflow 05 — Ticket generation + refinement

**Purpose:** tickets a developer (human or AI) can build without asking.
**Entry:** G2. **Exit gate:** G3 per ticket.

## Steps
| # | Step | Who | Guardrails | How checked |
|---|---|---|---|---|
| 1 | Break REQs into Epic → Story → Task; show before creating | AI drafts, team agrees | AI-01 | breakdown reviewed in refinement |
| 2 | Repeat search + impact sweep per ticket; repeats are updated | AI | PR-04 | `repeat_search` field; `tools/ticket_lint.py` |
| 3 | Fill required fields per schema (start from `_EXAMPLE-*`) | AI drafts | PR-02, AI-06 | `guardrails/schemas/ticket-schema.yaml` |
| 4 | Name exact metadata; mark existing/new | AI | AI-02 | `ticket_lint.py` checks source (+ `--org`) |
| 5 | State pattern (current/target + ADR) | AI + tech lead | PR-06 | ADR must exist |
| 6 | Link REQ / CR, migration items, dependencies | AI | PR-12, PR-10 | links must resolve |
| 7 | Changes to approved tickets go through a CR | PM | PR-05 | workflow `processes/change-control.md` |
| 8 | Lint to Ready; refinement meeting confirms | team | G3 | `ticket_lint.py` says ✅ ready |

## Outputs
Ready tickets · `docs/delivery/traceability.md` rows.
