# Lightning Web Components

**Verdict:** build an LWC only when standard components, Dynamic Forms or a screen Flow can't do the job. When you build one: small components with one job, base components and SLDS before custom markup, a clear public API that the component never changes itself, events up and properties down, one error helper, no unsafe DOM or code evaluation, accessible markup, and Jest tests that assert what the user sees. Where the data comes from is decided by `../architecture/lwc-data-access.md`; this guide does not repeat it.
Sources: see end. Confidence: non-negotiables [high]; numbers marked inline; analyzer rule names [verified] against the Code Analyzer v5 inventory (719 rules) on 2026-11-20.

## Scope
Lightning Web Components for Lightning Experience record, app and home pages, quick actions, utility bars and screen Flows. Data access order and caching: `../architecture/lwc-data-access.md`. Page placement and SLDS basics: `lightning-pages-ui.md`. Apex controllers: `apex.md`. Out of scope: Aura (legacy: migrate when touched), Visualforce, React or other frameworks hosted on the platform, Experience Cloud LWR specifics.

## Before you build: is an LWC the right tool?
Check in this order and record the answer on the ticket [high]:
1. Can standard UI do it (Dynamic Forms, Dynamic Actions, Dynamic Related Lists, compact layout)? → `lightning-pages-ui.md`.
2. Is it a guided step-by-step task with simple screens? → screen Flow (`flows.md`), with an LWC only for the one screen component Flow lacks.
3. Is there an existing component in the project or an AppExchange package already in the pattern register? → reuse it (PR-06).
4. Otherwise build an LWC, and put the rules that must hold for every channel on the server, not in the component.

## Non-negotiables
| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | **Data access follows `../architecture/lwc-data-access.md`** (base record components → LDS / GraphQL → Apex), with `@salesforce/schema` imports instead of field names in strings | one cache, FLS handled, renamed fields caught at deploy | review; `eslint:@lwc/lwc/valid-wire`, `eslint:@lwc/lwc/no-unknown-wire-adapters` |
| 2 | **Base components first.** Use `lightning-*` components before hand-built HTML; style with SLDS styling hooks, never by overriding SLDS classes | base components bring accessibility, theming and mobile behaviour for free | `eslint:@salesforce-ux/slds/no-slds-class-overrides`, `eslint:@salesforce-ux/slds/no-hardcoded-values-slds2`; review |
| 3 | **Public API is small and owned by the parent.** `@api` properties in camelCase, documented in a JSDoc comment; the component never reassigns its own `@api` property (copy into a private field, or use a getter / setter) | reassigning breaks one-way data flow and causes update loops | `eslint:@lwc/lwc/no-api-reassignments`, `eslint:@lwc/lwc/no-leading-uppercase-api-name`, `eslint:@lwc/lwc/valid-api` |
| 4 | **Events go up as `CustomEvent`** with a lowercase name without an `on` prefix and a copy of the data in `detail`; `bubbles` and `composed` stay `false` unless a documented reason exists. Unrelated components talk through Lightning Message Service, not a pub-sub module | an event that crosses every shadow boundary leaks data and collides with other names; passing an object by reference lets listeners change the sender's state | `eslint:@lwc/lwc/prefer-custom-event`, `pmd:AvoidLwcBubblesComposedTrue`; review |
| 5 | **No unsafe DOM or code evaluation.** No `innerHTML` / `lwc:dom="manual"` with user data, no `eval`, `new Function` or string timers, no `<script>` from an external CDN (use a Static Resource and `loadScript`), no Aura globals (`$A`) | Lightning Web Security isolates namespaces; it does not sanitise your own component's HTML, so XSS stays your problem [verified, Salesforce Developers blog "Security Anti-Patterns in Lightning Web Components", 2026-06: LWS sanitises only shared elements, not the component's own shadow DOM] | `eslint:@lwc/lwc/no-inner-html` (severity 2: blocks), `eslint:no-eval`, `eslint:no-implied-eval`, `eslint:no-new-func`, `eslint:@lwc/lwc-platform/no-aura`; `experience-lwc-security-validate` |
| 6 | **Third-party libraries** are loaded as Static Resources from a pinned version and scanned for known vulnerabilities | a vulnerable library ships into every page that uses the component | `retire-js:LibraryWithKnownCriticalSeverityVulnerability`, `retire-js:LibraryWithKnownHighSeverityVulnerability` |
| 7 | **One error helper.** Every wire and imperative call handles the error branch; one shared helper turns LDS, Apex and JavaScript errors into a user message (toast or inline) and sends details to the project logger. No raw error text or stack to users; no `console.log` left in shipped code | users see what to do; support sees what happened (`../architecture/error-handling-logging.md` rule 11) | `pmd:AvoidConsoleStatements`; review |
| 8 | **Accessible markup** to WCAG 2.2 AA [med: confirm the project's target level in the design sign-off]: every input has a label, images have `alt` text, interactive elements are buttons or links (not clickable `div`s), focus is visible and moves to dialogs and back, meaning is not carried by colour alone | keyboard and screen-reader users can't use what they can't reach; accessibility defects are expensive after go-live | `pmd:UseAltAttributeForImages`; Sa11y Jest tests (`@sa11y/jest`); `experience-accessibility-validate` |
| 9 | **No hard-coded IDs, URLs or text.** Record type and queue IDs come from Apex or Custom Metadata; navigation uses `lightning/navigation`; user-facing text comes from Custom Labels (`@salesforce/label`) | IDs and URLs differ per org; hard-coded text can't be translated | HG-03; review; `lightning-pages-ui.md` |
| 10 | **Clean lifecycle.** Listeners added to `window` or `document` are removed in `disconnectedCallback`; no reactive wire config set in `renderedCallback`; no `document`-level DOM queries; timers only with a reason | leaked listeners keep dead components in memory; config set during render loops forever | `eslint:@lwc/lwc/no-document-query`, `eslint:@lwc/lwc/no-async-operation`; review |
| 11 | **Jest tests per component** (`__tests__/<component>.test.js`): each test asserts a concrete DOM or event outcome; wire adapters and Apex are mocked; data and error paths are tested; the DOM is cleaned after each test | Jest tests run locally and never connect to an org [verified, LWC Developer Guide "Test Lightning Web Components"], so a deploy never runs them and untested UI logic ships silently | `testing.md`; G4; HG-05 (by analogy); coverage threshold in `jest.config.js` |
| 12 | **ESLint is a gate:** 0 severity 1–2 findings from the Code Analyzer eslint engine on `lwc/` | same quality bar as Apex | HG-10; rubric `design.lwc_eslint` |

## Structure and naming
| Item | Convention | Example |
|---|---|---|
| Folder and file names | camelCase, start with a lowercase letter; the markup tag is the kebab-case form [high, LWC Developer Guide "Component Folder"] | `accountHealthCard` → `<c-account-health-card>` |
| Component name | noun for what it shows or does; container vs presentational split visible in the name if the project uses it | `caseTimeline`, `caseTimelineItem` |
| `@api` properties | camelCase, no leading uppercase, no `on` prefix, documented | `recordId`, `maxRows` |
| Events | lowercase, no hyphens, no `on` prefix, past tense or noun for what happened [high, LWC Developer Guide "Create and Dispatch Events"] | `rowselected`, `filterchange` |
| Shared helpers | a service component without markup, exported functions | `errorUtils`, `dateUtils` |
| Tests | `__tests__/<component>.test.js`; accessibility tests in `<component>.accessibility.test.js` if the project splits them [med, sf-skills `experience-lwc-accessibility-jest-run`] | `__tests__/caseTimeline.test.js` |
| Meta file | `isExposed` only for components placed in App Builder, Flow or actions; declare each target and its `targetConfigs` | — |

Rules of thumb [high]:
- **One job per component.** If the JavaScript file needs scrolling to understand, split it into a container (data, events) and presentational children (props in, events out).
- **Business logic stays on the server.** The component formats and guides; rules that must hold for every channel belong in validation rules, Flows or Apex (`validation-rules-formulas.md`).
- **Getters for derived values** instead of computing in the template; keep the template free of logic beyond `lwc:if` and `for:each`.
- **Wire data is read-only and can arrive more than once.** Copy before changing it; make wire handlers idempotent [verified, Salesforce Developers blog "Data and Communication Anti-Patterns in Lightning Web Components", 2026-08].
- **Duplicate code across components** goes into a shared module; the analyzer flags copies (`cpd:DetectCopyPasteForJavascript`, `cpd:DetectCopyPasteForHtml`).

## Security notes
- Lightning Web Security (LWS) is the current security architecture for LWC; Lightning Locker is legacy [med: check the org's Session Settings for which one is active and the release that made LWS the default]. LWS isolates namespaces: storage and cookies are scoped to your namespace, a small set of APIs throws, and most others are sandboxed, not blocked [verified, blog "Security Anti-Patterns in Lightning Web Components"; distortions change between releases, the LWS Distortion Viewer is the current truth].
- A component that passes Jest but fails in the org is often hitting LWS or a runtime difference that jsdom doesn't have; check the LWS Distortion Viewer before a second debug round (AI-04) [med, LWC Developer Guide "Write Jest Tests for Lightning Web Components" (Jest uses jsdom, no browser); same security blog].
- Apex called from LWC is `with sharing` and runs queries in user mode (HG-01, HG-06; `apex.md`). The component can be bypassed: never rely on it for access checks.
- Lightning Message Channels stay `isExposed=false` unless a managed package needs otherwise (`pmd:AvoidLmcIsExposedTrue`).

## Testing
- Tool: `@salesforce/sfdx-lwc-jest`; scripts `test:unit` and `test:unit:coverage` in `package.json` [verified, LWC Developer Guide "Install `sfdx-lwc-jest`"].
- Mock patterns: emit test data and errors through the wire adapter mocks; `jest.mock` the `@salesforce/apex/...` import with resolved and rejected values; use the `lightning-stubs` from `sfdx-lwc-jest` for `lightning/*` modules [verified, LWC Developer Guide "Write Jest Tests for Lightning Web Components That Use the Wire Service", "Jest Test Patterns and Mock Dependencies"].
- LWC renders asynchronously: await a resolved promise before each assertion; remove all children of `document.body` and clear mocks in `afterEach` [verified, LWC Developer Guide "Write Jest Tests for Lightning Web Components"].
- Coverage threshold is a project decision set in `jest.config.js` (`coverageThreshold`) so the test run fails below it [verified, Jest docs "Configuring Jest"]; Salesforce sets no LWC number.
- Jest does not see LWS, the real render pipeline or the LDS cache (it runs without a browser or org [verified, LWC Developer Guide "Test Lightning Web Components"]): test the component in the sandbox in every context it is placed in (record page, Flow, mobile) before handing over.

## AI-assisted building
- Use Salesforce's `experience-lwc-generate` skill to scaffold, `experience-lwc-base-components-integrate` to pick base components, `experience-lds-best-practices-apply` for data access, then `experience-lwc-security-validate` and `experience-accessibility-validate` on the result. Our rules add: tests from the agreed test set exist before the component code (PR-08), naming and error helper per this guide.
- SLDS hooks and base component properties must exist: verify them with the skill's index or the component reference, never guess from a naming pattern (AI-02).
- Field and object names come from `@salesforce/schema` imports of fields that exist in the project or org (AI-02).
- The AI deploys components only to a write-allowed sandbox (HG-11), never to production (HG-09).

## Anti-patterns
LWC for a screen Dynamic Forms could build · Apex for single-record reads · reassigning `@api` properties · `bubbles: true, composed: true` by default · objects passed by reference in events · pub-sub modules · `innerHTML` with user data · CDN scripts · business rules only in the component · raw error text to users · clickable `div`s · hard-coded colours and text · `console.log` in shipped code · tests that only check "it rendered".

## Enforcement
- Code Analyzer eslint engine in CI and `dev_cycle.py dod`; rubric `design.lwc_eslint` (0 severity 1–2 findings). `eslint:@lwc/lwc/no-inner-html` is severity 2 by default and blocks under HG-10.
- Not mapped yet, proposal for project config (needs approval per PR-14): raise to severity 2 and tag `Project`: `eslint:@lwc/lwc/no-api-reassignments`, `eslint:no-eval`, `eslint:no-new-func`, `pmd:AvoidLwcBubblesComposedTrue`, `pmd:UseAltAttributeForImages`.
- Jest and Sa11y results are evidence for the ticket (AI-05); coverage threshold in `jest.config.js`.

## Sources
- LWC Developer Guide — Component Folder; Create and Dispatch Events; Data Guidelines; Lightning Web Security (developer.salesforce.com/docs/platform/lwc/guide)
- LWC Developer Guide — Test Lightning Web Components; Install `sfdx-lwc-jest`; Write Jest Tests for Lightning Web Components; Write Jest Tests for Lightning Web Components That Use the Wire Service; Jest Test Patterns and Mock Dependencies (developer.salesforce.com/docs/platform/lwc/guide/testing.html and the pages under it)
- Salesforce Developers blog, "Security Anti-Patterns in Lightning Web Components" (2026-06) — https://developer.salesforce.com/blogs/2026/06/security-anti-patterns-in-lightning-web-components
- Salesforce Developers blog, "Data and Communication Anti-Patterns in Lightning Web Components" (2026-08) — https://developer.salesforce.com/blogs/2026/08/data-and-communication-anti-patterns-in-lightning-web-components
- Salesforce Developers blog, "Runtime Behavior Anti-Patterns in Lightning Web Components" (2026-11) — https://developer.salesforce.com/blogs/2026/11/runtime-behavior-anti-patterns-in-lightning-web-components
- Jest docs, "Configuring Jest" (`coverageThreshold`) — https://jestjs.io/docs/configuration
- forcedotcom/sf-skills `experience-lwc-generate`, `experience-lwc-security-validate`, `experience-lwc-accessibility-jest-run`, `experience-accessibility-validate`, `experience-lwc-base-components-integrate`, `experience-lds-best-practices-apply`, `design-systems-slds-apply` (cloned 2026-11-20, commit 431c50f)
- Salesforce Code Analyzer v5 rule inventory (719 rules, 2026-11-20)
