# Architecture guides

Reference architectures for recurring Salesforce design areas. Each guide gives:
**non-negotiables** (always true, enforced by guardrails) · **options** where reasonable teams differ · **package policy / signals** · **anti-patterns** · **how it is checked** · **sources**.

When no option is clearly better for every project, the choice goes to a **decision card** in `decisions/` (copied into each project's `docs/decisions/`). The AI fills the project facts; a named human chooses (PR-15). The choice is recorded in `guardrails.project.yaml → architecture` and an ADR. G1 does not pass while a required card is `pending`.

| Guide | Decision card | Package policy |
|---|---|---|
| `structure-level.md` | ARCH-007 structure level | keep existing if consistent; else AI proposes from drivers, human decides |
| `trigger-framework.md` | ARCH-001 trigger framework | keep existing; **none yet → always ask** |
| `api-and-integration.md` | ARCH-002 inbound API style | **decide per interface** in `docs/design/integration-inventory.md` (pending rows block G2) |
| `api-and-integration.md` | ARCH-003 integration topology | per project; usually mixed |
| `async-processing.md` | — (per use case table) | Queueable + Finalizer default; no new `@future` |
| `error-handling-logging.md` | ARCH-004 logging framework | keep existing; none yet → ask |
| `data-model-ldv.md` | ARCH-005 archiving | only when an object heads past ~1M records; else `n/a` |
| `security-sharing.md` | — (rules) | permission-set-led; explicit user mode; plan API v67.0 |
| `configuration.md` | — (per-value table) | Custom Metadata for deployable config; hierarchy settings for per-user; labels; credentials |
| `lwc-data-access.md` | — (order of preference) | base components → LDS / GraphQL → Apex; notify LDS after Apex writes |
| `devops-packaging.md` | ARCH-006 delivery model | keep existing if it works; none / change sets → ask |
| `branching-environments.md` | ARCH-008 branching strategy · ARCH-009 sandbox strategy | keep existing if it works; else asked in setup (`sfg-setup`), a named human chooses; stored in `delivery.environments` |
