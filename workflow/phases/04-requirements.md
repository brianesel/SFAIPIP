# Workflow 04 — Requirements discovery + design

**Purpose:** testable requirements, designed within the project guardrails.
**Entry:** G1. **Exit gate:** G2.

## Steps
| # | Step | Who | Guardrails | How checked |
|---|---|---|---|---|
| 1 | Collect needs per business process (workshops, docs, transcripts) | AI drafts, BA reviews | PR-02, AI-01 | each REQ has a source |
| 2 | Write `REQ-nnn` with Given/When/Then, MoSCoW, source | AI drafts | PR-02, AI-06 | `docs/design/requirements.md` |
| 3 | Ask must-decide gaps for this scope (≤ 4 per round) | AI | PR-01 | open items stay open |
| 4 | Design loop (plan + red team), each choice names its pattern and follows the architecture guides | AI + tech lead | PR-01, AI-01 | ADRs; `best-practices/architecture/` |
| 5 | New integration or automation-heavy scope → revisit ARCH cards; each interface gets an inventory row whose style a human decides | AI fills facts, human decides | PR-15 | card status; `docs/design/integration-inventory.md` (pending rows block G2 in `gate_check.py`) |
| 6 | Pull in "when touched" migration items the scope hits | AI | PR-01 | listed in sign-off |
| 7 | Freeze requirements version; later changes only via CR | PM | PR-05 | version log in requirements.md |
| 8 | Approver signs the design | approver | G2, AI-01 | `tools/gate_check.py`; hook blocks force-app until then |

## Outputs
Requirements v1.0 · design sign-off · ADRs.
