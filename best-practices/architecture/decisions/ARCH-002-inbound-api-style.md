# ARCH-002 — Inbound API style (decided per interface)

Package policy (2026-11-20): **decide per interface.** There is no project-wide default. Every inbound interface gets a row in `docs/design/integration-inventory.md` with its style; rows with `Status: pending` block the design sign-off (G2).

## Options per interface
| | Standard APIs (REST sObject / Composite / Bulk 2.0, External ID upsert) | Custom Apex REST facade (`/v1/...`) | Middleware owns the contract (iPaaS), SF exposes standard APIs |
|---|---|---|---|
| Effort | lowest | medium–high (code, tests, versioning) | depends on existing middleware |
| Contract stability | tied to SF data model — field changes leak to clients | stable business contract; model can change behind it | stable at middleware layer |
| Business logic in one call (multi-object, validation) | limited (Composite helps) | full | in middleware or via SF services |
| Bulk / volume | best (Bulk API 2.0 above ~2,000 records) | per-transaction limits | middleware batches |
| Signals | data sync, CRUD, migrations | business operations ("place order"), external partners, many consumers | enterprise with integration team and platform |

## How the AI helps
Fill each inventory row's facts (system, direction, pattern, volume, consumers, idempotency, auth) and list the signals above. The named human sets the style and status.
