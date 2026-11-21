# Objects and fields

**Verdict:** the data model is the hardest thing to change later, so build it from a signed-off design: standard object first, one clear purpose per custom object, the right field type the first time, a description and help text on every field, required rules where they belong, external IDs on everything an integration writes, and a permission set in the same ticket. Relationship type, record type vs object and volume are design decisions (`../architecture/data-model-ldv.md`); this page is how to build what was decided.
Sources: see end. Confidence: non-negotiables [high]; platform limits marked inline; no analyzer rule in the verified inventory checks object or field XML, so most checks are review, `ticket_lint.py` or a project rule.

## Scope
Custom objects, custom fields on standard and custom objects, picklists, global and standard value sets, record types, lookup and master-detail relationships, field history and indexes. Pointers only: Big Objects and archiving (`../architecture/data-model-ldv.md`, ARCH-005), validation rules and formulas (`validation-rules-formulas.md`), page layouts and Lightning pages (`lightning-pages-ui.md`), access to new objects and fields (`permissions-access.md`), integration-facing metadata (`integration-metadata.md`).

## Non-negotiables
| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | **Only what the signed-off design names.** New objects and fields come from the design (DAT-01, DAT-02) and the ticket's `metadata` list; anything else is a CR | schema drift is permanent; every field is cost in layouts, reports, tests and integrations | G2; G3 (`ticket_lint.py`); PR-05 |
| 2 | **Search before you create.** Check the org and project for an existing standard or custom field with the same meaning (grounding search, then exact SOQL or retrieve) | duplicate fields split data and reports | AI-02; review |
| 3 | **Every object and field has a description and help text.** Description: what it holds, what sets it (user, Flow, Apex, integration), what uses it, ticket key. Help text: what the user should enter, beyond the label | in Setup and in the API, the description is the only documentation a maintainer sees | review; project rule proposal (see Enforcement) |
| 4 | **Choose the type for the data, not the screen.** Picklist for a fixed list, lookup for another record, number / currency / date for values you calculate or filter on, text only for free text. Changing a type later can lose data | type changes on populated fields convert or drop values | review |
| 5 | **Required in the right place.** Universally required (field level) only when every source, including integrations and data loads, always has the value; otherwise a validation rule with a clear message, or required on the layout / Dynamic Form for UI-only cases | field-level required breaks loads and integrations and can't be bypassed | review; `validation-rules-formulas.md` |
| 6 | **External ID (unique) on every object an integration or migration writes**, named after the source system | idempotent upserts; also gives the field a custom index | `../architecture/data-model-ldv.md` rule 4; ARCH-002 inventory |
| 7 | **Relationship type is decided, not defaulted.** Master-detail only when the child can't exist alone and should inherit sharing, delete and roll-ups; lookup otherwise, with an explicit delete behaviour | converting later is a data migration; master-detail forces `ControlledByParent` sharing | design / ADR; `data-model-ldv.md` rule 2 |
| 8 | **OWD set on purpose** in the object file for every new object (see `permissions-access.md` rule 8). The official object skill defaults to `ReadWrite`; the pipeline uses the access-model ADR | the default is the most open option | review |
| 9 | **Access ships with the field** (permission set in the same ticket) and **no hard-coded IDs** of record types or values anywhere that reads them | see `permissions-access.md` rule 3; HG-03 | G3; `pmd:AvoidHardcodingId`; `flow:HardcodedId` |
| 10 | **Destructive changes are their own reviewed step:** deleting a field, changing its type, deleting picklist values, lookup → master-detail. Snapshot the data first, include it in the rollback plan | they can't be undone by redeploying the old metadata | PR-13; release checklist (07) |

## Naming
Use the project's naming document if it exists (an established org style wins); otherwise these defaults. API names are English, `Title_Case_With_Underscores`, no abbreviations, no reserved words (`Order`, `Group`, `Select`, `Type`, `Date`, …) [high, sf-skills `platform-custom-object-generate`].

| Item | Convention | Example |
|---|---|---|
| Custom object | singular noun; junction = both parents | `Invoice__c`, `Position_Candidate__c` |
| Field | what it holds, not where it shows | `Contract_End_Date__c`, `Annual_Revenue_EUR__c` |
| Checkbox | `Is_` / `Has_` prefix | `Is_Key_Account__c` |
| Lookup / master-detail field | named after the role of the target | `Primary_Contact__c`, `Billing_Account__c` |
| Relationship name | plural PascalCase | `Invoice_Lines` |
| External ID | `<System>_Id__c` | `ERP_Id__c` |
| Formula / roll-up | result meaning, no `_Formula` suffix needed | `Days_Since_Last_Activity__c` |
| Record type | `DeveloperName` per variant | `Partner_Account` |
| Global value set | the shared concept | `Priority_Levels` |
| Picklist values | API name = the business value, spaces allowed; label may be translated | `Closed Won` |

Labels are in the users' language and Title Case; the API name doesn't change when the label does.

## Fields: build practices
| Topic | Do | Watch out |
|---|---|---|
| Text | set the shortest length that fits real data | Text max length 255; Text Area has a fixed 255 and takes no `<length>` [high, sf-skills `platform-custom-field-generate`] |
| Number / currency | `precision` ≤ 18 and `scale` ≤ `precision` [high, same source]; currency for money | Number for codes that are really text (leading zeros) |
| Picklist | restricted by default; inline values for one field, a global value set when several fields share the list | restricted picklists are capped at 1,000 values incl. inactive [med: sf-skills, check current limit]; deactivate values, don't delete them, when data uses them |
| Standard value set (e.g. `Industry`) | read the current set first; a deploy replaces the whole set | the names come from a fixed catalogue, you can't create new ones [high, sf-skills `platform-value-set-generate`] |
| Dependent picklist | both fields restricted; use the API 38.0+ `valueSettings` form | the legacy form fails to deploy [high, same source] |
| Formula | for display and simple derivations; complex logic in Apex or Flow | see `validation-rules-formulas.md`; filters on formula fields are usually not selective on large objects (`data-model-ldv.md`) |
| Roll-up summary | only on the master of a master-detail | for lookups use Flow or Apex roll-ups (decision in the design) |
| Unique / external ID | case-sensitivity chosen on purpose | external IDs are allowed on Text, Number and Email (and Auto Number) fields [med: check Salesforce Help "Custom Field Attributes"] |
| Field history | track only fields with an audit or business need | a limited number of tracked fields per object (20 per object by default [med: Salesforce Help "Field History Tracking"; Field Audit Trail raises it]); retention is limited, decide where long-term history goes (`data-model-ldv.md`) |
| Indexes | filter on indexed fields (Id, Name, lookups, external ID / unique fields) | other custom indexes are requested from Salesforce Support (`data-model-ldv.md`) |
| Encryption / sensitivity | classify personal and sensitive fields when created (`Data Sensitivity Level`, `Compliance Categorization` if used) | Shield encryption limits filtering and sorting; decision per DAT-04 |

## Objects and relationships
- **Standard object first** (Account, Contact, Case, Asset, Product, …), then a record type, then a new object (`data-model-ldv.md` rules 1, 3).
- **Name field:** Text for things people name; Auto Number with a display format (`INV-{0000}`) for transactions and logs [high, sf-skills].
- **Object features on purpose:** reports, search, activities and history on user-facing objects; off on junctions and technical logs.
- **Master-detail:** at most 2 per object [high, sf-skills `platform-custom-field-generate`, Salesforce Help]; the child's OWD is `ControlledByParent`; deleting the master deletes the children; reparenting is off unless allowed. Detail records can't have sharing rules, manual sharing or queues [high, Salesforce Help "Object Relationships Overview"].
- **Deploying master-detail** (new field, or lookup → master-detail): every detail row must reference a master; deleted detail rows in the recycle bin are removed permanently by the deploy [med: Salesforce Help "Special Behavior in Deployments"]. Ask whether those rows matter before the release.
- **Lookup:** choose delete behaviour (`SetNull`, `Restrict`, `Cascade`) explicitly; add a lookup filter when only some records are valid targets. Total relationship fields per object are limited [med: check "Custom Field Allocations" in Salesforce Help for your edition].
- **Record types:** for variants of one thing that need different picklist values, processes or layouts. On Opportunity, Lead, Case and Solution a record type also needs a business process [high, sf-skills `platform-custom-field-generate`]. Look them up by `DeveloperName` in code and Flows.
- **Big Objects, External Objects, archiving:** only from the ARCH-005 decision (`data-model-ldv.md`).

## AI-assisted building
- Use Salesforce's `platform-custom-object-generate`, `platform-custom-field-generate` and `platform-value-set-generate` skills for valid XML; `platform-metadata-grounding-get` to find existing metadata by meaning. Grounding is ranked and incomplete: confirm a "doesn't exist" answer with exact SOQL or a retrieve before creating anything (AI-02).
- Pipeline differences from the official skills: OWD comes from the access-model ADR, not `ReadWrite` by default (rule 8); every field also needs the permission set and the ticket's `metadata` entry; the official skill asks before rewriting an existing object description, and so do we.
- Never invent picklist values, field names or record types; standard value sets are read from the org before a change.
- Validate with a dry-run deploy against a write-allowed sandbox (HG-11); destructive changes are proposed, a human approves (AI-01).

## Anti-patterns
New object where a standard one fits · a custom field that duplicates a standard field · fields without description or help text · text fields holding dates, numbers or IDs · open (unrestricted) picklists that collect typos · field-level required that breaks integrations · master-detail picked for "it shows a related list" · more record types than real variants · hard-coded record type IDs · history tracking on every field · deleting fields or picklist values without a data check · fields created in production by hand.

## Enforcement
- `ticket_lint.py` (G3): every object and field in the ticket's `metadata` is marked existing (and verified) or new.
- Review checklist in DoD (G4): description, help text, type, required placement, permission set, OWD.
- No built-in analyzer rule covers object or field XML in the verified inventory. Proposal (needs approval per PR-14): a regex project rule on `*.field-meta.xml` and `*.object-meta.xml` that flags a missing `<description>` or (fields) `<inlineHelpText>`, drafted in `rules/custom-rules.yaml` with bad and good fixtures.
- Code that reads the schema is covered elsewhere: `pmd:AvoidHardcodingId` and `flow:HardcodedId` (HG-03), `pmd:EagerlyLoadedDescribeSObjectResult` for describe calls.
- Evaluation (01): fields without description, unused fields, duplicate fields, objects near relationship or field limits.

## Sources
- Salesforce Help: Object Relationships Overview; Considerations for Relationships; Roll-Up Summary Field; Field History Tracking; Custom Field Allocations; Special Behavior in Deployments — help.salesforce.com
- Metadata API Developer Guide: CustomObject, CustomField, GlobalValueSet, StandardValueSet, RecordType
- forcedotcom/sf-skills `platform-custom-object-generate`, `platform-custom-field-generate`, `platform-value-set-generate`, `platform-metadata-grounding-get` (cloned 2026-11-20, commit 431c50f)
- `../architecture/data-model-ldv.md` (standard-first, skew, selectivity, archiving)
