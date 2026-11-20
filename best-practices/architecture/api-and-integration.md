# API and integration design

**Verdict:** pick the integration pattern first, then the technology; prefer standard Salesforce APIs and events over custom code; every integration is idempotent, observable, limit-aware and uses Named/External Credentials. Two choices usually need a human: inbound API style (ARCH-002) and topology (ARCH-003).
Confidence: platform limits [verified from Salesforce docs, 2026-11]; design rules [high]; option defaults [med].

## 1. Choose the pattern (Salesforce integration patterns)
| Pattern | Direction · timing | Typical tech | Use when |
|---|---|---|---|
| Remote Process Invocation — Request and Reply | SF → remote, sync | Apex callout via Named Credential; Flow HTTP callout | user needs the answer now (price, credit check) |
| Remote Process Invocation — Fire and Forget | SF → remote, async | Platform Event, Queueable callout, outbound messaging | remote work can finish later |
| Batch Data Synchronization | both, batch | Bulk API 2.0, ETL/middleware, CDC | periodic large sync |
| Remote Call-In | remote → SF | REST/Composite/Bulk API, custom Apex REST | external system creates/reads/updates SF data |
| UI Update Based on Data Changes | SF → UI | Platform Events / CDC + LWC (empApi) | screens must refresh on changes |
| Data Virtualization | SF reads remote live | Salesforce Connect / External Objects | data stays in source, shown in SF |
| High-Frequency Data Replication | near real time, high scale | CDC + Pub/Sub API, middleware | keep a copy in sync at scale |

## 2. Inbound (remote call-in)
Non-negotiables:
- Authenticate with OAuth 2.0 via a Connected App / External Client App; dedicated integration user with least-privilege permission set (HG-01, PR-06).
- **Idempotent writes:** upsert on an External ID, or store an idempotency key per request and return the stored result on retry. Retries must not create duplicates.
- **Bulk by design:** accept lists; > ~2,000 records → Bulk API 2.0; smaller sets → bulkified synchronous calls (Composite / sObject Collections).
- Errors are honest: correct HTTP status codes, never `200` with an error body; per-record results for bulk requests.
- Correlation id in and out (header), logged on both sides.

**Custom Apex REST** (only when ARCH-002 says so) — design rules:
| Rule | Detail |
|---|---|
| Version in the path | `@RestResource(urlMapping='/v1/orders/*')`; new major version for breaking changes; additive changes stay in v1 |
| Resources, not verbs | `/v1/orders/{externalId}`, not `/createOrder` |
| Thin resource class | parse + validate + map → call a service class; no business logic in the REST class |
| Security | `with sharing`, queries `WITH USER_MODE`, validate every input (HG-01) |
| Consistent error body | one JSON error shape for all endpoints (e.g. code, message, field, correlationId — RFC 7807 style) |
| Contract first | publish an OpenAPI spec per version; contract tests in CI |
| Limits | one request = one transaction: cap payload size, document it |

## 3. Outbound (callouts)
| Rule | Why / limit |
|---|---|
| Named Credential + External Credential for every endpoint; no URLs, tokens or secrets in code (HG-03) | `pmd:ApexSuggestUsingNamedCred`, `pmd:ApexInsecureEndpoint` |
| Set an explicit timeout per call | default timeout is 10 s; per call max 120 s; **cumulative max 120 s per transaction**; max **100 callouts per transaction** |
| No callout after DML in the same transaction | pending operations block callouts → do DML after, or go async |
| No callouts from trigger context | hand off to Queueable (with Finalizer for retry/logging) or Platform Event |
| Retry only idempotent operations, with backoff, from async context | avoid duplicate side effects; cap attempts; dead-letter record after the last try |
| Circuit breaker / kill switch in Custom Metadata | stop calling a failing system without a deploy |
| Respect org read-only mode (`System.getApplicationReadWriteMode()`) | maintenance windows: callout succeeds but follow-up DML fails |
| Mock in tests (`HttpCalloutMock`); contract test against a sandbox endpoint | unit tests can't make real callouts |

## 4. Events
- **Platform Events** for business events ("Order Placed"); **Change Data Capture** for record-change replication; external subscribers via Pub/Sub API [med].
- Publish behaviour: choose publish-after-commit for events that must reflect saved data [med].
- Subscribers are idempotent (events can be redelivered) and store the last replay id.
- Event schema = contract: versioned, documented, additive changes only.

## 5. Observability and limits
- Every integration logs: correlation id, direction, endpoint, status, duration, record ids, error — to the project logging framework.
- Alert an owner on repeated failures; dead-letter records are reviewed daily.
- Watch the org API request allocation (`/limits`) and Bulk API daily allocations; budget per integration.

## Anti-patterns
Point-to-point spaghetti with no inventory · callouts in triggers · synchronous chains across 3+ systems in a user transaction · retries without idempotency · hardcoded endpoints/tokens · one giant "do everything" Apex REST endpoint · swallowing integration errors · integration user with admin profile.

## Enforcement
HG-01, HG-02, HG-03 via analyzer map · `flow:TriggerCallout` · tests rubric (integration: happy + main failure + timeout) · ticket field `metadata` must list Named Credentials and endpoints · decision cards ARCH-002, ARCH-003.

## Sources
- Salesforce Integration Patterns and Practices — pattern selection guide (developer.salesforce.com)
- Apex Developer Guide — Callout Limits and Limitations
- Bulk API 2.0 Developer Guide — introduction and limits
- Salesforce Architects decision guides (async processing, event-driven architecture)
- General REST practice: URI versioning, idempotency keys, RFC 7807 problem details
