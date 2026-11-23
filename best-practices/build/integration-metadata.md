# Integration metadata

**Verdict:** the integration pattern is an architecture decision (`../architecture/api-and-integration.md`, ARCH-002, ARCH-003); this guide is about building the metadata behind it. Every endpoint goes through a Named Credential backed by an External Credential, access to the credential is granted only by permission set, every external system gets its own least-privilege integration user, new OAuth apps are External Client Apps, and no secret, token, URL or record ID ever sits in source. Secrets are entered per org after deploy, as a recorded runbook step.
Sources: see end. Confidence: non-negotiables [high]; numbers marked inline; analyzer rule names [verified] against `sf code-analyzer rules --rule-selector all` on 2026-11-20.

## Scope
Named Credentials, External Credentials and their principals, permission-set mapping, Connected Apps and External Client Apps, Remote Site Settings (legacy), Platform Events, Change Data Capture enablement, managed event subscriptions, External Services, and integration users. Out of scope: pattern choice, retries, idempotency design and API style (`../architecture/api-and-integration.md`), callout code structure (`apex.md`), logging framework (`../architecture/error-handling-logging.md`, ARCH-004), Salesforce Connect adapters.

## Non-negotiables
| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | **Every outbound call uses a Named Credential** (`callout:<Name>/path`) backed by an External Credential. No endpoints, tokens, API keys or passwords in Apex, Flow, Custom Metadata, Custom Settings or static resources | secrets in source leak through every clone and backup; endpoints in code break per environment | HG-03; `pmd:ApexSuggestUsingNamedCred`, `pmd:ApexInsecureEndpoint`, `pmd:AvoidHardcodedCredentialsInHttpHeader`, `pmd:AvoidHardcodedCredentialsInVarAssign`, `pmd:AvoidHardcodedCredentialsInVarDecls`, `pmd:AvoidHardcodedCredentialsInFieldDecls` |
| 2 | **Secrets never enter the repo or the chat.** Metadata carries structure only; client secrets, certificates and principal credentials are entered in each org after deploy and the step is in the release runbook | an auth provider's consumer secret arrives as a placeholder after a change set, and a connected app's consumer key can't be set through the Metadata API, so the other system needs the new key [verified, Salesforce Help "Special Behavior in Deployments", release 264] | HG-03; release checklist (07); PR-13 |
| 3 | **Access to a credential is granted by permission set only:** External Credential principal access in a permission set assigned to the integration or running user, never to "all users" | the permission set is the audit trail of who can call the system | review; `permissions-access.md` |
| 4 | **Named principal vs per-user principal is decided per interface** and recorded in the ARCH-002 inventory: named for system-to-system, per-user when the remote system must see the real user | a shared named principal hides who did what on the remote side | PR-15 when unclear; review |
| 5 | **One integration user per external system** (or per use case), not an admin and not a person. Salesforce Integration user licence with the "Minimum Access - API Only Integrations" profile; access only through permission sets [high, Salesforce Help "Give Integration Users API Only Access"] | a dedicated user limits data reach and makes every change traceable to one system | HG-01 (least privilege, by analogy); `../architecture/security-sharing.md` rule 6 |
| 6 | **The integration user's sharing is designed, not discovered.** Check OWD and sharing for every object it reads or writes; grant record access with criteria-based sharing to a group, never "View All Data" / "Modify All Data" | under a Private OWD a user sees only records it owns or is granted through the role hierarchy or sharing rules [high, Salesforce Help "Organization-Wide Sharing Defaults"] | review; integration test as the integration user |
| 7 | **New OAuth apps are External Client Apps.** A Connected App only when a client requires it, with the reason on the ticket. Minimum scopes (never `full` by default), explicit https callback URLs, PKCE for public clients, JWT bearer or client credentials for server-to-server | new Connected App creation is disabled by default in orgs from Spring '26 [med, sf-skills `integration-connectivity-connected-app-configure`]; broad scopes and loose callbacks are token-theft paths | `pmd:LimitConnectedAppScope`, `pmd:UseHttpsCallbackUrlConnectedApp`; review |
| 8 | **Remote Site Settings are legacy.** Use one only where a Named Credential can't be used, https only, protocol security on | callouts through a Named Credential don't need a Remote Site Setting [high]; plain http and disabled protocol security expose traffic | `pmd:AvoidInsecureHttpRemoteSiteSetting`, `pmd:AvoidDisableProtocolSecurityRemoteSiteSetting` |
| 9 | **Inbound matching uses an External ID marked Unique**, never `Name` | without Unique, REST upsert needs "View All Data" for the caller and allows duplicates [high, REST API Developer Guide "Upsert Records Using sObject Rows by External ID"] | review; `../architecture/data-model-ldv.md` rule 4 |
| 10 | **Platform Events: publish behaviour is chosen on purpose.** Publish-after-commit for events that describe saved data; publish-immediately only when the event must go out even on rollback (for example error logging) | an event about data that was rolled back sends a false fact to every subscriber [high, sf-skills `integration-connectivity-generate` platform-events guide] | review |
| 11 | **Subscribers are idempotent and logged.** Platform Event and CDC triggers handle redelivery, store a resume checkpoint, and log failures to the ARCH-004 pattern | events can be delivered again; a subscriber that fails silently loses data | `../architecture/api-and-integration.md` §4; tests |
| 12 | **Tests cover every response class without the other system:** `HttpCalloutMock` for success and for each error class the code handles differently (for example 4xx, 401, 429, 5xx, timeout); one test per expected handling | in a test the callout isn't made; the Apex runtime returns the mock's response [high, Apex Developer Guide "Testing HTTP Callouts by Implementing the HttpCalloutMock Interface"] | HG-05; `testing.md`; tests rubric |

## Structure and naming
| Item | Convention | Example |
|---|---|---|
| Named Credential | `<System>_<Purpose>`; the same API name in every org, URL per environment | `ERP_Orders` |
| External Credential | `<System>_<AuthType>` | `ERP_ClientCredentials`, `ERP_JwtBearer` |
| Principal | `<System>Integration` (named) or `<System>PerUser` | `ERPIntegration` |
| Permission set (credential access) | `Int_<System>_Access`; one per system | `Int_ERP_Access` |
| Integration user | one per system; username pattern agreed per project | `int.erp@<domain>` |
| External Client App | `<System>_<Flow>` | `ERP_ClientCredentials` |
| Platform Event | business fact in past tense, `__e` | `Order_Placed__e` |
| Custom event channel | label in CamelCase + `__chn` [high, sf-skills `integration-eventing-cdc-configure`] | `PartnerSync__chn` |
| CDC channel member file | `<Entity>_ChangeEvent` with a single underscore; `selectedEntity` keeps the ChangeEvent name (`Order__ChangeEvent` for `Order__c`) [high, same skill] | `Order_ChangeEvent` |
| External ID field | `<System>_Id__c`, External ID + Unique (rule 9) | `ERP_Id__c` |

These names are a proposal; the project's pattern register decides (PR-06).

## Type-specific practices
| Type | Do | Avoid |
|---|---|---|
| Named / External Credential | External Credential model for all new work; migrate legacy Named Credentials (auth on the credential itself) when touched [high, sf-skills named-credentials guide]; set the per-environment URL through a deploy-time replacement or a recorded post-deploy step [med] | one credential per environment with the environment in the name and code choosing between them, unless the pattern register says so; also granting principal access only: a user making an authenticated callout also needs access to the User External Credential object, which some custom permission sets and profiles lack [high, Salesforce Help "Enable User External Credentials"] |
| External Client App | retrieve the OAuth security settings from the org before editing (they can't be authored from scratch) [high, sf-skills]; keep each ECA's files together in source | inventing ECA file suffixes: they are abbreviated (`.ecaGlblOauth`, `.ecaPlcy`) [high, same skill] |
| Platform Event | small payloads (IDs and changed values, not whole records); schema is a contract: additive changes only; check the current retention and allocation limits in the Platform Events Developer Guide before design [med] | one generic "anything happened" event |
| Change Data Capture | enable through `PlatformEventChannelMember` (there is no `ChangeDataCapture` metadata type); enrichment fields are single-hop field names; filter expressions without `WHERE` [high, sf-skills `integration-eventing-cdc-configure`] | CDC for an external subscriber when the integration user may not get object-wide read access: CDC ignores sharing, so a Pub/Sub API or CometD subscriber needs View All Records on the object (View All Data for all entities on a channel) [high, Change Data Capture Developer Guide "Required Permissions for Change Event Subscribers"]; prefer a Platform Event there |
| Managed event subscription | `ManagedEventSubscription` for Pub/Sub API subscribers that need managed replay; start from `LATEST` [high, sf-skills `integration-eventing-subscription-configure`] | `EARLIEST` on a busy channel without agreement: it replays the whole retained backlog [high, same skill] |
| External Service | register from a versioned OpenAPI spec in the repo, through a Named Credential; regenerate on contract change and re-run action tests | hand-edited generated classes; expecting an External Service from an Apex REST source (API Catalog) to deploy its Apex class or show in External Services setup: it does neither [high, Agentforce Developer Guide "Verify Metadata and OpenAPI Specification Documents"] |

## Integration user setup, in order
1. Plan access before build: list the objects and fields the flow reads and writes, per system; no "View All Data", no delete unless a requirement says so, following least privilege [high, Salesforce Help "Give Integration Users API Only Access"].
2. Create the user (Salesforce Integration licence, API-only profile) per org; users are data, not metadata, so this is a runbook step in each environment [high].
3. Grant object and field access, credential access and event access through one permission set (or group) per system; an external event subscriber needs Read on the event object; Create is for publishing [high, Platform Events Developer Guide "Enterprise Messaging Platform Events"].
4. Design record access for the user (rule 6) and test it: an integration test runs as the integration user (`System.runAs`) and proves it can see and upsert the records it should, and no others.
5. Record the user, its permission set and its auth flow in the ARCH-002 inventory row.

## Deploy and environments
- **Deploy order:** objects and External ID fields → permission sets → External Credential → Named Credential → ECA / Connected App → events and channel members → code and Flows [high]. CDC members fail if the source object isn't in the org yet [high, sf-skills `integration-eventing-cdc-configure`].
- **Sandbox refresh:** a refreshed sandbox carries production endpoints and possibly production credentials; repoint Named Credentials and disable outbound jobs as the first post-refresh step [high].
- **Kill switch:** each integration can be stopped without a deploy through Custom Metadata (see `../architecture/api-and-integration.md` §3), and the switch is named in the runbook.

## AI-assisted building
- Use Salesforce's `integration-connectivity-generate` (credentials, callouts, events, External Services), `integration-connectivity-connected-app-configure` (Connected App / ECA), `integration-eventing-cdc-configure` and `integration-eventing-subscription-configure`. Their output is checked against this guide before it counts as built.
- Where these skills disagree with this pipeline, the pipeline wins: they include production deploy steps and scripts that list all orgs; the AI never deploys to production (HG-09) and writes only to write-allowed sandboxes (HG-11). See `../salesforce-official-skills.md`.
- The AI never asks for, prints or stores a secret. Credential values are typed by a human into the org.
- Every Named Credential, endpoint and event name in a ticket must exist in the project or the ARCH-002 inventory (AI-02).

## Anti-patterns
Endpoints or tokens in code or Custom Metadata · one shared "integration" user for all systems · integration user with an admin profile or "View All Data" · credential access in a profile or for all users · new Connected App without a reason · `full` scope · http Remote Site Settings · External ID without Unique · publish-immediately by default · subscribers that ignore redelivery · CDC to an external subscriber that can't see the records · secrets in chat, tickets or the repo.

## Enforcement
- Mapped in `../../guardrails/analyzer-map.yaml`: HG-03 `pmd:ApexSuggestUsingNamedCred`, `pmd:ApexInsecureEndpoint`; HG-01 `pmd:ApexCRUDViolation` for callout services.
- Not mapped yet, recommended for project config (proposal, needs approval per PR-14): `pmd:AvoidHardcodedCredentialsInHttpHeader`, `pmd:AvoidHardcodedCredentialsInVarAssign`, `pmd:AvoidHardcodedCredentialsInVarDecls`, `pmd:AvoidHardcodedCredentialsInFieldDecls`, `pmd:LimitConnectedAppScope`, `pmd:UseHttpsCallbackUrlConnectedApp`, `pmd:AvoidInsecureHttpRemoteSiteSetting`, `pmd:AvoidDisableProtocolSecurityRemoteSiteSetting`, `flow:TriggerCallout`.
- Ticket field `metadata` lists every Named Credential, External Credential, event and integration user the ticket touches (G3).
- Release runbook lists every post-deploy secret entry and consumer-key handover (PR-13, G5).

## Sources
- forcedotcom/sf-skills `integration-connectivity-generate` (named-credentials, platform-events guides), `integration-connectivity-connected-app-configure`, `integration-eventing-cdc-configure`, `integration-eventing-subscription-configure` (cloned 2026-11-20, commit 431c50f)
- Salesforce Help (release 264): Give Integration Users API Only Access — help.salesforce.com/s/articleView?id=platform.integration_user.htm; Special Behavior in Deployments — help.salesforce.com/s/articleView?id=platform.deploy_special_behavior.htm; Organization-Wide Sharing Defaults — help.salesforce.com/s/articleView?id=platform.security_sharing_owd_about.htm; Enable User External Credentials — help.salesforce.com/s/articleView?id=xcloud.nc_user_external_credentials.htm
- Salesforce Developers, REST API Developer Guide "Upsert Records Using sObject Rows by External ID" — developer.salesforce.com/docs/platform/api-rest/guide/resources-sobject-upsert-patch.html; Platform Events Developer Guide "Enterprise Messaging Platform Events" — developer.salesforce.com/docs/platform/platform-events/guide/platform-events-intro-emp.html; Change Data Capture Developer Guide "Required Permissions for Change Event Subscribers" — developer.salesforce.com/docs/platform/change-data-capture/guide/cdc-security-perms.html
- Apex Developer Guide "Testing HTTP Callouts by Implementing the HttpCalloutMock Interface" — developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexcode/apex_classes_restful_http_testing_httpcalloutmock.htm
- Agentforce Developer Guide "Verify Metadata and OpenAPI Specification Documents" — developer.salesforce.com/docs/ai/agentforce/guide/agent-apex-verify-spec.html
