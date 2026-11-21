# Lightning pages and UI configuration

**Verdict:** the UI is configuration, so it lives in source control and follows the same review as code. Build few Lightning record pages per object, one per audience, with Dynamic Forms and Dynamic Actions where the object supports them; keep the first view light; show the right fields with compact layouts; put every user-facing text in labels or translatable metadata. Visibility rules shape the screen, they never secure data: access comes from permission sets (`permissions-access.md`).
Sources: see end. Confidence: non-negotiables [high]; numbers marked inline; analyzer rule names [verified] against the Code Analyzer v5 inventory (719 rules) on 2026-11-20.

## Scope
Lightning record, app and home pages (FlexiPages), page layouts, compact layouts, Dynamic Forms and Dynamic Actions, component visibility, Lightning apps and utility bars, tabs, list views, quick actions, custom labels and translations for UI text, SLDS styling, page performance and accessibility. Building custom components is `lwc.md`; screen Flows are `flows.md`; reports and dashboards are `reports-dashboards.md`; Experience Cloud sites are out of scope.

## Non-negotiables
| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | **Hiding is not security.** Component and field visibility rules, page assignments, app and tab visibility only change what a screen shows. Data access is FLS, object permissions and sharing in permission sets | hidden fields are still readable through reports, list views, search, the API and other pages | review; `permissions-access.md`; `security-sharing.md` |
| 2 | **Few pages, assigned on purpose.** One record page per object and audience; assign by app, record type and profile only where the audience really differs. Every page and every assignment is in source control | a page per profile becomes dozens of near-copies that drift; nobody knows which one a user sees | review; release checklist |
| 3 | **Dynamic Forms and Dynamic Actions** for new record pages where the object supports them [med: check the supported-objects list in Salesforce Help "Dynamic Forms" for standard objects]; fields in sections by task, required fields first | field and action visibility per context without extra page layouts or record types | review |
| 4 | **Light first view.** Put secondary content in tabs or accordions, keep only the related lists users act on, avoid several components that load the same data. Run the Lightning App Builder page performance analysis before review [high: the analysis exists; read its findings, not a fixed score] | every component on the first view loads before the user can work; slow pages are the most common UI complaint | App Builder performance analysis; UAT |
| 5 | **No JavaScript buttons or links.** Use quick actions (Flow, LWC, create or update record), Dynamic Actions or a screen Flow | JavaScript buttons do not run in Lightning Experience and are a security risk [high, Salesforce Help on buttons and links in Lightning Experience] | `pmd:AvoidJavaScriptWebLink`, `pmd:AvoidJavaScriptCustomObject` |
| 6 | **Every user-facing text is translatable.** Custom labels for text in components and Flows; field labels, help text, picklist values, action and page labels through the Translation Workbench. No text hard-coded in LWC markup or JavaScript | users in another language see a mixed UI; changing a word needs a code release | review; `../architecture/configuration.md`; `lwc.md` |
| 7 | **Compact layout per object** with the few fields that identify the record; it drives the highlights panel and the mobile record header [high, Salesforce Help "Compact Layouts"] | the default compact layout shows little more than the name | review |
| 8 | **Apps and tabs are granted, not assumed.** Grant app and tab visibility through permission sets (profiles only where the project still uses them); an app nobody is granted is invisible to everyone [high, sf-skills `platform-custom-application-generate`] | a deployed app that no user can open looks like a failed release | release checklist; UAT with a real user persona |
| 9 | **Activation is part of the release.** Record page assignments live in the app's and object's action overrides; deploy them with the page and verify in the sandbox as a user of each assigned profile or app | a page that deploys but is not assigned changes nothing, with no error | release checklist (07); PR-13 |
| 10 | **Accessible by default.** Use standard components and base components as designed, give every field a label and help text where the meaning isn't obvious, don't carry meaning by colour alone, keep tab order logical | standard components are built to be accessible; custom layouts and colour coding are where WCAG failures come from [med, sf-skills `experience-accessibility-validate`] | review; `lwc.md` accessibility tests |
| 11 | **List views are curated.** Shared list views have a clear name, a deliberate audience (all users, or named groups or roles) and columns users need; personal list views stay out of source control | dozens of "All X (copy)" views make users export to Excel | review |

## Naming
| Item | Convention | Example |
|---|---|---|
| Record page (FlexiPage) | `<Object>_Record_Page[_<Audience>]` | `Account_Record_Page_Sales`, `Case_Record_Page_Service` |
| App page / home page | `<Area>_App_Page` / `<Audience>_Home_Page` | `Onboarding_App_Page`, `Sales_Home_Page` |
| Lightning app | label says the job or audience; API name without spaces | `Service_Console` |
| Quick action | `<Verb>_<Noun>` on the object; label starts with the verb | `Log_Visit`, `Request_Credit_Check` |
| List view | `<Audience or Scope>_<Filter>`; label under 40 characters [high, sf-skills `platform-list-view-generate`] | `My_Open_Cases`, `Team_Renewals_This_Quarter` |
| Custom label | `<Area>_<Purpose>`; category = component or feature | `CaseClose_ErrorMissingReason` |
| Descriptions | every page, app, action and label says purpose, audience and ticket key | — |

An established org style wins over this table (PR-06); record the choice in the pattern register.

## Page layouts, compact layouts and Dynamic Forms
- With Dynamic Forms, the page holds the fields; page layouts still drive the Record Detail component, related lists in the Related Lists component, and some other contexts [med: check per object and per channel, e.g. mobile, before removing fields from a layout].
- Don't keep two sources of truth: when a page uses Dynamic Forms, keep the layout minimal and say so in its description.
- Record types are for different processes or picklist values, not for showing different fields: use visibility rules for that.
- Field visibility by user uses `$Permission` (Custom Permission) rather than profile name, so the rule follows the permission set model.

## Quick actions and Dynamic Actions
- Object-specific actions with predefined field values replace most custom buttons; the action layout holds only the fields needed for that task.
- An LWC quick action (screen or headless) or a Flow action when the task needs logic; the action description says what it changes.
- Dynamic Actions show an action only when it applies (status, record type, permission), which keeps the highlights panel short.

## UI text and translations
- Custom labels hold text used in components, Flows and Apex messages shown to users; LWC imports them from `@salesforce/label/c.<LabelName>`.
- Write the base-language text first, then translate through the Translation Workbench; one label per meaning, not per screen, so a word changes in one place.
- Labels follow the project's text style (sentence case, no internal codes); check it before handing over to test, because Jest and deploy checks don't read the screen [med: field report: a project where all tests passed while 7 of 12 labels had the wrong case].
- Never concatenate translated fragments into a sentence; use one label with placeholders and format it in code.

## Performance checklist
- First tab: highlights panel, the fields users edit most, at most the related lists they act on daily.
- Related lists: Dynamic Related Lists with filters and a sensible row count instead of the full list.
- Custom components: share data through Lightning Data Service instead of one Apex call per component (`../architecture/lwc-data-access.md`).
- Check the page on the slowest channel in scope (mobile app, VPN users) before sign-off.

## SLDS
- Order: base components → SLDS blueprints → SLDS styling hooks (`--slds-g-*`) → custom CSS as last resort [high, sf-skills `design-systems-slds-apply`]. Never override SLDS classes; never use private or shared hooks.
- Target SLDS 2: legacy `--lwc-*` design tokens are deprecated [high, sf-skills `design-systems-slds-apply`]; verify that a hook exists before using it (the skill ships a hooks index).
- No hard-coded colours, spacing or font sizes; they break dark mode and theming.
- Checked by the SLDS ESLint plugin in Code Analyzer: `eslint:@salesforce-ux/slds/lwc-token-to-slds-hook`, `eslint:@salesforce-ux/slds/no-hardcoded-values-slds2`, `eslint:@salesforce-ux/slds/no-slds-class-overrides`, `eslint:@salesforce-ux/slds/no-deprecated-classes-slds2`, `eslint:@salesforce-ux/slds/no-slds-private-var`. Defaults are severity 3–4, so they report but don't block.

## AI-assisted building
- Use Salesforce's `platform-flexipage-generate` skill for pages. From the skill [high]: start a new page from the CLI template command, never from hand-written XML; add components only after discovering them in the project or org; field references use `Record.<FieldApiName>`; every identifier is unique in the file.
- `platform-custom-application-generate` for apps (save order: utility bar page, then the app, then visibility grants), `platform-custom-tab-generate` for tabs, `platform-list-view-generate` for list views.
- Our rules add: audience and assignment are decided in the design (G2) before the page is built; visibility rules are reviewed against rule 1; labels are translatable.
- Field, object and component names must exist in the project or org (AI-02). The AI deploys and assigns pages only in a write-allowed sandbox (HG-11), never in production (HG-09).

## Anti-patterns
A record page per profile · security by visibility rule · forty components on the first tab · the same data loaded by three components · JavaScript buttons · hard-coded UI text · colour as the only signal · default compact layout · apps deployed without visibility · pages built in production App Builder and never retrieved · "copy of" list views shared to all users · custom CSS overriding SLDS classes.

## Enforcement
- Code Analyzer: `pmd:AvoidJavaScriptWebLink`, `pmd:AvoidJavaScriptCustomObject` (security, severity 2 by default, so they block under HG-10); SLDS ESLint rules above for component styling.
- Not mapped yet, proposal for project config (needs approval per PR-14): raise `eslint:@salesforce-ux/slds/no-hardcoded-values-slds2` and `eslint:@salesforce-ux/slds/no-slds-class-overrides` to severity 3 and tag them `Project`.
- FlexiPage structure, assignments, visibility rules and accessibility: review, UAT with real personas, and the App Builder performance analysis. No analyzer rule covers FlexiPage XML [verified, name scan of 719 rules on 2026-11-20].

## Sources
- Salesforce Help topics: Dynamic Forms; Dynamic Actions; Compact Layouts; Lightning App Builder page performance analysis; custom buttons and links in Lightning Experience; Translation Workbench — help.salesforce.com [med: article titles paraphrased, search by topic]
- forcedotcom/sf-skills `platform-flexipage-generate`, `platform-custom-application-generate`, `platform-custom-tab-generate`, `platform-list-view-generate`, `design-systems-slds-apply`, `design-systems-slds-validate`, `experience-accessibility-validate` (cloned 2026-11-20, commit 431c50f)
- Salesforce Code Analyzer v5 rule inventory (719 rules, 2026-11-20)
