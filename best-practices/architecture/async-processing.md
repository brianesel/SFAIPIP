# Async processing

**Verdict:** keep business logic independent of the async mechanism; Queueable (with Finalizers) is the default for custom async work, Batch only where it is the better fit, `@future` not in new code; filter before you enqueue and watch async limits. No decision card — the tool is chosen per use case with the table below.
Confidence: [high] for principles; tool details [med] (async features evolve each release — e.g. Apex Cursors).

## Non-negotiables
| # | Rule | Why |
|---|---|---|
| 1 | Business logic lives in service classes; Queueable / Batch / event subscribers only orchestrate | same logic runs sync, async or from an event without duplication |
| 2 | Check entry criteria **before** enqueueing | async jobs that do no work still burn org-wide async limits |
| 3 | No `@future` in new code; Queueable instead | Queueable has job ids, complex params, chaining, Finalizers |
| 4 | Every async job is idempotent and safe to retry | jobs and events can run twice |
| 5 | Failures are captured: Finalizer (Queueable) or `finish()` (Batch) logs outcome, retries transient errors with a cap, writes a dead-letter record otherwise | silent async failures are the hardest bugs |
| 6 | Don't start Queueables from inside a Batch for the same process; chain the next Batch from `finish()` | keeps one execution context per process |
| 7 | Monitor async limits centrally (scheduled job reads org limits, stores them, alerts at thresholds) | peaks exceed the daily async Apex limit without warning |
| 8 | Scheduled work prefers Scheduled Flow (deployable as metadata) calling an invocable action, or Scheduled Apex delegating to Queueable/Batch | schedules set by hand in Setup don't travel with deployments |

## Which tool
| Use case | Default | Why / note |
|---|---|---|
| Small deferred unit of work, callout after DML, work from a trigger | Queueable (+ Finalizer) | fast start, job id, chaining |
| Very large data set (millions), DB maintenance | Batch Apex — or Queueable + Apex Cursors where available | Cursors allow multiple fetches per transaction [med: check feature status in your release] |
| Time-based | Scheduled Flow / Scheduled Apex → Queueable or Batch | keep the scheduler thin |
| Decouple producers from several consumers | Platform Events | custom payload, independent subscribers; hourly limits apply |
| Replicate record changes to other systems | Change Data Capture | standard change payloads |
| Record-triggered follow-up in Flow | Asynchronous Path / Scheduled Path | off the user's transaction |
| Long-running UI callout | Continuation (Visualforce/Aura/LWC) | frees the request thread |

## Anti-patterns
`@future` chains · enqueue-then-filter · retry without idempotency · Batch → Queueable fan-out for one process · async errors only in debug logs · logic copied into each async wrapper.

## Enforcement
Project rule `NoFutureMethods` (template, PRJ-01) · flow `TriggerCallout` · review checklist rows 1, 2, 4, 5 · tests: Finalizer path + retry cap.

## Sources
Salesforce Architects: Asynchronous Processing decision guide; Step-Based Async Framework; blog "Design a Resilient Async Architecture That Scales With Demand" (2026); Apex Developer Guide — Asynchronous Apex.
