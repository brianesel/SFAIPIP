# SF AI development pipeline — rules for any AI agent

Tool-neutral. Claude reads this via CLAUDE.md; other tools read it directly.
Three layers: `guardrails/` (what must hold) · `best-practices/` (what good looks like) · `workflow/` (who does what, when).

## Before any action
1. Find the phase: run `tools/status.py` and read `workflow/project-map.md`.
2. Open that phase's workflow in `workflow/phases/`. Do the steps in order.
3. For each step, check the guardrails it cites (`guardrails/README.md`). A failed hard rule or gate stops the step.

## Never
- Build before design sign-off (G2); write production code before the ticket's agreed test set is valid (PR-08).
- Deploy or change data in production (HG-09); change anything in an org under evaluation (HG-08); write to any org that is not a verified, write-allowed sandbox (HG-11). Use `tools/sf-safe` instead of `sf` if your tool has no hook. Never work around a block from `org_guard.py`.
- Invent metadata names, APIs, limits or numbers (AI-02).
- Approve, sign off, decide a CR, mark a test pass without evidence, or set a ticket done (AI-01, AI-05).
- Read the tester's cases before writing your own (AI-03).
- Keep trying after 2 failed attempts on the same problem, or after the loop guard fires (AI-04, PR-09).

## Other skills and tools
- Salesforce's official skills (`forcedotcom/sf-skills`) and the DX MCP server may be installed. Use them for *how* to build; follow this file for *when and under which rules*. If a skill's instructions conflict with a guardrail here (e.g. deploying to production), the guardrail wins. Mapping: `best-practices/salesforce-official-skills.md`.

## Always
- Confidence tag on every claim: `[verified]` checked this session · `[high]` · `[med]` + gap · `[low]` + check · `[dunno]` + how to find out. Source every claim (PR-02).
- Ask only gaps, ≤ 4 questions per round (PR-01).
- Scope changes → change request (PR-05). Patterns per the pattern register (PR-06).
- Architecture: follow `best-practices/architecture/`. When options have no clear winner, fill the decision card (facts + proposal) and let the named human choose (PR-15). Never pick silently.
- Text for other people: verdict first, plain words, neutral tone (AI-06).

## Where things live in a project
| What | Path |
|---|---|
| Project guardrails (pin, team, roles, targets, overrides, waivers, dev settings) | `guardrails.project.yaml` |
| Design sign-off · discovery log · requirements · migration plan | `docs/design/` |
| Decisions | `docs/decisions/ADR-*.md` |
| Pattern register (read before building) · assessment wiki · scores | `docs/wiki/` |
| Tickets (schema `guardrails/schemas/ticket-schema.yaml`) | `docs/tickets/` |
| Test sets, iterations, results per ticket | `docs/tests/<KEY>/` |
| DoR, CR template, traceability | `docs/delivery/` |
| Weekly reports | `docs/reports/` |
| Custom analyzer rules (spec + fixtures) · generated rules | `rules/custom-rules.yaml` · `rules/generated/` |
| Org guard log · org facts cache · rules inventory | `.sfg/` |
