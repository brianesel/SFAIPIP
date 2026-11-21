# Build guides

How to build each kind of Salesforce metadata well. `../architecture/` answers *which design*; these guides answer *how to build it once the design is chosen*. Guardrails (`../../guardrails/`) are the enforced subset.

Every guide has the same shape: **verdict** · **scope** · **non-negotiables** (rule, why, how it is checked) · **naming** · practices · **AI-assisted building** (which Salesforce official skill to use and what this pipeline adds) · **anti-patterns** · **enforcement** · **sources**. Claims carry confidence tags (PR-02); analyzer rule names are verified against Code Analyzer v5 (AI-02).

| Guide | Covers | Official skills used | Related architecture guide |
|---|---|---|---|
| `flows.md` | record-triggered, scheduled, autolaunched, screen, platform-event Flows; Flows as agent actions | `automation-flow-generate` | `trigger-framework.md`, `error-handling-logging.md` |
| `apex.md` | classes, triggers, bulk, limits, layers, tests | `platform-apex-generate`, `platform-apex-test-generate` | `trigger-framework.md`, `async-processing.md` |
| `permissions-access.md` | permission sets / groups, FLS, OWD, sharing rules, roles, queues, integration users | `platform-permission-set-generate`, `platform-sharing-*`, `platform-role-hierarchy-apply` | `security-sharing.md` |
| `objects-fields.md` | custom objects, fields, picklists, value sets, record types, relationships | `platform-custom-object-generate`, `platform-custom-field-generate`, `platform-value-set-generate` | `data-model-ldv.md` |
| `validation-rules-formulas.md` | validation rules, formula fields, roll-ups | `platform-validation-rule-generate` | `configuration.md` |
| `lightning-pages-ui.md` | record pages, layouts, apps, tabs, list views, actions, labels | `platform-flexipage-generate`, `platform-custom-application-generate`, `design-systems-slds-*` | `lwc-data-access.md` |
| `lwc.md` | Lightning Web Components | `experience-lwc-*`, `experience-lds-*` | `lwc-data-access.md` |
| `reports-dashboards.md` | report types, reports, dashboards, folders | `platform-report-generate`, `platform-custom-report-type-generate` | `data-model-ldv.md` |
| `integration-metadata.md` | Named / External Credentials, connected apps, Platform Events, CDC, External Services | `integration-connectivity-*`, `integration-eventing-*` | `api-and-integration.md` |
| `agentforce.md` | agents, topics, actions, prompt templates, testing, tracing | `agentforce-*`, `platform-tracing-agentforce-configure` | `../well-architected.md` (Agentic Enterprise lens) |

Not covered yet: OmniStudio, Experience Cloud sites, industry clouds, CRM Analytics, approval processes and assignment rules. Use the official skills and the general guardrails for those until a guide exists.
