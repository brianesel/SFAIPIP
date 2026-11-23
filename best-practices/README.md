# Best practices

What good looks like, and why. Guardrails (`../guardrails/`) are the subset that is enforced; practices here are the target the team aims for and the reasoning behind each guardrail.

| File | Topic | Main sources |
|---|---|---|
| `well-architected.md` | pillars, trade-offs, targets | Salesforce Well-Architected Framework (5 pillars, 2026) |
| `clean-apex.md` | code design | *Clean Apex Code* (P. Gonzalez, Apress 2025) chapter topics, *Clean Code* (R. C. Martin) |
| `testing.md` | test tiers, short tests, test design | Clean Apex Code ch. 12, Apex testing practice |
| `patterns-and-migration.md` | current vs target patterns, team size, migration cost | strangler-fig practice, WSJF |
| `requirements-and-tickets.md` | REQs, tickets, change control | to-or-not-to-ticket rules |
| `ai-assisted-development.md` | how AI is used safely in this pipeline | this package's AI rules |
| `salesforce-official-skills.md` | how this pipeline uses Salesforce's official skills + DX MCP server; conflicts and precedence | forcedotcom/sf-skills, DX MCP server docs |
| `build/` | 10 build guides, one per metadata area: Flows, Apex, permissions & access, objects & fields, validation rules & formulas, Lightning pages & UI, LWC, reports & dashboards, integration metadata, Agentforce | Salesforce official skills (`forcedotcom/sf-skills`), Salesforce Architects decision guides and Well-Architected, Salesforce Help, Salesforce developer guides (Apex, LWC, Metadata API, REST API, Platform Events, Agentforce, Object Reference), Salesforce release notes, Salesforce Developers blog, Code Analyzer v5 rules |
| `architecture/` | 9 reference architectures (triggers, API & integration, async, errors & logging, data model / LDV, security & sharing, configuration, LWC data access, DevOps) + decision cards ARCH-001…006 | Salesforce Architects decision guides, integration patterns, open-source frameworks |
