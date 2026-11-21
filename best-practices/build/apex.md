# Apex

**Verdict:** Apex is built for the bulk case, not the single record: every entry point takes a collection, queries and DML sit outside loops, access is stated explicitly (user mode by default, system mode only with a reason), logic lives in services and domain classes that a trigger, Flow, LWC or async job can all call, and tests prove 251+ records, a non-admin user and the failure path. Code design (naming, method size, DI) is scored by `../clean-apex.md`; this page is the build-level checklist around it.
Sources: see end. Confidence: non-negotiables [high]; numbers marked inline; analyzer rule names [verified] against `sf code-analyzer rules --rule-selector all` on 2026-11-20.

## Scope
Apex classes and triggers written or changed in a ticket: services, selectors, domain classes, trigger handlers, invocable actions, `@AuraEnabled` controllers, REST resources, async jobs and their tests. Out of scope here (link, don't repeat): code-design rubric `../clean-apex.md`, trigger framework choice `../architecture/trigger-framework.md` (ARCH-001), async tool choice `../architecture/async-processing.md`, error classes and logging `../architecture/error-handling-logging.md` (ARCH-004), user/system mode and the API v67.0 change `../architecture/security-sharing.md`.

## Non-negotiables
| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | **Bulk by signature.** Public methods take `List`/`Set`/`Map`; a single-record overload only wraps the bulk method. No SOQL, DML, callout or `Database.*` call inside a loop | governor limits count per transaction, and a trigger receives up to 200 records per chunk [high, Apex Developer Guide "Triggers and Bulk Requests"] | HG-02; `pmd:OperationWithLimitsInLoop`; `sfge:AvoidDatabaseOperationInLoop` |
| 2 | **Only touch what changed.** Compare with `Trigger.oldMap` (or prior state) before adding a record to a query filter or update list | fewer rows, less CPU, no recursion from no-op updates | review; bulk + recursion tests (`trigger-framework.md` rule 5) |
| 3 | **Access is explicit on every database call.** `WITH USER_MODE` / `AccessLevel.USER_MODE` by default; `SYSTEM_MODE` only with a comment saying why. `AccessLevel.SYSTEM_MODE` lifts CRUD/FLS, **not** record sharing: sharing comes from the class keyword [high, Apex Developer Guide "Enforce User Mode for Database Operations"] | the v67.0 defaults change silently what un-annotated code returns | HG-01; `pmd:ApexCRUDViolation`; `sfge:ApexFlsViolation`; `pmd:AvoidSecurityEnforcedOldApiVersion` |
| 4 | **Every class declares sharing.** Entry points (`@AuraEnabled`, REST, invocable) `with sharing`; services and selectors `inherited sharing`; `without sharing` only in a small inner or helper class with a recorded reason (ADR) | an undeclared class behaves differently by API version; elevated access must be narrow and visible | HG-06; `pmd:ApexSharingViolations`; `sfge:DatabaseOperationsMustUseWithSharing` |
| 5 | **Layers keep their job.** Trigger → handler (routing) → service (orchestration) → domain (rules on in-memory records) and selector (all SOQL); DML via the service or unit of work. Follow the pattern register for the area | the same logic must run from a trigger, Flow, LWC, batch or agent without copies | PR-06; rubric `design.layering`; `pmd:AvoidLogicInTrigger` (HG-07) |
| 6 | **No hard-coded IDs, endpoints, secrets or business literals.** Record types by `DeveloperName` (`Schema.SObjectType.X.getRecordTypeInfosByDeveloperName()`), queues by `DeveloperName` + `Type = 'Queue'`, thresholds in Custom Metadata, endpoints in Named Credentials | IDs differ per org; literals hide business rules | HG-03; `pmd:AvoidHardcodingId`; `pmd:ApexSuggestUsingNamedCred`; `../architecture/configuration.md` |
| 7 | **Dynamic SOQL binds variables**; field and object names from input are checked against an allow-list or `Schema` describe. No generic "object + fields + where from the client" controllers | SOQL injection and accidental data exposure | `pmd:ApexSOQLInjection`; review |
| 8 | **No silent failures.** No empty catch; catch only to add context, translate or retry; one custom exception per service; partial-success DML (`Database.update(records, false)`) only when every `SaveResult` error is handled | swallowed errors become data loss nobody sees | `pmd:EmptyCatchBlock`; `error-handling-logging.md` |
| 9 | **Async is chosen from the table, not by habit.** Queueable (+ Finalizer) by default, no `@future` in new code, filter before enqueue | see `async-processing.md` | `pmd:AvoidFutureAnnotation`; `pmd:QueueableWithoutFinalizer`; project rule `NoFutureMethods` |
| 10 | **API version is the project's pinned version** for new classes; raising an old class to v67.0+ is its own change with regression tests | v67.0 switches database operations to user mode and removes `WITH SECURITY_ENFORCED` [verified, see `security-sharing.md`] | rubric `design.api_version`; `regex:AvoidOldSalesforceApiVersions` |
| 11 | **Tests before code** (PR-08) and per `../testing.md`: factory data, no `SeeAllData`, one behavior per test, bulk 251+, a `System.runAs` test with a minimum-access user + the ticket's permission set, a negative test, async asserted after `Test.stopTest()` | proves rules 1–4 and 8; admin-only tests pass code that fails for real users | HG-04, HG-05; `pmd:ApexUnitTestShouldNotUseSeeAllDataTrue`; `pmd:ApexUnitTestClassShouldHaveAsserts`; `pmd:ApexUnitTestClassShouldHaveRunAs`; G4 |

## Governor limits to design against
Per-transaction limits are the reason for rules 1–2. Common ones [high, Apex Developer Guide "Execution Governors and Limits"; re-check the current table before relying on a number]:

| Limit | Synchronous | Asynchronous |
|---|---|---|
| SOQL queries | 100 | 200 |
| Records retrieved by SOQL | 50,000 | 50,000 |
| DML statements | 150 | 150 |
| Records processed by DML | 10,000 | 10,000 |
| CPU time | 10,000 ms | 60,000 ms |
| Heap size | 6 MB | 12 MB |

Practices [high, sf-skills `platform-apex-generate`]:
- Build `Map<Id, SObject>` from a query in one step; group children with `Map<Id, List<SObject>>` built in one loop; use `Set.contains()` for membership.
- Fetch parent + children in one query with a relationship subquery; use `AggregateResult` for counts and sums.
- Read Custom Metadata with `getAll()` / `getInstance()`, not SOQL; cache per transaction in a `private static Map`, lazily filled.
- Describe calls: request only what you need (`pmd:EagerlyLoadedDescribeSObjectResult`, `sfge:AvoidMultipleMassSchemaLookups`).
- Queries in a trigger path must be selective on large objects (`../architecture/data-model-ldv.md`); a query with no filter or limit is flagged by `pmd:AvoidNonRestrictiveQueries`.
- For hot paths, assert headroom in the bulk test: `Assert.isTrue(Limits.getQueries() < Limits.getLimitQueries(), '...')`.

## Class roles and naming
Use the pattern register first; where it says nothing, these defaults apply [high, sf-skills `platform-apex-generate`; ARCH-001 decides the trigger side].

| Role | Name | Sharing | Owns | Must not contain |
|---|---|---|---|---|
| Trigger | `<Object>Trigger` | n/a | one framework call | logic (HG-07) |
| Handler / trigger action | `<Object>TriggerHandler` or `TA_<Object>_<Action>` (TAF) | `with sharing` or `inherited sharing` per framework | routing by context | SOQL/DML written inline |
| Service | `<Object or Area>Service` | `inherited sharing` | orchestration, transactions | inline SOQL; UI types |
| Domain | `<Object>Domain` | `with sharing` | defaults, derivations, validation on in-memory lists | SOQL, DML, callouts |
| Selector | `<Object>Selector` | `inherited sharing` | all SOQL for the object, one shared field list, `WITH USER_MODE` | business decisions |
| Invocable | `<Verb><Object>Action` | `with sharing` | `List<Request>` → `List<Response>` with `isSuccess` / `errorMessage` | single-record signatures |
| Controller | `<Feature>Controller` | `with sharing` | `@AuraEnabled` boundary; `cacheable=true` only for reads | business logic |
| Async | `<Purpose>Queueable` / `Batch` / `Schedulable` | `with sharing` unless recorded | orchestration only; calls the service | copied logic |
| Exception | `<Service>Exception` | none | message + cause | — |
| Test | `<Class>Test`, factory `TestDataFactory` | n/a | one behavior per method | `SeeAllData` |

Method names start with a verb; maps are `<value>By<key>` (`accountsById`); no abbreviations (`acc`, `rec`). `global` only when a managed package or `@RestResource` requires it (`pmd:AvoidGlobalModifier`).

## Exceptions at the boundaries
- **Trigger:** user-correctable problems → `addError` on the record or field, in the users' language (Custom Label). Do not throw from deep code for something a user can fix.
- **`@AuraEnabled`:** catch, log the cause, rethrow as `AuraHandledException` with a user-safe message. Call `setMessage(msg)` on it, otherwise tests and logs read "Script-thrown exception" [med: observed in delivery projects]. Throw `AuraHandledException` only at this boundary, never from services or batch.
- **Invocable:** return errors in the response; throw only for unrecoverable cases (that sends the Flow down its fault path).
- **Async:** Finalizer or `finish()` records the outcome; retries only for transient errors, with a cap (`async-processing.md` rule 5).
- Preserve the cause: `new InvoiceServiceException('context', cause)`. No personal data in messages or logs.

## Test data and access in tests
- One `TestDataFactory`: bulk-first methods (`createAccounts(Integer count, Boolean doInsert)`), single-record methods delegate to them; set every field that validation rules require; make values unique where duplicate rules match [high, sf-skills `platform-apex-test-generate`].
- Record types by `DeveloperName`; standard price book via `Test.getStandardPricebookId()`.
- **Non-admin user per access-relevant test:** create a user on a minimum-access profile, assign the ticket's permission set (group) in the test, run the act inside `System.runAs`. `runAs` applies the user's record sharing; CRUD/FLS are applied only where the code runs in user mode [high, Apex Developer Guide "Using the runAs Method"]. Test both without the permission set (blocked or empty) and with it. Details: `permissions-access.md`.
- **Mixed DML:** inserting setup objects (User, `PermissionSetAssignment`, Group membership) and regular records in one transaction fails with `MIXED_DML_OPERATION`; create setup records inside `System.runAs(new User(Id = UserInfo.getUserId()))` [high, Apex Developer Guide "sObjects That Cannot Be Used Together in DML Operations"].
- Callouts: `Test.setMock` before `Test.startTest()`; one success and one error response at least.
- Assertions use the `Assert` class with a message (`pmd:ApexAssertionsShouldIncludeMessage`); expected values come from the setup, not magic numbers.

## AI-assisted building
- Use Salesforce's `platform-apex-generate` and `platform-apex-test-generate` skills for *how*; they align with rules 1, 4, 6, 7, 9 here. Pipeline differences: the ticket's agreed test set exists before production code (PR-08); per-class coverage is the project minimum (default 85), not 75; tests are written blind to the tester's set (AI-03).
- Before writing, read the pattern register and existing classes for the object (trigger framework, logger, selector base); never add a second pattern for the same concern without PR-06.
- Every object, field, class and method used must exist in the project or the org (AI-02). Look up method signatures (`integration-apex-symbol-table-query`, or read the source) instead of guessing.
- Run Code Analyzer and the tests before reporting; severity 1–2 findings block (HG-10). After two failed fixes on the same error, stop and report (AI-04).
- The AI deploys only to a write-allowed sandbox (HG-11), never to production (HG-09).

## Anti-patterns
SOQL or DML in loops · single-record public methods · logic in the trigger body · static Boolean recursion guards · `without sharing` on a whole service "to make it work" · `SYSTEM_MODE` everywhere after a v67.0 bump · `WITH SECURITY_ENFORCED` in new code · `@future` · empty catch or catch-and-`System.debug` · hard-coded record type or queue IDs · generic dynamic-query controllers · tests without asserts, run only as admin, or with `SeeAllData=true` · one test method that checks five behaviors.

## Enforcement
- Code Analyzer in CI and `dev_cycle.py dod`, mapped in `../../guardrails/analyzer-map.yaml`: HG-01 `pmd:ApexCRUDViolation`, `pmd:ApexSOQLInjection`; HG-02 `pmd:OperationWithLimitsInLoop`, `regex:AvoidGetHeapSizeInLoop`; HG-03 `pmd:AvoidHardcodingId`, `pmd:ApexSuggestUsingNamedCred`, `pmd:ApexInsecureEndpoint`; HG-04 `pmd:ApexUnitTestShouldNotUseSeeAllDataTrue`; HG-05 `pmd:ApexUnitTestClassShouldHaveAsserts`; HG-06 `pmd:ApexSharingViolations`; HG-07 `pmd:AvoidLogicInTrigger`. Rubric: `regex:AvoidOldSalesforceApiVersions`, `pmd:AvoidDebugStatements`, `pmd:ApexAssertionsShouldIncludeMessage`.
- Not mapped yet, recommended for project config (proposal, needs approval per PR-14): `sfge:AvoidDatabaseOperationInLoop`, `sfge:ApexFlsViolation`, `sfge:DatabaseOperationsMustUseWithSharing`, `pmd:OperationWithHighCostInLoop`, `pmd:AvoidSecurityEnforcedOldApiVersion`, `pmd:AvoidFutureAnnotation`, `pmd:QueueableWithoutFinalizer`, `pmd:ApexUnitTestClassShouldHaveRunAs`, `pmd:EagerlyLoadedDescribeSObjectResult`, `pmd:AvoidNonRestrictiveQueries`, `pmd:AvoidGlobalModifier`. The sfge engine needs a full compile graph and is slower; run it in CI, not on every save.
- Rubric `code-design.yaml` and `tests.yaml` score the rest at evaluation (01) and DoD (G4).

## Sources
- Apex Developer Guide: Execution Governors and Limits; Triggers and Bulk Requests; Enforce User Mode for Database Operations; Using the runAs Method; sObjects That Cannot Be Used Together in DML Operations — developer.salesforce.com/docs/atlas.en-us.apexcode.meta
- Salesforce Summer '26 release notes (API v67.0 Apex security defaults), summarised in `../architecture/security-sharing.md`
- forcedotcom/sf-skills `platform-apex-generate`, `platform-apex-test-generate` (cloned 2026-11-20, commit 431c50f)
- Salesforce Code Analyzer v5 rule inventory (verified 2026-11-20)
