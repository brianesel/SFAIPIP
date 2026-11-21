# Reports and dashboards

**Verdict:** reports, dashboards, report types and folders are deployable metadata, so build them in source like everything else: reuse a report type before creating one, keep every report in a named shared folder, choose each dashboard's running user on purpose (a static running user shows that user's data to every viewer), set explicit time-frame filters, and open the result as a real user before anyone sees it. A report that deploys cleanly can still show the wrong numbers.
Sources: see end. Confidence: non-negotiables [high]; numbers marked inline; analyzer rule names [verified] against `sf code-analyzer rules --rule-selector all` on 2026-11-20 (no analyzer rule covers report or dashboard XML, so checks here are review and test).

## Scope
Custom report types, Lightning reports (tabular, summary, matrix, joined), dashboards and dashboard components, report and dashboard folders, and their sharing. Out of scope: CRM Analytics / Tableau, list views, reporting snapshots (mentioned only as a large-data option), and the data model behind the reports (`objects-fields.md`, `../architecture/data-model-ldv.md`).

## Non-negotiables
| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | **Reuse before you create a report type.** Search existing standard and custom report types for the object combination first; create a custom report type only when none fits, and record why on the ticket | duplicate report types confuse report builders and stay as debt nobody owns [med: field experience] | PR-04 (repeat search, by analogy); review |
| 2 | **Reports and dashboards live in named, shared folders, never in a personal folder or Unfiled Public Reports.** Folder metadata is in source next to the reports | private reports can't be packaged; Unfiled Public Reports can be added to a change set but do not migrate [med: reading of Salesforce Help "Components Available in Change Sets", release 264, not reproduced in an org] | review; release checklist (07) |
| 3 | **Folder access goes to groups or roles, not named users.** View for consumers; Edit or Manage only for the owning team | folder shares on individuals break when people leave and hide who can see what | review; `permissions-access.md` |
| 4 | **Every dashboard has a deliberate running user.** "Run as specified user" shows that user's data to everyone with folder access; use the viewer (dynamic dashboard) when data must follow the viewer's access. A specified running user is a named, low-privilege user, never an admin | a dashboard running as an admin publishes admin-level data to every viewer, which bypasses sharing in effect | review; G2 design note |
| 5 | **No org-specific values in report or dashboard metadata.** No record IDs in filters (filter on names, record type developer names or picklist values); no personal usernames as running user. Use a dedicated user with the same username pattern in every org, or set the running user as a recorded post-deploy step | IDs and usernames differ per org, so the deploy fails or the dashboard shows the wrong data | HG-03 (by analogy); review |
| 6 | **Explicit time-frame filter on every report** (relative intervals such as this and last fiscal year), and the filters say what is in and out (open vs all, record types) | without it the report often shows only the current period and gives a wrong picture [med: observed in a delivery project] | review; UAT |
| 7 | **Column names come from the report type, not the field API name.** Report XML uses platform column names (`CLOSE_DATE`, not `CloseDate`); a custom report type is referenced with the `__c` suffix and its columns use `$` paths | the most common report deploy failure [high, sf-skills `platform-report-generate` rules 2–3] | `platform-report-generate` verification checklist |
| 8 | **Description on every report type, report and dashboard:** who uses it, what question it answers, ticket key | in the report picker, the label and description are all a user sees | review |
| 9 | **Verify in the browser as a target user before showing it.** Check periods, groupings, filters and rough counts against a SOQL `COUNT()`; when a result is zero, run and log a control query without the filter | deploy success says nothing about the data shown; a zero result can be a silently rejected filter [med: field experience] | UAT; G4 evidence (AI-05) |
| 10 | **Large data: selective filters first.** Filter on indexed fields, use relative date ranges, avoid `contains` on large objects, prefer summaries over long detail lists | non-selective reports on large objects time out [high]; check the current report run and display limits in Salesforce Help before quoting a number | review; `../architecture/data-model-ldv.md` |

## Structure and naming
| Item | Convention | Example |
|---|---|---|
| Custom report type API name | `<BaseObjects>_with_<RelatedObjects>`, as the builder reads it | `Accounts_with_Projects` (referenced in reports as `Accounts_with_Projects__c`) |
| Report type label | `<Base objects> with <Related objects>`; category set so users find it | `Accounts with Projects and Tasks` |
| Report name | `<Object or area> - <Question>`; max 40 characters [high, sf-skills `platform-report-generate` rule 6] | `Opps by Stage - Avg Deal Size` |
| Report / dashboard API name | the name without spaces, underscores between words | `Opps_by_Stage_Avg_Deal_Size` |
| Folder | per audience or business area, not per author | `Sales_Leadership`, `Service_Operations` |
| Dashboard | `<Audience> - <Purpose>`; each component title states the question it answers | `Sales Leadership - Pipeline Health` |
| Description | purpose · audience · data scope (filters, period) · owner · ticket key; report description max 255 characters [high, sf-skills `platform-report-generate` rule 12] | — |

Rules of thumb [high]:
- **One question per component.** A dashboard of six components answers six named questions; a chart with too many series answers none.
- **Pick the chart for the question:** trend over time → line; compare categories → bar or column (bar for long labels); share of a whole → donut with few segments; one key number → metric; target vs actual → gauge; stages → funnel; detail → table [med: field practice].
- **Summary or matrix for charts and totals.** Charts, aggregates and custom summary formulas need a summary or matrix report [high, sf-skills `platform-report-generate` rules 4–5, 16].
- **Inner vs outer join is a business choice.** In a custom report type, an outer join keeps parents without children; once a join is outer, every deeper join must be outer too; one report type joins at most four objects [high, sf-skills `platform-custom-report-type-generate` rules 2, 6, 7].
- **The base object of a custom report type can't be changed after creation** [high, same skill]: settle it in design.

## Running user and data visibility
| Dashboard type | Data shown | Use when | Watch |
|---|---|---|---|
| Run as specified user | that user's access, to every viewer | the same company-wide numbers for everyone | the running user's access is the dashboard's data exposure: review it like a permission set |
| Run as logged-in user (dynamic) | each viewer's own access | data must follow sharing | the number of dynamic dashboards is limited per edition [med: check the current limit in Salesforce Help]; scheduling and following differ from static dashboards [med] |
| Run as a manager's team (where offered) | one manager's team view | team leads | availability per edition [low: verify in Salesforce Help before promising] |

Reports themselves always run with the viewing user's record access and field-level security [high]. Folder access controls who can open a report, not which rows they see.

## Reports as deployable metadata
- **Deploy order follows dependencies:** objects and fields → report type → folders → reports → dashboards [high]. A report on a report type that isn't in the target org fails.
- **Retrieve reports and dashboards by folder and name** (`Report:<Folder>/<Report>`); don't rely on wildcards for folder-based types [high, Metadata API Developer Guide; field notes: wildcard retrieves can miss components from installed unlocked packages, med].
- **Report type `deployed`:** `false` while you iterate, `true` to expose it to users [high, sf-skills `platform-custom-report-type-generate`].
- **New fields don't appear by themselves in a custom report type:** add each field to the report type's section in the same ticket that creates it [high]; link the field ticket and the report ticket (PR-12).
- **Before deleting or renaming a field,** check where it is used in reports and report types; deletion breaks them [high]. Record the impact on the ticket.

## Large data and performance
- Filter on indexed fields (Id, Name, OwnerId, CreatedDate, SystemModstamp, lookups, External IDs) and add a relative date range [high, Salesforce Query & Search Optimization Cheat Sheet].
- Avoid cross filters, `contains` and formula fields as the main filter on large objects; each adds work to every run [med].
- For trends over long periods, consider reporting snapshots or an analytics product instead of a live detail report [med].
- A slow source report makes the whole dashboard slow. Test with production-like volumes in a full or partial copy sandbox [high].

## AI-assisted building
- Use Salesforce's `platform-report-generate` (report XML) and `platform-custom-report-type-generate` (report type XML). Both require looking up column names and report types before any XML is written; our rules add folders, running user, time frame and browser verification.
- sf-skills has no general dashboard-generation skill at commit 431c50f [verified: skill list]. For dashboards, retrieve a working dashboard from the sandbox as a template and edit it; don't write dashboard XML from memory (AI-02). Field notes: components reference reports with `<report>`, chart type values are exact enums, some style fields are required [med: field notes; check against the Metadata API Dashboard reference].
- The AI deploys reports and dashboards only to a write-allowed sandbox (HG-11), never to production (HG-09).
- The AI never calls a dashboard correct without having opened it and compared counts (AI-05).

## Anti-patterns
New report type per report · reports in personal or Unfiled Public folders · folders shared to named users · dashboard running as an admin · personal username as running user in source · record IDs in report filters · no time-frame filter · "all time" detail reports on large objects · charts on tabular reports · six series in one chart · showing a dashboard nobody opened · a zero-row result reported as "no data" without a control query.

## Enforcement
- No Code Analyzer rule covers report, dashboard or report type XML [verified: inventory of 719 rules, 2026-11-20]. Checks are review, the `platform-report-generate` verification checklist, and UAT evidence (G4, G5).
- Release checklist (07): reports and dashboards in named folders, folder metadata in the package, running user resolved in the target org.
- Proposal (needs approval per PR-14): a custom regex rule that flags 15- or 18-character ID patterns in `*.report-meta.xml` filter values and personal usernames in `*.dashboard-meta.xml`.

## Sources
- forcedotcom/sf-skills `platform-report-generate`, `platform-custom-report-type-generate` (cloned 2026-11-20, commit 431c50f)
- Salesforce Help, Components Available in Change Sets (report folder behaviour, release 264)
- Salesforce Help, dashboard running user and dynamic dashboards — help.salesforce.com
- Salesforce Developers, Metadata API Developer Guide: Report, ReportType, Dashboard, ReportFolder, DashboardFolder
- Salesforce Query & Search Optimization Cheat Sheet (indexed fields, selectivity)
