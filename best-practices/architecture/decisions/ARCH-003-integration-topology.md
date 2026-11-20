# ARCH-003 — Integration topology

Status: pending
Decided-by:
Date:
Choice:                  <!-- point-to-point | middleware-hub | event-driven | mixed | n/a -->
ADR:

## Question
How are Salesforce and other systems connected overall?

## Options
| | Point-to-point (direct callouts / API calls) | Middleware hub (iPaaS / ESB) | Event-driven (Platform Events, CDC, Pub/Sub, event bus) |
|---|---|---|---|
| Good for | 1–3 integrations, simple contracts | many systems, transformations, central monitoring | many consumers, loose coupling, near real time |
| Cost | lowest start; grows with each link | licence + platform team | design discipline (schemas, replay, idempotency) |
| Failure handling | built per link | central retry, dead-letter, monitoring | consumers own retries; durable replay |
| Risk | spaghetti once > ~3–5 links [low] | single platform dependency | eventual consistency must be acceptable to the business |

## Default by context
≤ 3 integrations, no middleware → point-to-point with the outbound rules · existing middleware or many systems → hub · several consumers of the same business events → event-driven · usually `mixed`, per interface.

## AI proposal
<!-- fill from INT-01..03 answers and the existing landscape -->
