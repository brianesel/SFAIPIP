# Security and sharing

**Verdict:** least privilege everywhere: permission-set-led access by job function, private-by-default sharing for sensitive objects, Apex explicitly in user mode, integration users with narrowly scoped permission sets. **API v67.0 changes Apex defaults — plan the version bump.**
Confidence: v67.0 changes and profile/permission-set status [verified from Salesforce sources, 2026]; design rules [high].

## Platform change to plan for (API v67.0, Summer '26)
- Database operations (SOQL, SOSL, DML, `Database` methods) run in **user mode by default** from v67.0.
- **`WITH SECURITY_ENFORCED` is removed** — classes on v67.0 that use it don't compile; use `WITH USER_MODE` (or explicit `WITH SYSTEM_MODE` where system access is intended).
- Classes **without a sharing declaration default to `with sharing`**.
- Bumping a class to v67.0 can surface access errors that were silent before → treat the bump as a change with regression tests, not a cosmetic upgrade (it interacts with rubric check `design.api_version`).

## Rules
| # | Rule | Checked by |
|---|---|---|
| 1 | New Apex states access explicitly: `WITH USER_MODE` / `AccessLevel.USER_MODE`; `WITH SYSTEM_MODE` only with a comment saying why | HG-01, `pmd:ApexCRUDViolation`, project rule `NoSecurityEnforced` |
| 2 | Every class declares sharing; services use `inherited sharing`; `without sharing` only with an ADR | HG-06, `pmd:ApexSharingViolations` |
| 3 | Dynamic SOQL uses bind variables; no string concatenation of user input | `pmd:ApexSOQLInjection` |
| 4 | Permission-set-led model: minimal baseline profile (login hours, IP, defaults); access via Permission Sets grouped into Permission Set Groups per **job function** | review; evaluation (01) |
| 5 | OWD Private (or Read Only) for sensitive objects; open access only with a documented reason; prefer criteria/owner sharing rules over manual sharing; Apex managed sharing only for rules config can't express | access-model ADR |
| 6 | Integration users: dedicated user, client credentials flow for server-to-server, narrowly scoped permission set; named-user OAuth (web server flow) when user context matters | ARCH-002 inventory row `Auth` |
| 7 | Guest / community users: no default access; review guest sharing every release | review |
| 8 | Sensitive data: classify fields; encryption / masking decisions recorded (Shield, data masking in sandboxes) | DAT-04 |
| 9 | LWC: no `innerHTML` with user data; Apex controllers `with sharing` + user mode | ESLint LWC rules, `pmd:ApexXSSFromEscapeFalse` |
| 10 | Security Health Check reviewed every release; score trend in the weekly report | 01-eval, rituals |

## Profiles vs permission sets (status 2026)
Salesforce cancelled the planned end-of-life for permissions on profiles, but still recommends a permission-set-led model and invests there. This package keeps the recommendation: new access goes into Permission Sets / Groups; profile clean-up is a migration item (decision: when touched).

## Sources
Salesforce Summer '26 architect highlights and API v67.0 security blog; SOQL `WITH` clause docs (USER_MODE recommended over SECURITY_ENFORCED); Salesforce Ben reporting on the profile-permission retirement cancellation (2026); Salesforce Security Implementation Guide.
