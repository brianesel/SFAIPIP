# Clean Apex

Baseline: *Clean Apex Code* chapter topics + general clean-code practice. Measured by `../guardrails/rubric/code-design.yaml`.

**Verdict:** simple first. The best code is the least code that meets the acceptance criteria and the hard rules, and that the next person understands without help. Prefer, in order: standard feature or configuration → declarative → small code → abstraction. Add a layer, interface or setting only when a second real use exists or a test needs the seam. How much structure a project uses is set once by its structure level (ARCH-007, `architecture/structure-level.md`); within that level, the simplest option wins. Hard rules (HG-01–HG-07) apply at every level: simpler never means less safe.

| Topic | Practice | Measured by |
|---|---|---|
| Simplicity | least code for the AC; no speculative abstraction, wrappers that only forward, settings nobody changes, parameters "for later" | `design.speculative_generality` |
| Naming | intent-revealing names, one word per concept, role suffixes (Service, Selector, TriggerHandler, Test) | `design.naming_*` |
| Do one thing | no boolean flag parameters; ≤ 4 parameters | `design.flag_params`, `design.param_count` |
| Method size | ≤ 30 statements, cognitive complexity < 15, nesting ≤ 3 | `design.method_*`, `design.nesting_depth` |
| Comments | no comments that restate code; why-comments only where the table below requires or allows them | `design.comments_why`, `design.commented_out_code` |
| Null / guard clauses | validate at entry, return or throw early; no defensive checks repeated inside | `design.guard_clauses` |
| Trigger boundaries | decide all-or-nothing vs partial success per entry point; `addError` per record | `design.trigger_boundary` |
| Classes | one responsibility; extension points (interface, strategy) only where a second real variant exists | `design.class_*` |
| Modularity | data access and DML placed per the structure level; low fan-out; no duplication | `design.layering`, `design.coupling`, `design.duplication` |
| Dependency injection | seams where tests or external systems need them, per the structure level; no interface with a single non-test implementation | `design.di_seams` |
| Hygiene | no magic literals, dead code, `System.debug`; current API versions; formatter + ESLint | `design.*` |

## Comments
Default: no comments. A better name, a smaller method or a test explains *what* the code does. Write one line only when the reason lives outside the code: history, the platform, another metadata type, or a business rule.

| Kind | Rule |
|---|---|
| **Forbidden** | comments that restate the code · commented-out code · TODO / FIXME without a ticket key · author or changelog headers (git has them) · section banners |
| **Required** | why `SYSTEM_MODE` or `without sharing` is safe here (HG-01, HG-06) · reason and ticket for any analyzer suppression · platform limit or bug workaround, with a link · ordering dependency on another metadata type ("runs before Flow X sets Status") · ApexDoc / JSDoc on `global`, `@AuraEnabled`, `@api` and `@InvocableMethod` members, or the annotation's `label` / `description` |
| **Allowed** | a non-obvious business rule, with its REQ or ticket key · what a regex or complex formula is meant to match |
| **Not affected** | Flow, object and field descriptions and help text: still required (`build/flows.md` rule 10, `build/objects-fields.md` rule 3); on declarative metadata they are the only documentation |

Commit messages explain the change; comments explain code that would otherwise be misread. Salesforce code is often read in Setup, the Developer Console or a debug session, where git history is not visible, which is why required why-comments stay in the code.

Legacy code is scored honestly; new and touched code must not get worse (PR-10).
