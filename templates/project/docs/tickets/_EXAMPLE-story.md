---
key: STORY-001
type: story
status: ready
title: "[Invoicing] Sales rep creates invoice from closed-won opportunity"
parent: EPIC-001
business_process: Opportunity to invoice
source: "Jane PM · 2026-11-20 · requirements workshop"
criticality: high
repeat_search: 'Searched docs/tickets: "invoice", process=Opportunity to invoice → 0 hits'
req: [REQ-001]
user_story: "As a sales rep, I want to create an invoice from a closed-won opportunity, so that billing starts the same day."
business_value: "Billing lead time 5 days → same day — Source: Jane PM, 2026-11-20"
scope_in: "Invoice header + lines from opportunity products"
scope_out: "Payment collection, credit notes"
owner: "Dev A"
acceptance_criteria:
  - "Given a closed-won opportunity with 2 products, when the rep clicks Create invoice, then 1 Invoice__c with 2 lines exists"
  - "(negative) Given an open opportunity, when the rep clicks Create invoice, then an error says the opportunity must be closed-won and no invoice is created"
metadata:
  - {type: object, name: Invoice__c, state: new}
  - {type: field,  name: Opportunity.StageName, state: existing}
  - {type: class,  name: InvoiceService, state: new}
pattern: {follows: target, adr: ADR-001}
access: "Permission set Invoice_User (new)"
test_tier: both
hard_gate_risk: none
pillar_impact: {trust: "0", reliability: "+", opex: "+", cost: "0", fairness: "0"}
migration_items: none
dependencies: none
estimate: M
---
## 1. Business requirements
...
## 2. Background
...
## 3. Technical requirements
...
## 4. Acceptance criteria
See front matter.
## 5. Detail implementation requirements
...
