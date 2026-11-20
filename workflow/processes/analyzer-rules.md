# Process — Analyzer rules from guardrails

**Purpose:** every guardrail that a scanner can check is checked by a rule that provably works. Built-in rules first; custom rules only for gaps.
**When:** evaluation (baseline coverage), alignment (project rules), after any analyzer upgrade or new project rule.

## Steps
| # | Step | Who | Guardrails | How checked |
|---|---|---|---|---|
| 1 | Inventory installed rules (PMD, ESLint, Flow, regex, CPD, SFGE, RetireJS) | AI | PR-14 | `tools/rule_map.py inventory` → `.sfg/rules-inventory.json` |
| 2 | Baseline mapping: guardrail → built-in rules (`guardrails/analyzer-map.yaml`), severities raised to block hard rules | AI | PR-14, HG-10 | `rule_map.py coverage` flags names not installed |
| 3 | Project rules: list intents in `guardrails.project.yaml → project_rules` (`enforce: analyzer \| review \| script`) | tech lead | PR-06, PR-14 | `coverage` lists each project rule |
| 4 | For each analyzer project rule: search the inventory for an existing rule first | AI | PR-14, AI-02 | cite the rule name from the inventory, never from memory |
| 5 | No existing rule → AI drafts a custom rule in `rules/custom-rules.yaml`: PMD XPath (Apex AST) or regex (any file, incl. `.flow-meta.xml`), with a bad and a good fixture | AI | PR-14, AI-01 | spec validation in `generate` / `test` |
| 6 | Generate config: custom PMD ruleset + regex rules + tag `Project` + severities | AI | PR-14 | `rule_map.py generate` → `code-analyzer.yml`, `rules/generated/` |
| 7 | Test: bad fixture must hit, good fixture must not | AI | PR-14, AI-05 | `rule_map.py test`; result tied to the spec hash (edit = retest) |
| 8 | Tech lead reviews rule + fixtures, sets `approved_by` | tech lead | AI-01 | `coverage` shows unapproved rules as gaps |
| 9 | Coverage report: no gaps for hard rules and analyzer project rules | AI | PR-14 | `rule_map.py coverage` exit 0 → `docs/wiki/_data/analyzer-coverage.md` |
| 10 | CI and dev loop scan with `--rule-selector Recommended --rule-selector Project --severity-threshold 2` | CI | HG-10 | `ci/github-actions.yml` |

## Notes
- Flow Scanner has a fixed rule set (no custom rules); Flow project rules use the regex engine on `.flow-meta.xml`.
- Cross-file rules (e.g. one trigger per object) cannot be analyzer rules; they are scored from the metadata inventory (`enforce: script`).
- Custom rules are rarely perfect: false positives go to triage (01-eval step 5); tune the spec, re-test, re-approve.
