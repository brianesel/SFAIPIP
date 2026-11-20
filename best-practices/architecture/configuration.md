# Configuration (Custom Metadata, Custom Settings, Labels, Credentials)

**Verdict:** configuration that should travel with deployments goes in **Custom Metadata**; per-user/profile overrides in **hierarchy Custom Settings**; user-facing text in **Custom Labels**; endpoints and secrets in **Named / External Credentials**; user feature access via **Custom Permissions**. No decision card — the table below decides per value.
Confidence: [verified from Salesforce docs/Trailhead, 2026-11] for platform behaviour; [high] for the rules.

## Where does this value go?
| Value | Store | Why |
|---|---|---|
| Mappings, routing rules, thresholds, allowlists, global feature flags, integration settings without secrets | **Custom Metadata Type** | records are metadata: deployable, packageable; readable from Apex, Flow, formulas, validation rules |
| Value that differs per user / profile / org (pilot flags, personal defaults) | **Hierarchy Custom Setting** | resolves the lowest level (user → profile → org); cached reads |
| Simple list data in new work | Custom Metadata, not List Custom Settings [med] | List Custom Settings records don't deploy with the setting |
| Text a user reads (messages, buttons, help) | **Custom Label** | translatable; changeable without code |
| Endpoint URLs, tokens, passwords, certificates | **Named Credential + External Credential** | HG-03; secrets never in code or readable config |
| Who may use a feature | **Custom Permission** (in a Permission Set) | checks access, not a flag in code |
| Business data that users maintain daily | Custom object | it is data, not configuration |

## Platform facts that drive the table
- Custom Metadata records deploy with the type; for custom objects and Custom Settings only the definition deploys, the records stay behind.
- Custom Settings are cached: reading them doesn't cost SOQL queries.
- In Apex tests Custom Settings count as data: create them in `@TestSetup` (never `SeeAllData=true`, HG-04).
- Protected Custom Settings are for managed packages only; outside packages use Named Credentials or encrypted fields for secrets.
- Lightning Data Service does not support Custom Metadata Types → LWC reads them via Apex (see `lwc-data-access.md`).

## Rules
1. No business literals in code or Flows (rubric `design.magic_literals`); name each config value once.
2. One config object per concern, documented in the pattern register (no "Settings__mdt" junk drawer).
3. Every config value has an owner and a default; missing config fails loudly (log + clear error), never silently.
4. Kill switches for integrations and heavy automation live in Custom Metadata (deployable) or a hierarchy setting (when admins must flip it in production without a deploy) — decide per switch and document.
5. Config changes go through the same pipeline as code when stored as metadata.

## Sources
Trailhead "Custom Metadata Types — Get Started"; Apex Developer Guide "Custom Settings"; LWC Developer Guide "Data Guidelines".
