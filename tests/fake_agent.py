#!/usr/bin/env python3
"""Stand-in for `claude -p` in tests: acts as the agent named in env SFG_AGENT. Mode via SFG_FAKE_MODE."""
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

PKG = Path(__file__).resolve().parents[1]
agent, key, n = os.environ["SFG_AGENT"], os.environ["SFG_TICKET"], os.environ.get("SFG_ITER", "0")
mode = os.environ.get("SFG_FAKE_MODE", "good")
root = Path.cwd()
d = root / "docs/tests" / key
sys.stdin.read()
with open(root / ".agent-calls", "a") as f:
    f.write(f"{agent} {n} argv={len(sys.argv)}\n")

TICKET = f"""---
key: {key}
type: story
status: ready
title: "[Invoicing] Rep creates invoice from closed-won opportunity"
parent: EPIC-001
business_process: Opportunity to invoice
source: "PM · 2026-11-23 · request"
criticality: high
repeat_search: 'Searched docs/tickets: "invoice" → 0 hits'
req: [REQ-001]
user_story: "As a sales rep, I want an invoice from a closed-won opportunity, so that billing starts the same day."
business_value: "Same-day billing — Source: PM, 2026-11-23"
scope_in: "Invoice header"
scope_out: "Payments"
owner: "Dev A"
acceptance_criteria:
  - "Given a closed-won opportunity, when the rep clicks Create invoice, then 1 Invoice__c exists"
  - "(negative) Given an open opportunity, when the rep clicks Create invoice, then an error is shown and no invoice is created"
metadata:
  - {{type: class, name: InvoiceService, state: new}}
pattern: {{follows: target, adr: ADR-001}}
access: none
test_tier: unit
hard_gate_risk: none
pillar_impact: {{trust: "0", reliability: "+", opex: "0", cost: "0", fairness: "0"}}
migration_items: none
dependencies: none
estimate: S
---
## 1. Business requirements
Invoice from opportunity.
"""


def case(cid, cat, ac, meth, title):
    return {"id": cid, "ac": [ac], "category": cat, "title": title, "given": "an opportunity",
            "when": "the rep clicks Create invoice", "then": "the expected outcome", "level": "unit",
            "automation": {"type": "apex", "test": f"InvoiceServiceTest.{meth}"}}


if agent == "intake":
    if mode == "questions" and not (d / "questions.md").exists():
        (d / "questions.md").write_text("## Round 1\n- [ ] Q: Which stage counts as closed-won?\n  A:\n")
    else:
        (root / "docs/tickets" / f"{key}.md").write_text(TICKET)
elif agent == "test-designer":
    if (d / "tester.yaml").exists():
        (root / ".blind-violation").write_text("tester.yaml visible")
    (d / "ai.yaml").write_text(yaml.safe_dump({"ticket": key, "cases": [
        case("A-01", "happy", "AC-1", "createsInvoice", "creates invoice for closed-won"),
        case("A-02", "negative", "AC-2", "rejectsOpen", "rejects open opportunity")]}))
elif agent == "developer":
    if mode == "stuck":
        sys.exit(0)
    cls = root / "force-app/main/default/classes"
    cls.mkdir(parents=True, exist_ok=True)
    (cls / "InvoiceService.cls").write_text(f"public with sharing class InvoiceService {{ // iter {n}\n}}\n")
    (cls / "InvoiceServiceTest.cls").write_text(
        "@IsTest\nprivate class InvoiceServiceTest {\n  @IsTest static void createsInvoice() {}\n  @IsTest static void rejectsOpen() {}\n}\n")
    tr = root / "docs/delivery/traceability.md"
    if key not in tr.read_text():
        tr.write_text(tr.read_text() + f"| REQ-001 | {key} | InvoiceServiceTest.createsInvoice | in progress |\n")
elif agent == "functional-tester":
    outcome = "Fail" if mode in ("stuck", "failing") else "Pass"
    run = {"result": {"tests": [{"FullName": f"InvoiceServiceTest.{m}", "Outcome": outcome, "Message": ""}
                                for m in ("createsInvoice", "rejectsOpen")],
                      "coverage": {"coverage": [{"name": "InvoiceService", "coveredPercent": 95}]}}}
    (root / ".sfg/run").mkdir(parents=True, exist_ok=True)
    (root / ".sfg/run/test-result.json").write_text(json.dumps(run))
    subprocess.run([sys.executable, str(PKG / "tools/dev_cycle.py"), "import-apex", key, "--file", ".sfg/run/test-result.json"], check=True)
    (d / "code-analyzer.json").write_text(json.dumps({"violations": []}))
elif agent == "tech-lead-reviewer":
    (d / "review").mkdir(exist_ok=True)
    findings = []
    if mode == "review_blocking_once":
        findings = [{"id": "R-01", "rule": "HG-01", "file": "force-app/main/default/classes/InvoiceService.cls", "line": 1,
                     "severity": "blocking", "evidence": "query without USER_MODE", "fix": "add WITH USER_MODE",
                     "status": "open" if n == "1" else "fixed"}]
    (d / "review" / f"iter-{n}.yaml").write_text(yaml.safe_dump({"iteration": int(n), "commit": "working tree",
                                                                 "verdict": "pass", "findings": findings}))
