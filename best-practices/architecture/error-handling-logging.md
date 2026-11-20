# Error handling and logging

**Verdict:** classify every error, show users only what they can act on, never swallow, log through **one** framework whose entries survive a rollback, and alert an owner on repeated failures. Which framework is a human choice (ARCH-004): keep the existing one; if none exists, ask.
Confidence: [high] principles; framework details [med] (check the project's release notes).

## Error classes and handling
| Class | Example | Handling |
|---|---|---|
| User / validation | missing field, wrong status | `addError` on the record or field; clear message; no stack traces to users |
| Business rule | credit limit exceeded | domain exception with a business message; logged at INFO/WARN |
| Transient technical | callout timeout, row lock | retry from async with cap + backoff; then dead-letter |
| Permanent technical | 4xx from remote, bad data | no retry; dead-letter record + alert owner |
| Defect | NullPointerException | log ERROR with stack + context; alert; fix via bug ticket |

## Non-negotiables
1. **No empty catch blocks**; catch only to add context, translate, or retry. (`pmd:EmptyCatchBlock`)
2. **Custom exception per domain/service** (`InvoiceServiceException`), wrapping the cause.
3. **Log entries survive rollback**: publish logs via Platform Event (or save before rethrowing) — a log written with plain DML disappears when the transaction rolls back.
4. **One correlation id** per request/process, passed through Apex, Flow, callouts and async jobs.
5. **Every Flow DML / callout / action has a fault path** that logs. (`flow:MissingFaultHandler`, tagged Project)
6. **No `System.debug` in production code paths**; use the logger. (`pmd:AvoidDebugStatements`, project rule `UseProjectLogger`)
7. **No personal data or secrets in logs**; mask by default.
8. **Log levels per user/profile**, low by default; raise temporarily for troubleshooting.
9. **Retention**: scheduled purge of old logs (e.g. 30–90 days) [low: set per project].
10. **Alerting**: repeated ERRORs or dead-letter growth notify an owner (email, Slack, case).
11. **LWC**: one error-to-message helper; user sees a toast with an actionable message, details go to the logger.

## Options (ARCH-004 logging framework)
| | A. Nebula Logger (open source) | B. In-house minimal logger | C. Platform only (debug logs, Event Monitoring) |
|---|---|---|---|
| What | native logging for Apex, LWC/Aura, Flow, OmniStudio; publishes log events via Platform Event; settings per user/profile; plugin framework | custom Log object + Platform Event + small Apex/Flow API | no custom logging; rely on debug logs and Shield Event Monitoring |
| Install | unlocked package, managed package (namespace; some features missing), or bundle the open-source metadata | built by the team | nothing |
| Effort | low to adopt; learn its settings | medium to build, ongoing maintenance | none |
| Coverage | Apex + Flow + LWC in one log | what you build | debug logs are short-lived and per-user |
| Risk | external dependency, upgrades | gaps and drift | errors in production go unseen |
| Signals | most projects with Apex + Flow + LWC | strict no-dependency policy, very small scope | tiny config-only orgs (rarely acceptable) |

**Package policy:** existing logger used consistently → keep-existing; none → always ask (fill ARCH-004 with facts, no default).

## Sources
Nebula Logger repository and wiki (github.com/jongpie/NebulaLogger); Salesforce Architects Step-Based Async Framework (fault paths + logging via Platform Events); Apex Developer Guide — exceptions.
