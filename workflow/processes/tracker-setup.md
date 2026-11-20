# Tracker setup

Two options. Pick one per project.

## A. Markdown tickets (any team, no tracker admin needed)
Tickets live in `docs/tickets/*.md` with YAML front matter (see `templates/project/docs/tickets/_EXAMPLE-*.md`).
- Lint: `python3 <pkg>/tools/ticket_lint.py --project .` (add `--org <alias>` to verify standard fields)
- CI runs the same lint on every PR (`ci/github-actions.yml`).
- Good for: small teams, AI-heavy work, projects without a customer tracker.

## B. Jira as system of record  [med: field/validator names differ per Jira edition, check your admin screens]
1. **Issue types**: Story, Task, Bug, Spike, Change Request (+ Epic).
2. **Custom fields** (names = schema fields, so mapping is 1:1):
   | Schema field | Jira field type |
   |---|---|
   | business_process | select list |
   | source, repeat_search, access, hard_gate_risk, migration_items | text (single line) |
   | req | text or issue links ("implements") |
   | acceptance_criteria | paragraph (one Given/When/Then per line, negative tagged `(negative)`) |
   | metadata | paragraph, one `type · name · state` per line |
   | pattern | select (current/target) + text (ADR id) |
   | test_tier, criticality, estimate | select list |
   | pillar_impact | 5 select lists (+/0/−) or one text `trust:+ reliability:0 …` |
   | cr_size, cr_decider | select list (CR only) |
   | effort_days, scope_pct | number (CR only) |
   | design_change, guardrail_change, new_process | checkbox (CR only) |
3. **Workflow**: Draft → Needs refinement → Ready → In progress → Done.
4. **Validators**: on Create require the `create` fields; on → Ready require the `ready` fields (Jira "field required" validator on the transition).
5. **Automation rules** (Jira Automation):
   - CR transitioned to Approved → transition linked issues to *Needs refinement* + comment "re-run DoR (CR-nnn)".
   - CR created → assign/notify the decider by `cr_decider`.
   - Issue moved to Ready while a linked CR is open → comment warning.
6. **Lint Jira tickets** (format + metadata names, which validators can't do): ask Claude (Atlassian connector) to export the sprint's Ready candidates into `docs/tickets/` front-matter files, then run `tools/ticket_lint.py`. Jira stays the source of truth; the files are a check copy.
