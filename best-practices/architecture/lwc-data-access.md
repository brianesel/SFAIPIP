# LWC data access

**Verdict:** use the least code that works, in this order: **base record components → Lightning Data Service wire adapters / GraphQL → Apex**. Apex is for what LDS can't do (multi-record transactions, complex logic, unsupported objects). Keep caches consistent after Apex writes. No decision card.
Confidence: [verified from the LWC Developer Guide, 2026-11]; component patterns [high].

## Choose the data path
| Need | Use | Note |
|---|---|---|
| View / edit / create one record with standard layout behaviour | `lightning-record-form`, `-edit-form`, `-view-form` | validation rules, FLS, help text handled |
| Custom UI, one or a few records, reactive | LDS wire adapters (`lightning/ui*Api`) e.g. `getRecord` | managed cache; no API usage; ask only the fields you need |
| Several queries or objects in one request, filtering, pagination | GraphQL wire adapter (`lightning/graphql`) | returns only queried fields |
| Create / update / delete one record | `createRecord`, `updateRecord`, `deleteRecord` | each call is its own transaction |
| Several records in **one** transaction, complex logic, objects LDS doesn't support (incl. Custom Metadata) | Apex: `@AuraEnabled(cacheable=true)` for reads, imperative calls for writes | Apex data is not managed by LDS |

## Rules
1. After Apex changes records, call `notifyRecordUpdateAvailable(recordIds)` so LDS wires refresh; refresh Apex wires with `refreshApex`. `refreshApex` for non-Apex wire adapters is deprecated.
2. Don't mix Apex and GraphQL for fetch + search of the same data; LDS and Apex don't share a cache.
3. Read Apex methods are `cacheable=true`; write methods aren't.
4. Apex controllers: `with sharing`, queries `WITH USER_MODE`, thin — call service classes (same layering as triggers).
5. Data flows parent → child via properties; events flow up; Lightning Message Service between unrelated components.
6. One error helper turns any error (LDS, Apex, JS) into a user message; details go to the logger (`error-handling-logging.md`).
7. Security: no `innerHTML`/`lwc:dom="manual"` with user data; ESLint LWC rules are a gate (`design.lwc_eslint`).
8. Tests: Jest per component; mock wire adapters and Apex (`@salesforce/sfdx-lwc-jest`).

## Anti-patterns
Apex for simple single-record reads · `getRecord` asking for whole layouts when 3 fields are needed · forgetting to notify LDS after Apex DML (stale UI) · business logic in the component · several components each querying the same data instead of sharing it.

## Sources
LWC Developer Guide — "Data Guidelines", "Display Data in a Table with Inline Editing" (developer.salesforce.com).
