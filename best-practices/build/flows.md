# Flows

**Verdict:** a Flow is production code that people can't see in a diff. Build it like code: one job per Flow, entry criteria on every record-triggered Flow, same-record updates before save, no data operations in loops, a fault path on every element that can fail that decides on purpose whether to stop (roll back) or continue, no hard-coded IDs, a description a maintainer can read, and tests that use bulk data. Choosing Flow or Apex for an object is an architecture decision (ARCH-001, automation density), not a per-ticket preference.
Sources: see end. Confidence: non-negotiables [high]; numbers marked inline; analyzer rule names [verified] against `sf code-analyzer rules --rule-selector all` on 2026-11-20.

## Scope
Record-triggered (before / after save), scheduled, autolaunched (no trigger), screen and platform-event-triggered Flows, plus Flows used as Agentforce actions. Out of scope: Process Builder and Workflow Rules (legacy: migrate when touched, never extend), OmniScript and Integration Procedures.

## Non-negotiables
| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | **Flow or Apex is decided per object, not per ticket: one entry mechanism per object.** Follow the pattern register for that object; a new busy object gets an ARCH-001 decision. Record-triggered Flow and Apex triggers as entry points on the same object only as a recorded exception (ADR) | Salesforce: "use one mechanism as your entry point… try to avoid mixing Flow and Apex triggers" [verified, Salesforce Architects "Record-Triggered Automation" decision guide]; mixed entry points cause double writes and unpredictable order | PR-06; rubric `automation.double_write_fields`; `trigger-framework.md` rule 8 |
| 2 | Every record-triggered Flow has **entry criteria**; prefer "only when updated to meet the condition" or a formula on `$Record__Prior`, so it runs only when a relevant field changed | without them the Flow runs on every save of every record, burning limits and re-running itself | `flow:TriggerEntryCriteria` |
| 3 | **Same-record field updates go in a before-save Flow.** After-save is for related records, actions, callouts (async path) and anything that needs the record Id | before-save avoids an extra DML and a second pass through the save order, which also removes most recursion | `flow:SameRecordUpdate`; review |
| 4 | **No Get / Create / Update / Delete inside a Loop.** Collect into a collection variable, then one data element after the loop | record-triggered Flows run in batches of up to 200 records per transaction [high, Salesforce record-triggered decision guide]; per-record DML hits limits on data loads | HG-02; `flow:DbInLoop` |
| 5 | **Fault path on every element that can fail** (Get, Create, Update, Delete records, Actions, Subflows). It goes to the project's logging pattern (ARCH-004) or a named owner, never to nobody | without one the user gets a generic error message and error logging is limited [verified, Code Analyzer "Flow Scanner Rules Reference", MissingFaultHandler]; the default error email goes to the user who last modified the Flow [verified, Salesforce Help "Select Flow and Process Error Email Recipients"] | `flow:MissingFaultHandler`; rubric `automation.flow_fault_paths`; `error-handling-logging.md` |
| 6 | **No hard-coded record IDs** (queues, record types, users, groups). Look them up by `DeveloperName` (with `Type = 'Queue'` for queues) or read them from Custom Metadata | IDs are org-specific (sandbox vs production), so the Flow breaks after deploy or when records are recreated [verified, Code Analyzer "Flow Scanner Rules Reference", HardcodedId; Salesforce Help "Plan for Success with Flow Builder Best Practices"] | HG-03; `flow:HardcodedId`; `configuration.md` |
| 7 | **No callouts or Wait elements in the synchronous part of a record-triggered Flow.** Use an asynchronous path or a Platform Event, and only when the work needs it (callouts, slow work); each asynchronous path has its own fault path | callouts are not allowed after uncommitted DML in the same transaction; asynchronous work started from record-triggered automation adds error-handling cases and limit risk [verified, Salesforce Architects "Record-Triggered Automation" decision guide, "exercise caution when triggering asynchronous processes"] | `flow:TriggerCallout`, `flow:TriggerWaitEvent` |
| 8 | **Access is explicit.** Set the run mode on purpose: record-triggered and scheduled Flows run in system context, screen Flows in user context by default [med: check "How Does Flow Security Work" in Salesforce Help for the current defaults per launch type]; "system context without sharing" only with a recorded reason (same rule as `without sharing` in Apex). Never pass user input into an element that runs without sharing | a system-context Flow started from a screen bypasses sharing for whoever runs it | HG-01, HG-06 (by analogy); `flow:PreventPassingUserDataIntoElementWithoutSharing`; `security-sharing.md` |
| 9 | **Bypass switch** on every record-triggered Flow, read from the project's standard bypass (Custom Permission or Custom Metadata, the same switch Apex uses) | data loads, migrations and incident fixes must not fire business logic | review; bypass test; `trigger-framework.md` rule 4 |
| 10 | **Description and naming** follow the project convention (see below). Every Flow has a description saying what starts it, what it does, its known limits and the ticket key | labels, API names and descriptions are the only way to document what a Flow does [verified, Salesforce Help "Plan for Success with Flow Builder Best Practices"] | `flow:MissingDescription` (raise to severity 3 in project config); review |
| 11 | **Tests:** a Flow test or Apex test per outcome, bulk 251+ records for record-triggered Flows (crosses the 200-record batch), bypass on/off, and a fault-path test where the element can fail that asserts the data outcome (rolled back, or partial save logged) | proves rules 2, 4, 5, 9, 13 | `testing.md`; G4 |
| 12 | **Activation is verified, not assumed.** After every deploy, query `FlowDefinitionView` (`IsActive`, `ActiveVersionId`). When a Flow replaces another automation, activate the new one first, verify, then deactivate the old one in a separate step | by default, Flows active in a sandbox deploy to production as inactive unless "Deploy processes and flows as active" is on, and that setting covers processes and autolaunched Flows only [verified, Salesforce Help "Deploy Processes and Flows as Active"]; `FlowDefinitionView` exposes `IsActive` and `ActiveVersionId` [verified, Object Reference "FlowDefinitionView"]. Salesforce's own migration steps also activate the new Flow before deactivating the old automation [verified, Salesforce Help "Move Processes and Workflows to Flow Builder with the Migrate to Flow Tool"] | release checklist (07); PR-13 |
| 13 | **Every fault path decides stop or continue, on purpose.** *Stop*: in a record-triggered Flow, end the fault path with a Custom Error element (rolls back the triggering change and shows the message); in a screen Flow, use Roll Back Records. *Continue*: log, alert an owner, and say in the Flow description why a partial save is acceptable. Logging alone is a *continue* | with a fault path, Salesforce does not block the triggering change and does not roll back the transaction in record-triggered and autolaunched Flows; a screen Flow rolls back only with a Roll Back Records element; without a fault path all three roll back [verified, Salesforce Help "Default Flow Error Handling"]. A Custom Error element in the fault path rolls back the triggering change [verified, Salesforce Help "Custom Error Element"]. Roll Back Records exists only in screen Flows [verified, Metadata API "Flow", FlowRecordRollback] | review; fault-path test (rule 11) |
| 14 | **Screen Flows write once, after the last screen that collects the data.** Dependent records are created in one transaction; collect updates across screens and save them together. Logs from a fault path that rolls back are published as a Platform Event so they survive (`../architecture/error-handling-logging.md` rule 3) | screens and local actions end a transaction, so records saved before a screen stay committed and Roll Back Records can't undo them; users who go back and forward repeat the writes [verified, Salesforce Architects "Building Forms" decision guide; Previous-button duplicates: med, Salesforce Ben "10 Mistakes Salesforce Architects Make When Scaling Flow"] | review; screen Flow test with back navigation |

## Structure and naming
| Item | Convention | Example |
|---|---|---|
| API name and label | the project's naming document (an established org style wins); the name says what the Flow does | — |
| Description | what starts it · what it does · known limits · ticket key; also describe elements, resources and versions [verified, Salesforce Help "Plan for Success with Flow Builder Best Practices"] | — |
| Elements | label and API name say what the element does [verified, same source] | `Get Account Records` |
| Variables and formulas | name says what the resource holds [verified, same source] | `ThreeDaysFromToday` |
| Subflows | one reusable job each, typed input / output variables, own description | — |

Rules of thumb [high]:
- **One job per Flow.** Split by outcome, not by "everything that happens on Account update". A Flow that needs scrolling to understand is two Flows.
- **Order explicitly** when several record-triggered Flows run on the same object and timing: set the trigger order. Trigger order is not recursion control.
- **Decisions read like requirements:** outcome names say the business condition (`isHighValueRenewal`), not `Outcome1`.
- **No logic in formulas you can't test:** complex formulas belong in a formula resource with a clear name, or in Apex invocable code if they need unit tests.
- **Reuse with subflows or invocable Apex**, not copy-paste. Apex is the better home for complex collection processing, callouts with retries, or anything that needs unit tests without DML.
- **Unused variables, unreachable elements and default copy names** are clean-up debt; the analyzer finds them (`flow:UnusedResource`, `flow:UnreachableElement`, `flow:DefaultCopy`).

## Flow or Apex for this job
The object-level choice is ARCH-001 (`../architecture/trigger-framework.md`). Within that choice, these signals point to Apex or invocable Apex for one job [high, Salesforce record-triggered decision guide]:
- complex collection processing (maps, de-duplication, sorting beyond what Flow handles well);
- high data volume (batch and integration loads, not only UI saves);
- callouts that need retries, response parsing or error mapping;
- logic that needs fast unit tests with mocks;
- an object that already has dense Apex automation, so adding Flows creates mixed ordering.

Flow is the better fit for simple same-record defaults (before save), guided screens, schedule-driven updates and admin-maintained logic with low volume.

## Type-specific practices
| Type | Do | Avoid |
|---|---|---|
| Record-triggered, before save | field defaults and derivations on `$Record`; no DML elements needed | Get Records chains that belong in after-save |
| Record-triggered, after save | related records, actions; asynchronous path for callouts and slow work | updating `$Record` again (use before-save); callouts in the immediate path |
| Scheduled | put the record filter on the start element, which runs the Flow once per matching record; no Loop that re-queries the same object [high, sf-skills `automation-flow-generate`] | one interview processing everything in a loop |
| Autolaunched (no trigger) | typed input / output variables; behave like a function; called from Apex, other Flows or agents | reading global state the caller can't control |
| Screen | user context; validate input on the screen; clear error text in the users' language; fault path rolls back (rule 13), shows a friendly message and logs the detail; one write after the last data screen (rule 14) | system context without sharing; raw error messages to users |
| Platform-event-triggered | idempotent (an event can be delivered again); log failures | assuming order between events |
| Agentforce action | input / output variable names and descriptions are the agent's interface: write them for the agent (see `agentforce.md`) | vague variable names; side effects the action description doesn't mention |

## AI-assisted building
- Use Salesforce's `automation-flow-generate` skill (DX MCP `execute_metadata_action`) to generate Flow XML: it grounds on the org schema first. Our rules add: entry criteria, fault paths, naming and bypass are checked on the output before the Flow counts as built. The skill forbids hand-editing generated XML; if the output breaks a rule here, regenerate with a clearer prompt or make a targeted fix and record it on the ticket.
- Split a multi-Flow request into one Flow per prompt (same as the official skill).
- The AI never activates a Flow in production and never deploys it there (HG-09). It may deploy to a write-allowed sandbox (HG-11).
- Field and object names in the prompt must exist in the project or the org (AI-02); `ticket_lint.py` checks ticket references.

## Anti-patterns
"Mega Flow" per object · DML in loops · after-save update of the triggering record · no entry criteria · missing fault paths · hard-coded IDs · callouts in the synchronous path · system context without a reason · Flow and Apex writing the same field · copy-pasted logic across Flows instead of a subflow · relying on a default Flow error email · a fault path that only logs in a Flow that should stop · writes before each screen in a multi-screen Flow · activating by hand in production without a release · Process Builder or Workflow Rules for new work.

## Enforcement
- Code Analyzer flow engine in CI and `dev_cycle.py dod`. Mapped in `../../guardrails/analyzer-map.yaml`: HG-01 `flow:PreventPassingUserDataIntoElementWithoutSharing`, HG-02 `flow:DbInLoop`, HG-03 `flow:HardcodedId`, rubric `flow:MissingFaultHandler`.
- Not mapped yet, but recommended for project config (proposal, needs approval per PR-14): `flow:TriggerEntryCriteria`, `flow:TriggerCallout`, `flow:TriggerWaitEvent`, `flow:SameRecordUpdate`, `flow:CyclicSubflow`, `flow:MissingNextValueConnector`, `flow:MissingDescription`, `flow:UnusedResource`, `flow:UnreachableElement`, `flow:DefaultCopy`.
- Evaluation (01) measures fault-path coverage, hard-coded IDs and double writes per object (rubric `automation.*`).

## Sources
- Salesforce Architects, Record-Triggered Automation Decision Guide — architect.salesforce.com/docs/architect/decision-guides/guide/record-triggered.html
- Salesforce Help, Define the Run Order of Record-Triggered Flows — help.salesforce.com (article `platform.flow_task_trigger_run_order`)
- Salesforce Help, Plan for Success with Flow Builder Best Practices — https://help.salesforce.com/s/articleView?id=platform.flow_prep_bestpractices.htm&type=5 (release 264)
- Salesforce Help, Default Flow Error Handling — https://help.salesforce.com/s/articleView?id=platform.flow_build_logic_fault_default.htm&type=5 (release 264)
- Salesforce Help, Customize What Happens When a Flow Fails — https://help.salesforce.com/s/articleView?id=platform.flow_build_logic_fault.htm&type=5 (release 264)
- Salesforce Help, Custom Error Element — https://help.salesforce.com/s/articleView?id=platform.flow_ref_elements_custom_error.htm&type=5 (release 264)
- Metadata API Developer Guide, Flow (FlowRecordRollback) — https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_visual_workflow.htm
- Salesforce Architects, Building Forms decision guide — https://architect.salesforce.com/docs/architect/decision-guides/guide/build-forms.html
- Salesforce Ben, 10 Mistakes Salesforce Architects Make When Scaling Flow — https://www.salesforceben.com/10-mistakes-salesforce-architects-make-when-scaling-flow/ (community source, Nov 2026)
- Salesforce Help, Select Flow and Process Error Email Recipients — https://help.salesforce.com/s/articleView?id=platform.flow_troubleshoot_error_email.htm&type=5 (release 264)
- Salesforce Help, Deploy Processes and Flows as Active — https://help.salesforce.com/s/articleView?id=platform.flow_distribute_deploy_active.htm&type=5 (release 264)
- Salesforce Help, Move Processes and Workflows to Flow Builder with the Migrate to Flow Tool — https://help.salesforce.com/s/articleView?id=platform.flow_migrate_to_flow.htm&type=5 (release 264)
- Salesforce Object Reference, FlowDefinitionView — https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_flowdefinitionview.htm
- Salesforce Code Analyzer, Flow Scanner Rules Reference (MissingFaultHandler, HardcodedId) — https://developer.salesforce.com/docs/platform/salesforce-code-analyzer/guide/rules-flow.html
- Salesforce Code Analyzer v5, flow engine rules (15 rules, verified 2026-11-20 with `sf code-analyzer rules --rule-selector flow`)
- forcedotcom/sf-skills `automation-flow-generate` (cloned 2026-11-20, commit 431c50f)
