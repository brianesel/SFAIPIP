# Agentforce agents

**Verdict:** an Agentforce agent is production software that decides at run time which of your actions to call, so build it like code with a non-deterministic front end: design and sign off the agent spec first, start with one focused scope, give every action a precise description and a least-privilege implementation, put every rule with a consequence in Apex or Flow (not in the prompt), require confirmation or a human for anything irreversible, give it a staffed escalation path, test it with a saved test suite including adversarial cases, and switch on tracing before go-live. Agentforce changes every release: check product specifics against the current docs.
Sources: see end. Confidence: non-negotiables [high]; product specifics [med] unless the sf-skills text confirms them; analyzer rule names [verified] against `sf code-analyzer rules --rule-selector all` on 2026-11-20.

## Scope
Agents customers build and run in Salesforce: Agent Script agents (`AiAuthoringBundle`), legacy Agent Builder agents (`GenAiPlannerBundle`, `GenAiPlugin`), their topics or subagents, instructions, actions (Flow, invocable Apex, prompt templates, standard actions), grounding, escalation, tests and monitoring. **Not** the AI that builds code in this pipeline: that is `../ai-assisted-development.md`. Quality bar and pillar targets: `../well-architected.md` (Agentic Enterprise lens; profile `agentic` in `../../guardrails/rubric/pillars.yaml`).

Terms: legacy Agent Builder calls the scope units **topics**; Agent Script calls them **subagents** [med, sf-skills `agentforce-generate` and `service-agentforce-human-escalation-configure`]. The rules below apply to both.

## Non-negotiables
| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | **An agent only where the job needs language judgement.** Deterministic work (fixed rules, calculations, routing by field value) stays in Flow or Apex. The design records why an agent, the use cases, the data it reads and the actions it can take, and is signed off before build | an agent costs per action and can choose wrongly; a Flow can't [high] | G2; PR-15 when unclear; agent spec in `docs/design/` |
| 2 | **Start with one focused scope; split only at a real boundary** (different objective, instructions, actions, authority or escalation) | splitting too early creates routing errors between topics [high, sf-skills `agentforce-generate` rule 7] | review |
| 3 | **Every action and every input / output has a precise description** written for the model: what it does, when to use it, what each field means. Outputs are structured with a status field (`isSuccess`, `isFound`) and a message | the agent sees only the action definition, never the Flow or Apex inside [high, sf-skills `actions-reference.md`] | review; agent tests |
| 4 | **Action implementations meet the same bar as any code:** invocable Apex declares sharing, queries in user mode and checks CRUD / FLS; Flows follow `flows.md`; no user input passed into a without-sharing element | the model passes user text into your code; whatever the code allows, any user can reach through the agent | HG-01, HG-06, HG-02; `pmd:ApexCRUDViolation`, `pmd:ApexSharingViolations`, `pmd:ApexSOQLInjection`, `sfge:DatabaseOperationsMustUseWithSharing`, `flow:PreventPassingUserDataIntoElementWithoutSharing` |
| 5 | **Data access during reasoning is least privilege.** Service agents run as a dedicated agent user; employee agents run as the signed-in user [med, sf-skills `agent-user-setup.md`]. The agent user's permission sets are the agent's data reach: scope them to the use cases, one `<AgentName>_Access` permission set, no admin rights | anything the agent user can read can end up in an answer to any customer | review; `permissions-access.md`; test as the agent user |
| 6 | **Rules with consequences are enforced in code, not instructions.** Eligibility, limits, amounts, dates and identity checks are computed or validated in Apex / Flow or runtime conditions; instructions handle intent and tone | instructions are followed most of the time, not always; smaller models follow them less [high, sf-skills rule 13; small-model part: field experience, med] | review; agent tests with boundary cases |
| 7 | **Irreversible or consequential actions need confirmation or a human.** Ask the user to confirm before a write (action-level confirmation where offered [med, sf-skills `actions-reference.md`]); money, legal effect or customer commitments go through a human approver | a wrong or manipulated call can't be taken back | review; G2 records which actions need approval |
| 8 | **A working human escalation path for customer-facing agents:** an escalation topic or action that routes to a staffed Omni-Channel queue with at least one active member, plus a failure threshold written into the instructions | a queue without members never reaches a human; the threshold is instruction text, not a metadata setting [med, sf-skills `service-agentforce-human-escalation-configure`, default two consecutive failures] | escalation test in UAT; runtime check |
| 9 | **User text and grounded records are data, not instructions.** Instructions say what the agent must not do (scope, no credentials or payment data, no internal scores shown), and the agent says it is an AI where the design requires it | prompt injection and over-sharing are the main agent risks [med, sf-skills `safety-review-reference.md`; EU AI Act Art 50 decision per project, not legal advice] | safety review; adversarial tests |
| 10 | **A saved agent test suite per agent:** one or more cases per use case with expected topic, actions and outcome, plus off-topic, escalation and adversarial cases. Assert on topic, action and outcome, not exact wording | without a suite, regressions in routing go unseen after each change [high, sf-skills `agentforce-test`] | PR-08 (agreed test set); G4 |
| 11 | **Live actions only in a verified sandbox with test data.** Use simulated actions in preview; run live actions only against a write-allowed sandbox | a preview with live actions really writes data [high, sf-skills `agentforce-generate` rule 3] | HG-11; `org_guard.py` |
| 12 | **Publish and activate are release steps.** Draft, validate and preview freely in sandboxes; activation in production is a human release with a recorded rollback (previous version) | activation is the moment real users meet the agent | HG-09; G5; PR-13 |
| 13 | **Observability before go-live:** tracing on, an owner who reviews session traces and alerts (escalation rate, failures), and a credit budget with consumption alerts | agent failures are silent unless someone looks at traces; usage is metered per action [med: reading of Salesforce Help, release 264] | release checklist (07); run book |

## Structure and naming
| Item | Convention | Example |
|---|---|---|
| Agent API name | `<Domain>_<Audience>_Agent` | `Order_Service_Agent` |
| Topic / subagent | named by user intent, not by implementation; one-line scope description | `order_status`, `returns`, `escalation`, `off_topic` |
| Action (Flow) | `<Object>_Agent_<VerbPurpose>`, autolaunched, typed I/O (see `flows.md`) | `Order_Agent_GetStatus` |
| Action (Apex) | one invocable class per action, `<Purpose>Action`; label and description match the agent's action definition | `OrderStatusAction` |
| Prompt template | `<Purpose>_<Type>`; grounding inputs named | `Case_Summary_Flex` |
| Permission set for the agent user | `<AgentName>_Access` [med, sf-skills `agent-user-setup.md`] | `Order_Service_Agent_Access` |
| Test suites | `<AgentName>_Tests`, `<AgentName>_Security` | `Order_Service_Agent_Security` |

These names are a proposal; the project's pattern register decides (PR-06).

## Building blocks
| Block | Do | Avoid |
|---|---|---|
| Instructions | short, specific, per topic; "always" / "never" with a condition; formatting rules in the instructions, not in the scope text [med: field experience]; language rules in every topic, not only once [med: field test 2026-10-24] | business facts mixed into glossaries; general bans the model can't anchor ("only talk about X") |
| Actions | reuse standard actions first; one action, one job; return only the fields the agent needs | actions that write without a status; outputs with internal scores marked displayable |
| Prompt templates | grounded on named record fields or retrieval; output format stated | asking the model to calculate dates, sums or eligibility |
| Grounding / knowledge | curated sources with an owner and a refresh process; the agent user can read exactly those | grounding on everything the agent user happens to see |
| Escalation | reachable from every topic; context passed to the human | an escalation action that only says "contact support" |

## Lifecycle: design to production
1. **Design (02/04):** agent spec with use cases, out-of-scope list, actions and which need approval, data sources, agent user access, escalation, AI disclosure and high-risk decisions, expected volume and credit ceiling [med: field practice]. Signed off at G2.
2. **Tests first (06):** the agreed test set per PR-08 includes the agent test cases (use cases, off-topic, escalation, adversarial) before actions are built.
3. **Actions:** build and unit-test each Flow or Apex action on its own first (Apex tests, Flow tests); an action that fails alone will fail inside the agent.
4. **Draft and preview** in a write-allowed sandbox with simulated actions; then a run with live actions on test data.
5. **Run the saved suite** after every change to instructions, actions or topics; failing cases go back through the loop guard (PR-09).
6. **Browser walk-through as a real user of the target channel** before calling it done: preview doesn't see the full product context [med: field test].
7. **Release (07):** human publishes and activates in production; previous version noted as rollback; tracing, alerts and credit alerts checked the same day.
8. **Run:** review traces and escalations on a fixed rhythm; a recurring failure becomes a ticket with a new test case first.

## AI-assisted building
- Use Salesforce's `agentforce-generate` (Agent Script authoring, validation, deploy, publish), `agentforce-test` (preview, batch suites, security tests), `agentforce-observe` (traces, health alerts), `agentforce-architecture-analyze` (read-only call graph), `agentforce-persona-generate` (persona and boundaries), `service-agentforce-human-escalation-configure` and `platform-tracing-agentforce-configure` (`AgentforcePlatformTracingSettings`; needs Data Cloud and the `PlatformObservability` org permission [med, sf-skills; the skill's API version note is internally inconsistent, check the Metadata API reference]).
- The pipeline's rules win where the skills differ: the AI never publishes or activates in production (HG-09), uses live actions only in write-allowed sandboxes (HG-11), and security test generation needs the human's go-ahead (same as `agentforce-test` Mode C).
- Agent, topic, action, object and field names in a ticket must exist (AI-02). Don't state Agentforce limits, credit rates or feature availability from memory; cite the current docs or tag `[dunno]`.
- The AI that builds the agent is not the reviewer of the agent: safety review and test sign-off are human (AI-01, AI-05).

## Anti-patterns
An agent for a job a Flow can do · many topics before the first one works · vague action descriptions ("Get data") · business rules only in instructions · invocable Apex without sharing or FLS checks · agent user with admin or "View All Data" · writes without confirmation · escalation to an empty queue · no saved test suite · testing with live actions in a shared or production org · activating by hand in production · no tracing or owner after go-live · quoting credit costs from memory.

## Enforcement
- Code Analyzer on action code: HG-01 `pmd:ApexCRUDViolation`, `pmd:ApexSOQLInjection`, `flow:PreventPassingUserDataIntoElementWithoutSharing`; HG-06 `pmd:ApexSharingViolations`; HG-02 `pmd:OperationWithLimitsInLoop`, `flow:DbInLoop` (mapped in `../../guardrails/analyzer-map.yaml`). Recommended addition (proposal, PR-14): `sfge:DatabaseOperationsMustUseWithSharing`.
- No analyzer rule reads `.agent` files or agent metadata [verified: inventory of 719 rules]. Checks there are the sf-skills local compiler and safety review, the agent test suite, and human review.
- G2 checks the agent spec (use cases, actions needing approval, escalation, AI disclosure decision); G4 needs a passing agent test suite with evidence; G5 covers activation and rollback.
- Evaluation (01) scores agents against the `agentic` pillar profile (agent-specific checks: action approval, data access during reasoning, escalation path).

## Sources
- forcedotcom/sf-skills `agentforce-generate` (incl. `actions-reference.md`, `agent-user-setup.md`, `safety-review-reference.md`), `agentforce-test`, `agentforce-observe`, `agentforce-architecture-analyze`, `agentforce-persona-generate`, `service-agentforce-human-escalation-configure`, `platform-tracing-agentforce-configure` (cloned 2026-11-20, commit 431c50f)
- Salesforce Developers, Agentforce Developer Guide — developer.salesforce.com/docs/einstein/genai/guide/
- Salesforce Help, Considerations for Agentforce Employee Agent; Manage Consumption Threshold Alerts (release 264)
- Salesforce Well-Architected, Agentic Enterprise lens — architect.salesforce.com
