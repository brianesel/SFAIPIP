# Trigger framework

**Verdict:** every object with Apex trigger logic has exactly one trigger that only hands off to a framework; the framework choice depends on automation density, Flow coexistence and team shape — it is a human decision (ARCH-001).
Sources: see end. Confidence: non-negotiables [high]; option comparison [med] (framework features change between versions — check the repo before adopting).

## Non-negotiables (any framework)
| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | One trigger per object, declaring all events it may need, body = one framework call | multiple triggers on one object run in no guaranteed order | HG-07; inventory count; `pmd:AvoidLogicInTrigger` |
| 2 | Bulk-safe: collections in, one query/DML per context | governor limits apply per transaction, not per record | HG-02; `pmd:OperationWithLimitsInLoop` |
| 3 | Same-record field updates in **before** context; related records in **after** | before-save avoids extra DML and re-running the save order | review; Salesforce record-triggered decision guide |
| 4 | Standard bypass: per handler/action and global, switchable without deploy (Custom Metadata or Custom Permission), used for data loads and integration users | data migrations and incident fixes must not fire business logic | review; bypass test |
| 5 | Recursion control by design: act only on records whose relevant fields changed; track processed Ids per context — never a single static Boolean | static Booleans silently skip the second chunk of 200 in bulk operations | review; bulk 251+ test |
| 6 | No callouts in trigger context; hand off to Queueable / Platform Event | callouts are not allowed after pending DML | `flow:TriggerCallout` for Flows; review for Apex |
| 7 | User-facing errors via `addError` on the record; no swallowed exceptions | users and integrations need record-level outcomes | `pmd:EmptyCatchBlock`; review |
| 8 | Flow and Apex on the same object+event: order is explicit and documented (pattern register) | mixed paradigms without order = double writes, unpredictable results | PR-06; Execution Map; rubric `automation.double_write_fields` |
| 9 | Tests: bulk 251+ (two trigger chunks), bypass on/off, recursion, one per handler branch | proves rules 2, 4, 5 | tests rubric |

## Options (ARCH-001)
| | A. Minimal handler base class (Kevin O'Hara style) | B. Metadata-driven actions (Trigger Actions Framework) | C. Domain layer (Apex Enterprise Patterns / fflib) | D. In-house interface |
|---|---|---|---|---|
| Idea | One virtual `TriggerHandler`; per-object handler overrides `beforeInsert()` etc. | One class (or Flow) per action; Custom Metadata says which actions run, in what order, for which object/context | Domain class per object (`onValidate`, `onApplyDefaults`, trigger events) + unit of work + selectors + services | Small interface + dispatcher written by the team |
| Bypass | API: bypass by handler name, global bypass | Setup: bypass object or single action via metadata; also in code | via configuration in the domain base class | whatever you build |
| Recursion | `setMaxLoopCount` (stops silently when exceeded — log it) | built-in max recursion depth | per domain logic | you build it |
| Flow ordering | outside the framework | **Flow actions ordered together with Apex actions**; entry-criteria formulas | outside the framework | you build it |
| Learning curve | lowest | medium (metadata model) | highest (full layering, unit of work, mocking) | low to start, grows |
| Admin visibility | code only | high (setup shows all actions per object) | code only | depends |
| Testability | plain unit tests | actions are small single-purpose classes | strongest: DI + mocks across layers | depends |
| Fits | 1–3 devs, low/medium automation density | Flow + Apex mixed on busy objects; admins + devs together; medium/high density | multi-team, ISV/packaged apps, existing fflib codebase | only if A–C don't fit (rare) |
| Main risk | handlers grow into god classes | metadata sprawl; another dependency | over-engineering for small teams | maintenance and no community |

**Package policy** (decided 2026-11-20):
| Project facts | What happens |
|---|---|
| A framework already exists and is used consistently | **keep-existing** is proposed (pattern rule PR-06), human confirms |
| A framework exists but is used inconsistently | present: keep-existing + migration items vs switch; human decides |
| **No framework exists yet** | **always ask.** The AI fills ARCH-001 with project facts and the trade-offs of A, B, C — no default, no recommendation as the answer — and a named human chooses |

Signals to show the human (not a verdict): the project's structure level (ARCH-007: Lean → A, Standard → A or B, Enterprise → C); small team + low density favours A's simplicity; Flow + Apex mixed on busy objects favours B's ordering and Setup bypass; multi-team / ISV / existing fflib favours C.

## Automation density (Salesforce guidance, 2026)
Salesforce's record-triggered decision guide now ranks Flow vs Apex by **automation density**: number of automations per object, record volume (UI vs batch/integration scale), and dependency sprawl (cascades into other objects; around five or more related objects counts as high). High density → code-based framework with strict control; low density → declarative-first is fine. Evaluation (01) measures this per busy object; the result feeds ARCH-001.

## Anti-patterns
Logic in the trigger body · several triggers per object · static Boolean recursion guards · DML or SOQL per record · callouts from triggers · after-save update of the same record · a "monster" Flow or handler doing everything · bypass by editing code.

## Enforcement
HG-02, HG-06, HG-07 + analyzer map; project rule template (after ARCH-001 is chosen), e.g. a regex rule that trigger files contain only the framework call — draft in `rules/custom-rules.yaml`, test, approve (PR-14).

## Sources
- Kevin O'Hara, sfdc-trigger-framework — github.com/kevinohara80/sfdc-trigger-framework (fork with docs: github.com/dschach/salesforce-trigger-framework)
- Mitch Spano, Apex Trigger Actions Framework — github.com/mitchspano/apex-trigger-actions-framework
- Apex Enterprise Patterns, fflib-apex-common — github.com/apex-enterprise-patterns/fflib-apex-common; Trailhead "Apex Enterprise Patterns: Domain & Selector Layers"
- Salesforce Architects, Record-Triggered Automation Decision Guide (2026 refresh) and blog "Record-Triggered Automation: Apex or Flow?"
