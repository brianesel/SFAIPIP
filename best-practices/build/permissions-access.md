# Permissions and access

**Verdict:** access is designed once per project (access-model ADR), then built from small permission sets per capability, grouped into one permission set group per job function, on a minimal profile. Record access starts from the most restrictive OWD the business accepts and opens up with rules, not with manual shares. Every new object or field ships with the permission set that grants it, and a test proves a normal user (not an admin) can do the job and a user without the set cannot.
Sources: see end. Confidence: non-negotiables [high]; deployment behaviours marked inline; analyzer rule names [verified] against `sf code-analyzer rules --rule-selector all` on 2026-11-20.

## Scope
Building access metadata in a ticket: permission sets (PS), permission set groups (PSG), muting permission sets, custom permissions, profiles (minimal), object and field permissions, OWD, sharing rules, role hierarchy, public groups and queues, integration and agent users, assignment, and access in Apex tests. The high-level rules (least privilege, user mode, OWD posture, profile status) are in `../architecture/security-sharing.md`; this page is the build level below them. Apex sharing keywords and user mode: `apex.md`.

## Non-negotiables
| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | **Access model before the first PS.** Roles × objects × CRUD matrix, OWD per object, sensitive fields, privileged exceptions (`View All Data`, `Modify All Data`, `View All` / `Modify All` per object) recorded in an access-model ADR, signed off by a named human | access built ticket by ticket ends as one PS per person | G2; PR-15; DAT-04; review |
| 2 | **New access goes into permission sets, never into profiles.** Profiles carry only what PS can't: login hours and IP ranges, default record type and app, page layout assignment [med: page layout assignment still lives on profiles unless the org uses Dynamic Forms / Lightning record pages per app; check the project] | profile edits are hard to review and don't compose | review; evaluation (01) |
| 3 | **Every new object, field, tab, Apex class, Flow or custom permission ships with the PS that grants it, in the same ticket.** New custom fields get no access in profiles by default [med: Salesforce Help "Special Behavior in Deployments"] | without it the build "works" only for admins | ticket `metadata` lists the PS (G3); DoD runAs test (G4) |
| 4 | **Never put a universally required field (or a master-detail field) in `fieldPermissions`**; formula and roll-up fields are read-only | the deploy fails: required fields always have full access [high, sf-skills `platform-permission-set-generate`] | deploy validation; review |
| 5 | **A PS deploy replaces the target's version of that PS**, it does not merge [med: Salesforce Help "Special Behavior in Deployments", API 40.0+]. Retrieve and diff the target's PS before deploying; source control is the master | an edit made in the org only is silently removed | review; release checklist (07) |
| 6 | **Privileged permissions need a named reason**: `ModifyAllData`, `ViewAllData`, `ManageUsers`, object `modifyAllRecords` / `viewAllRecords`, `ApiEnabled` for humans. Default: nobody | they bypass sharing and FLS for everything | access-model ADR exception list; Security Health Check (security-sharing rule 10) |
| 7 | **Feature checks use custom permissions**, not profile names, user IDs or role names: `FeatureManagement.checkPermission('<Name>')` in Apex, `$Permission.<Name>` in Flows and formulas. The standard bypass is a custom permission too | names and IDs change; custom permissions are assignable and testable | HG-03; `pmd:AvoidHardcodingId`; `trigger-framework.md` rule 4 |
| 8 | **OWD is set on purpose for every new object**: Private or Read Only for sensitive data, `ControlledByParent` is forced on master-detail children. Never leave the platform default without a decision [med: new custom objects default to Public Read/Write, sf-skills `platform-sharing-owd-configure`] | the default is the most open option | access-model ADR; review of `<sharingModel>` in the object file |
| 9 | **External OWD ≤ internal OWD**; change both together | the platform rejects external wider than internal [high, sf-skills `platform-sharing-owd-configure`] | deploy validation |
| 10 | **Integration and agent users are dedicated users** with their own PS (no admin profile, no shared human login), scoped to the objects and fields the interface needs | an over-privileged integration is the largest blast radius in the org | `security-sharing.md` rule 6; ARCH-002 inventory `Auth` column; review |
| 11 | **Assignments are data, not metadata.** They don't travel with a deploy. The AI assigns only test users in a write-allowed sandbox (HG-11); production assignment is a human step in the release (HG-09) | an unassigned PS looks deployed but changes nothing; a removed assignment can't be restored by a retrieve | `org_guard.py`; release checklist (07) |
| 12 | **Tests prove access** with `System.runAs` as a minimum-access user, with and without the PS (group) | admin-run tests hide missing FLS, especially with v67.0 user mode | `pmd:ApexUnitTestClassShouldHaveRunAs`; `testing.md`; G4 |

## Building blocks and naming
Use the project's convention if one exists; otherwise these defaults. API names in `PascalCase_With_Underscores`, labels in the users' language, a description on every item (who it is for, what it grants, ticket key).

| Item | Convention | Example | Notes |
|---|---|---|---|
| Permission set (capability) | `<Area>_<Capability>` | `Sales_Opportunity_Edit`, `Service_Case_Close`, `Invoice_Read` | one capability, reusable across job functions; object + field + class + tab access for that capability |
| Permission set group (job function) | `<JobFunction>` or `PSG_<JobFunction>` | `Sales_Representative`, `Service_Agent` | what users are assigned; one per job function from the access matrix |
| Muting permission set | `Mute_<PSG>_<What>` | `Mute_Service_Agent_Delete` | exists only inside one PSG; removes a permission the group's sets would grant |
| Custom permission | `<Feature>_<Action>` | `Bypass_Automation`, `Discount_Approve` | assigned through a PS; checked in code and Flows |
| Integration / agent PS | `Integration_<System>` / `Agent_<AgentName>` | `Integration_ERP` | on a dedicated user; no human gets it |
| Public group | `<Team or Purpose>` | `Finance_Controllers` | for sharing rules and list views, not for permissions |
| Queue | `<Team>_Queue` | `Support_Tier1_Queue` | look up by `DeveloperName` with `Type = 'Queue'`, never by Id |

Rules of thumb [high, unless marked]:
- **PSG status:** after a component change, a PSG recalculates; while its status is `Outdated` the group is not yet in effect [med: observed in delivery projects]. Check `PermissionSetGroup.Status` before testing.
- **Muting** is for exceptions inside one group. If two job functions need different muting, it is usually two capability sets, not more muting.
- **Licences first:** a PS can't grant what the user's licence lacks; some features need a permission set licence. Check licence availability before planning assignment [med: field observation: a licence pool ran down to one free seat mid-change].
- **Assignment expiry** for temporary access (support, cut-over) instead of "remember to remove" [med: check the feature is enabled in the org].
- **Profiles:** one minimal baseline profile per licence type (based on a minimum-access profile) is the target; cloning System Administrator for anyone else is not allowed.

## Record access (sharing)
| Mechanism | Use for | Build notes |
|---|---|---|
| OWD (`<sharingModel>` / `<externalSharingModel>` in the object file) | the baseline | most restrictive the business accepts; a change to more restrictive triggers a sharing recalculation, plan it for large objects |
| Role hierarchy | managers see their team's records | mirror reporting lines for data access, not the org chart's every box; turn off "Grant Access Using Hierarchies" on custom objects where managers must not see; owners of very many records get no role (`../architecture/data-model-ldv.md`, ownership skew) |
| Owner-based sharing rule | records owned by group / role A visible to group / role B | only `accessLevel` can be edited later; other changes mean delete and recreate [high, sf-skills `platform-sharing-rules-generate`] |
| Criteria-based sharing rule | records matching field values | prefer over owner rules when the business rule is about the data, not the owner |
| Teams (account, opportunity, case) | per-record collaboration | standard feature first, before custom sharing |
| Apex managed sharing | rules config can't express | custom objects with an Apex sharing reason; survives owner change; recalculation class required |
| Manual sharing | one-off by users | never part of a design: manual shares are removed when the owner changes [high]; a Winter '27 setting "Keep Manual Shares When Transferring Records" (off by default) changes this [med: release notes 264; check the org's setting] |

Gotchas:
- A queue can't be a sharing rule's shared-to target; share with a public group or role instead [high, sf-skills `platform-sharing-rules-generate`].
- Master-detail children have no own OWD, sharing rules or queues; access follows the parent [high, Salesforce Help "Object Relationships Overview"].
- A new custom object, its OWD change and a new owner-based sharing rule need separate deploys in that order [med: Salesforce Help "Special Behavior in Deployments"; not reproduced here]. Run `sf project deploy validate` (dry run) first.
- Public group members don't travel with a deploy [med: same source]; group and queue membership is data, set per org.

## Access in tests
- Create the test user on a minimum-access profile; assign the PSG (or PS) with a `PermissionSetAssignment` insert; run the act inside `System.runAs(user)`.
- Setup and non-setup DML in one transaction fail with `MIXED_DML_OPERATION`: insert the user and assignments inside `System.runAs(new User(Id = UserInfo.getUserId()))` [high, Apex Developer Guide].
- `runAs` applies record sharing; CRUD/FLS apply only where the code runs in user mode [high, Apex Developer Guide "Using the runAs Method"]. So a user-mode selector is the thing a permission test proves.
- Cases per access change: allowed (with PS), blocked or empty (without PS), sharing (a record owned by someone else). Assert the outcome, not "no exception".
- For Flows, run the Flow test or the Apex test that starts it as the same user.

## AI-assisted building
- Use Salesforce's `platform-permission-set-generate`, `platform-sharing-owd-configure`, `platform-sharing-rules-generate` and `platform-role-hierarchy-apply` skills for metadata shape. Our rules add: the access-model ADR comes first (rule 1), capability-sized sets grouped per job function, and no permission beyond the ticket.
- Grant only objects and fields the ticket names and that exist (AI-02); the official skill says the same and fails deploys on invented fields.
- `dx-org-permission-set-assign` assigns via `sf org assign permset`: allowed only for test users in a write-allowed sandbox (HG-11), and only when the ticket needs it. Never in production (HG-09); `org_guard.py` blocks MCP and CLI assignment there.
- Answering "can user X do Y": read the automation's run mode first (system-mode Flows and Apex ignore the user's permissions), then name *what* grants or blocks (PS, PSG, licence, sharing), and say whether the answer is static analysis or a real `runAs` run. Never report a static check as tested (AI-05).
- Changing a privileged permission, OWD, or a role hierarchy is an architecture-level change: propose it, a named human decides (PR-15, AI-01).

## Anti-patterns
One permission set per person · access added to profiles · cloned System Administrator profiles · `View All Data` "for now" · integration on a named human's login · sharing rule to fix a missing object permission (or the other way round) · manual sharing as a design · checks on profile or role names in code · OWD left at the default · a PS edited in production and overwritten by the next deploy · tests run only as admin · assigning access in production from a script.

## Enforcement
- Code Analyzer: `pmd:ApexUnitTestClassShouldHaveRunAs` (recommended for project config, proposal per PR-14), `pmd:AvoidHardcodingId` (HG-03), `pmd:ApexCRUDViolation` (HG-01). Permission set, profile and sharing XML have no analyzer rules in the verified inventory → review, plus a possible regex project rule (e.g. flag `<name>ModifyAllData</name>` with `<enabled>true</enabled>` in `*.permissionset-meta.xml`), drafted and fixture-tested per PR-14.
- `ticket_lint.py` (G3): ticket `metadata` lists the permission set for new objects and fields.
- `dev_cycle.py dod` (G4): access test cases present and passing.
- Evaluation (01): count of profile-granted permissions, users with `Modify All Data`, PS without assignments, OWD per sensitive object.

## Sources
- Salesforce Help: Permission Set Groups; Muting Permission Sets; Custom Permissions; Sharing Settings; Object Relationships Overview; Special Behavior in Deployments — help.salesforce.com
- Apex Developer Guide: Using the runAs Method; sObjects That Cannot Be Used Together in DML Operations
- forcedotcom/sf-skills `platform-permission-set-generate`, `dx-org-permission-set-assign`, `platform-sharing-owd-configure`, `platform-sharing-rules-generate`, `platform-role-hierarchy-apply` (cloned 2026-11-20, commit 431c50f)
- `../architecture/security-sharing.md` (profile vs permission set status 2026, v67.0 user mode)
