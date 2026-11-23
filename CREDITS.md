# Credits

This package stands on other people's work. The guides cite these sources inline; this page names the people and organisations behind them. Thank you.

Authors checked on 2026-11-23 against the publisher, author or repository page (`[verified]`); widely documented origins of classic methods are `[high]`.

## Books
| Work | Author | Used in |
|---|---|---|
| *Clean Apex Code: Software Design for Salesforce Developers* (Apress, 2025) | **Pablo Gonzalez** [verified, Apress / O'Reilly listing] | `best-practices/clean-apex.md`, `best-practices/testing.md` |
| *Clean Code: A Handbook of Agile Software Craftsmanship* (Prentice Hall, 2008) | **Robert C. Martin** [high] | `best-practices/clean-apex.md` |
| *Patterns of Enterprise Application Architecture* (Addison-Wesley, 2002) — the basis of Apex Enterprise Patterns | **Martin Fowler** [high] | `best-practices/architecture/trigger-framework.md` (option C) |

## Open-source frameworks
| Project | Author / maintainers | Used in |
|---|---|---|
| sfdc-trigger-framework | **Kevin O'Hara**; documented fork by **David Schach** [verified, GitHub] | trigger framework, option A |
| Apex Trigger Actions Framework | **Mitch Spano** and contributors [verified, GitHub] | trigger framework, option B |
| Apex Enterprise Patterns (fflib-apex-common, ApexMocks) | created by **Andrew Fawcett** (FinancialForce); maintained by the Apex Enterprise Patterns community [verified, project history] | trigger framework, option C; structure levels |
| Nebula Logger | **Jonathan Gillespie** and contributors [verified, GitHub] | `best-practices/architecture/error-handling-logging.md` |

## Salesforce
Official documentation by **Salesforce, Inc.** and its documentation, architect and developer-relations teams:
- Salesforce Well-Architected and the Salesforce Architects decision guides (record-triggered automation, building forms, async processing, event-driven architecture), Integration Patterns and Practices
- Salesforce Help, release notes, Trailhead
- Developer guides: Apex, Apex Reference, Aura Components, LWC, Metadata API, REST API, Bulk API 2.0, Platform Events, Change Data Capture, Object Reference, Agentforce, Salesforce DX
- Salesforce Developers blog and podcast
- **forcedotcom/sf-skills** (official agent skills) and the Salesforce DX MCP server
- **Salesforce Code Analyzer**, built on PMD and other engines (below)

## Community articles
| Article | Author | Used in |
|---|---|---|
| "10 Mistakes Salesforce Architects Make When Scaling Flow" (Salesforce Ben) | **Christine Marshall** [verified, article byline] | `best-practices/build/flows.md` |
| "12 Salesforce Apex Best Practices" (Salesforce Ben) | **Alex Crisp** [verified, article byline] | `best-practices/build/apex.md` |
| Salesforce Ben reporting on profile permissions and DevOps Center; Gearset articles on DevOps Center | Salesforce Ben and Gearset authors | `best-practices/architecture/security-sharing.md`, `devops-packaging.md` |

## Methods and standards
| Method | Origin | Used in |
|---|---|---|
| Strangler fig migration | **Martin Fowler** [high] | `best-practices/patterns-and-migration.md` |
| WSJF (weighted shortest job first) | Scaled Agile Framework, building on **Donald Reinertsen**'s cost of delay [high] | `best-practices/patterns-and-migration.md` |
| Given/When/Then | **Dan North** and **Chris Matts** (behaviour-driven development) [high] | requirements, tickets, test cases |
| MoSCoW prioritisation | **Dai Clegg** [high] | `workflow/phases/04-requirements.md` |
| Arrange-Act-Assert | **Bill Wake** [high] | `best-practices/testing.md` |
| Trunk-based development | **Paul Hammant** (trunkbaseddevelopment.com) [high] | `best-practices/architecture/branching-environments.md` |
| GitFlow branching model | **Vincent Driessen** (2010) [high] | `best-practices/architecture/branching-environments.md` |
| Problem Details for HTTP APIs (RFC 7807, now RFC 9457) | **Mark Nottingham** and **Erik Wilde** (IETF) [high] | `best-practices/architecture/api-and-integration.md` |
| EU AI Act, Article 50 | European Union; cited from the European Commission AI Act Service Desk | `best-practices/build/agentforce.md` |

## Tools this package runs on
PMD (the PMD project), Jest (Jest contributors / OpenJS Foundation), Playwright (Microsoft), Chrome DevTools Recorder (Google Chrome team), PyYAML (the YAML project), Salesforce CLI, git, GitHub CLI, Claude Code (Anthropic).

Missing someone? Add them here and to the guide's Sources list.
