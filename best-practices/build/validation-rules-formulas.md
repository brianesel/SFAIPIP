# Validation rules and formulas

**Verdict:** a validation rule is a business rule that blocks saves for every channel (UI, API, data loads, integrations), so build it like code: one condition per rule, a bypass check, an error message that tells the user how to fix the record, shown on the field they must change, and fired only on the change that matters. Formula fields are read-time calculations: keep them simple, don't hide business logic or security in them, and store the value instead when it must be indexed, reported over history or trigger automation. Native roll-ups only on master-detail; any other roll-up is an automation decision.
Sources: see end. Confidence: non-negotiables [high]; numbers marked inline; analyzer rule names [verified] against the Code Analyzer v5 inventory (719 rules) on 2026-11-20.

## Scope
Validation rules, formula fields, default value formulas, roll-up summary fields and their alternatives, cross-object formulas. Formulas inside Flows are in `flows.md`; field types and relationships in `objects-fields.md`; who can see a field in `permissions-access.md`.

## Non-negotiables
| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | **Every validation rule reads the project's standard bypass** (the same Custom Permission or Custom Metadata switch that Apex and Flows use), e.g. `AND(NOT($Permission.<ProjectBypassPermission>), <condition>)` with the project's real permission name | data loads, migrations and incident fixes must be able to save records without editing metadata | review; bypass test; `trigger-framework.md` rule 4 |
| 2 | **Fire on the change that matters.** Use `ISNEW()`, `ISCHANGED()` and `PRIORVALUE()` so a rule added today doesn't block unrelated edits of old records that never met it | a new rule on existing data otherwise blocks every save of every legacy record, including integration updates | review; test on a copy of production-like data |
| 3 | **The error message says what is wrong and how to fix it**, in the users' language, and stays within 255 characters [high, sf-skills `platform-validation-rule-generate`]. Show it on the field the user must change (`errorDisplayField`); use the top of the page only when several fields are involved | "Invalid data" makes users open a ticket; a message on the wrong field hides the fix | review; UAT |
| 4 | **No hard-coded IDs, user names or profile names.** Use `$RecordType.DeveloperName`, `$Permission.<name>` or Custom Metadata, never a record type Id or a profile name in the formula | IDs differ per org; profile names change and are not how access is granted (`permissions-access.md`) | HG-03; review |
| 5 | **Picklists through `ISPICKVAL()` or `TEXT()`**; `CASE()` always has its default value (even number of arguments) [high, sf-skills `platform-validation-rule-generate`] | direct picklist comparison does not compile; a missing CASE default fails silently in odd cases | deploy validation; review |
| 6 | **Right layer for the rule.** Single-record rule a user can fix on the screen → validation rule. Rule that needs other records, queries or bulk context → before-save Apex `addError()` or a Flow error in the before-save path of the agreed automation (ARCH-001) | validation rules see the record and its parents only; a cross-record check in a formula gets slow and brittle | PR-06; `flows.md`; `apex.md` |
| 7 | **Know the save order.** Custom validation rules run after before-save Flows and before-triggers, and before the record is saved [high, Apex Developer Guide "Triggers and Order of Execution"]. A value set by a before-save Flow is validated; an after-save update of the same record starts another save that runs the rules again [med: check the order-of-execution page for each automation type] | rules that "don't fire" or "fire twice" are usually ordering problems, not formula bugs | review; test that runs the whole save |
| 8 | **Data-load impact is planned.** Before any migration or integration go-live, run the load file against the active rules in a sandbox and decide per rule: fix the data, use the bypass, or change the rule (with a CR, PR-05) | validation rules apply to API saves too; a migration that fails on row 40 000 is found too late | migration plan (`docs/design/`); PR-05 |
| 9 | **Formula fields hold no security and no history.** Use FLS for access. A formula that must be filtered on large volumes, reported over time or used to start automation becomes a stored field set by a before-save Flow or Apex | formula values are calculated when read: they change without a save, so no trigger or Flow fires, and history tracking cannot track them [high, Salesforce Help "Formula Field Limits and Restrictions"] | review; `data-model-ldv.md` |
| 10 | **Cross-object formulas are checked for exposure and cost.** A user can see a cross-object formula value even without access to the source record [med: confirm in Salesforce Help "Tips for Building Cross-Object Formulas" for the current behaviour]; each spanned relationship counts toward a per-object limit [med: check the current number in "Formula Field Limits and Restrictions"] | silent data exposure; hitting the relationship limit late blocks the next field | review; `permissions-access.md` |
| 11 | **Native roll-up summary fields only exist on the master side of a master-detail** [verified, Salesforce Help "Roll-Up Summary Field"; sf-skills `platform-custom-field-generate`]. Every other roll-up (lookup parent, filtered across objects) is an automation choice: Flow, Apex or a packaged tool, decided per object (ARCH-001) | choosing master-detail only for a roll-up changes ownership, sharing and deletes of the child: the detail takes the master's owner and security, and deleting the master deletes it [verified, Salesforce Help "Object Relationships Overview"] (`objects-fields.md`) | data model review (`objects-fields.md`); PR-15 when options are close |
| 12 | **Tests:** each rule has a test that it blocks (with the expected message) and a test that the valid case and the bypass save. Test data factories must create valid records; run all local tests in the sandbox before merging a new rule | a new rule breaks unrelated Apex tests that build incomplete records | `testing.md`; G4; HG-05 |

## Naming and description
| Item | Convention | Example |
|---|---|---|
| Validation rule API name | `<Field or Area>_<Rule>`; letters, digits and single underscores, max 40 characters [high, sf-skills `platform-validation-rule-generate`] | `CloseReason_RequiredWhenLost`, `EndDate_AfterStartDate` |
| Validation rule description | the business rule in one sentence · when it fires · bypass used · ticket key | `Lost opportunities need a close reason. Fires on stage change to Closed Lost. Bypass: project standard. ABC-123` |
| Error message | what is wrong + what to do; no technical words, no field API names | `Enter a close reason before you set the stage to Closed Lost.` |
| Formula field API name | says the result, not the calculation; an established org style wins | `Days_Since_Last_Activity__c`, `Is_Key_Account__c` |
| Formula field description | inputs · result type · blank handling · ticket key | — |

Error message text: validation rule messages are translatable through the Translation Workbench [high]; write them once in the base language and translate, don't build language branches in the formula.

## Formula practices
- **Readable over clever.** Indent nested `IF` / `CASE`, one condition per line; split a long rule into two rules with their own messages.
- **Blank handling on purpose:** number, currency and percent formulas usually treat blanks as zero, text and dates as blank [high, sf-skills `platform-custom-field-generate`]. Write it in the description.
- **Formula size limits:** formulas have a text length and a compiled size limit [med: check current numbers in "Formula Field Limits and Restrictions"]. A formula near the limit is a sign the logic belongs in Apex or in a stored field.
- **Non-deterministic formulas** (using `TODAY()`, `NOW()` or other records) can't be indexed and slow down large list views and reports [high, Salesforce Help]. For large objects store the value (`data-model-ldv.md`).
- **Function types:** `TEXT()` is not used on text fields, `DAY()` / `MONTH()` need a Date (convert Datetime first), `VALUE()` only on text [high, sf-skills `platform-validation-rule-generate`].
- **Formulas in XML:** formulas with `&`, `<` or `>` go in a CDATA section in the metadata file [high, sf-skills].

## Before a data load or integration go-live
1. List the active validation rules on each target object (retrieve them from the sandbox; don't trust memory, AI-02).
2. Run the load file, or a representative sample, in a full or partial copy sandbox with the rules active and the integration user's real permissions.
3. For each failing rule, record the decision on the migration plan: fix the data, use the bypass for this load, or change the rule (CR, PR-05).
4. Turn the bypass off after the load and record when it was on (who, from, to) for the audit trail.

## Default values
- A default value (or default value formula) fills a field **only when a record is created** and the field has no value; it never runs on edit [high, Salesforce Help "Default Field Values"].
- Prefer a default value over a before-save Flow for a simple, static default: no automation to test or order.
- Use a before-save Flow (`flows.md`) when the default depends on other fields that may be set later in the same save, or when it must also apply on update.
- Default values can reference `$User`, `$Organization` and Custom Metadata; no hard-coded IDs (HG-03).

## Roll-ups: pick the mechanism
| Option | Use when | Watch |
|---|---|---|
| Native roll-up summary | master-detail already chosen for other reasons; COUNT, SUM, MIN, MAX | per-object limit on roll-up fields [med: check the current number in Salesforce Help]; parent record locks during child loads (`data-model-ldv.md`) |
| Record-triggered Flow | lookup parent, low to medium volume, admin-maintained | must handle insert, update, delete and reparenting; bulk test 251+ records (`flows.md` rule 11) |
| Apex (trigger handler or async) | high volume, complex filters, the object already has Apex automation | same events as Flow; lock contention on skewed parents |
| Packaged tool (e.g. the open-source Declarative Lookup Rollup Summaries) | the project already uses it | a dependency to keep updated; counts toward the pattern register (PR-06) |
| Report or CRM Analytics | the number is only needed for reporting | no field value on the record (`reports-dashboards.md`) |

## AI-assisted building
- Use Salesforce's `platform-validation-rule-generate` skill for validation rule XML and `platform-custom-field-generate` for formula and roll-up fields. Our rules add: bypass, `ISCHANGED` gating, error text and placement, description and tests are checked on the output before the rule counts as built.
- From the official skills [high]: formula fields use the result type (`Number`, `Text`, …) as `<type>`, never `Formula`; roll-up fields use `<type>Summary</type>` with a fully qualified `summaryForeignKey` (`Child__c.Master__c`) and no precision or scale.
- Field and object names in the formula must exist in the project or org (AI-02). The AI does not invent the bypass permission name: it reads it from the project config or asks.
- "Update the formula to X" replaces the logic; "also X" adds to it. When the ticket is unclear, ask (PR-01) instead of guessing.
- The AI activates or changes validation rules only in a write-allowed sandbox (HG-11), never in production (HG-09).

## Anti-patterns
Rule without bypass · rule that fires on every save of old records · "Invalid value" messages · error at the top of the page for a single-field rule · hard-coded record type Ids or profile names · validation in a formula that queries half the data model · security by formula or by hiding a field · formula used as a trigger condition that never fires · master-detail chosen only to get a roll-up · roll-up Flow that forgets delete and reparent · migration run with validation rules nobody checked.

## Enforcement
- No rule in the verified Code Analyzer inventory checks validation rule or formula metadata [verified, name scan of 719 rules on 2026-11-20]. Rules 1–5 and 9–11 are checked in review and by tests.
- Proposal (needs approval per PR-14): a custom regex rule in `rules/custom-rules.yaml` that flags `*.validationRule-meta.xml` files whose formula does not reference the project bypass, with bad / good fixtures.
- Tests prove rules 1, 3, 7 and 12 (`testing.md`); traceability from requirement to rule to test (PR-12).

## Sources
- Salesforce Apex Developer Guide, Triggers and Order of Execution — developer.salesforce.com
- Salesforce Help, Formula Field Limits and Restrictions; Tips for Building Cross-Object Formulas; Default Field Values — help.salesforce.com
- Salesforce Help "Roll-Up Summary Field" — https://help.salesforce.com/s/articleView?id=platform.fields_about_roll_up_summary_fields.htm&type=5
- Salesforce Help "Object Relationships Overview" — https://help.salesforce.com/s/articleView?id=platform.overview_of_custom_object_relationships.htm&type=5
- forcedotcom/sf-skills `platform-validation-rule-generate`, `platform-custom-field-generate` (cloned 2026-11-20, commit 431c50f)
- Salesforce Code Analyzer v5 rule inventory (719 rules, 2026-11-20)
