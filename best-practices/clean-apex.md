# Clean Apex

Baseline: *Clean Apex Code* chapter topics + general clean-code practice. Measured by `../guardrails/rubric/code-design.yaml`.

| Topic | Practice | Measured by |
|---|---|---|
| Naming | intent-revealing names, one word per concept, role suffixes (Service, Selector, TriggerHandler, Test) | `design.naming_*` |
| Do one thing | no boolean flag parameters; ≤ 4 parameters | `design.flag_params`, `design.param_count` |
| Method size | ≤ 30 statements, cognitive complexity < 15, nesting ≤ 3 | `design.method_*`, `design.nesting_depth` |
| Comments | explain why, not what; no commented-out code | `design.comments_why`, `design.commented_out_code` |
| Null / guard clauses | validate at entry, return or throw early | `design.guard_clauses` |
| Trigger boundaries | decide all-or-nothing vs partial success per entry point; `addError` per record | `design.trigger_boundary` |
| Classes | one responsibility; extend via interfaces; no unused abstraction | `design.class_*` |
| Modularity | SOQL in selectors, DML in services/unit of work; low fan-out; no duplication | `design.layering`, `design.coupling`, `design.duplication` |
| Dependency injection | external systems and data access behind interfaces; logic testable in memory | `design.di_seams` |
| Hygiene | no magic literals, dead code, `System.debug`; current API versions; formatter + ESLint | `design.*` |

Legacy code is scored honestly; new and touched code must not get worse (PR-10).
