"""Unit tests for impact.py, recording_to_cases.py, system_map.py and uat.py. Run: python3 -m unittest discover tests"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))

FLOW = """<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
  <status>Active</status>
  <start><object>Opportunity</object><recordTriggerType>Update</recordTriggerType><triggerType>RecordBeforeSave</triggerType></start>
  <assignments><name>SetFlag</name><assignmentItems><assignToReference>$Record.Billing_Ready__c</assignToReference></assignmentItems></assignments>
</Flow>
"""
FLOW_AFTER = """<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
  <status>Active</status>
  <start><object>Opportunity</object><recordTriggerType>CreateAndUpdate</recordTriggerType><triggerType>RecordAfterSave</triggerType></start>
  <recordUpdates><name>U</name><object>Account</object><inputAssignments><field>Last_Won__c</field></inputAssignments></recordUpdates>
</Flow>
"""
VR = """<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata"><active>true</active></ValidationRule>
"""


def sh(cwd, *args, env=None):
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, env=env)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "proj"
        sh(PKG, sys.executable, "tools/init_project.py", str(self.root))
        src = self.root / "force-app/main/default"
        (src / "flows").mkdir(parents=True)
        (src / "flows/Opp_Before.flow-meta.xml").write_text(FLOW)
        (src / "flows/Opp_After.flow-meta.xml").write_text(FLOW_AFTER)
        (src / "triggers").mkdir()
        (src / "triggers/OpportunityTrigger.trigger").write_text(
            "trigger OpportunityTrigger on Opportunity (before update, after insert, after update) { OpportunityHandler.run(); }")
        (src / "classes").mkdir()
        (src / "classes/OpportunityHandler.cls").write_text(
            "public with sharing class OpportunityHandler { public static void run() { InvoiceService.create(); } }")
        (src / "classes/InvoiceService.cls").write_text(
            "public with sharing class InvoiceService { @InvocableMethod public static void create() { Invoice__c i; i.Amount__c = 1; } }")
        (src / "classes/InvoiceServiceTest.cls").write_text("@IsTest private class InvoiceServiceTest { @IsTest static void createsInvoice() { InvoiceService.create(); } }")
        (src / "objects/Opportunity/validationRules").mkdir(parents=True)
        (src / "objects/Opportunity/validationRules/Close_Date_Required.validationRule-meta.xml").write_text(VR)
        for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@e.com"), ("config", "user.name", "T"),
                     ("add", "-A"), ("commit", "-qm", "init")):
            sh(self.root, "git", *args)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def tool(self, script, *args):
        return sh(self.root, sys.executable, str(PKG / "tools" / script), *args, "--project", str(self.root))


class SystemMapTest(Base):
    def feature(self, components, status="live"):
        d = self.root / "docs/wiki/map/features"
        d.mkdir(parents=True, exist_ok=True)
        (d / "FEAT-01-invoice.md").write_text("---\n" + yaml.safe_dump({
            "id": "FEAT-01", "purpose": "Create invoices from won opportunities", "aliases": ["billing", "dunning"],
            "status": status, "processes": ["PROC-01#2"], "components": components,
            "tests": {"automated": ["InvoiceServiceTest.createsInvoice"], "uat": []}}) + "---\nWritten notes.\n")
        p = self.root / "docs/wiki/map/processes"
        p.mkdir(parents=True, exist_ok=True)
        (p / "PROC-01-order-to-cash.md").write_text("---\n" + yaml.safe_dump({
            "id": "PROC-01", "name": "Order to cash", "steps": [{"n": 1, "name": "Win deal", "role": "Sales rep", "features": []},
                                                              {"n": 2, "name": "Invoice", "role": "Finance", "features": ["FEAT-01"]}]}) + "---\n")

    def test_generate_and_queries(self):
        self.feature([{"type": "apexclass", "name": "InvoiceService"}])
        r = self.tool("system_map.py", "generate")
        self.assertEqual(r.returncode, 0, r.stderr)
        q = lambda *a: self.tool("system_map.py", "query", *a).stdout
        fires = q("fires", "Opportunity", "update")
        self.assertLess(fires.index("Opp_Before"), fires.index("OpportunityTrigger"))
        self.assertLess(fires.index("Close_Date_Required"), fires.index("after trigger"))
        self.assertLess(fires.index("after trigger"), fires.index("Opp_After"))
        self.assertIn("flow:Opp_Before [high]", q("writes", "Opportunity.Billing_Ready__c"))
        self.assertIn("flow:Opp_After [high]", q("writes", "Account.Last_Won__c"))
        self.assertIn("apexclass:InvoiceService [med]", q("writes", "Invoice__c.Amount__c"))
        self.assertIn("component: OpportunityHandler", q("used-by", "InvoiceService"))
        impact = q("impact", "InvoiceService")
        self.assertIn("references (2nd level): OpportunityTrigger", impact)
        self.assertIn("feature: FEAT-01", impact)
        self.assertIn("process: PROC-01", impact)
        self.assertIn("re-run test: InvoiceServiceTest.createsInvoice", impact)
        self.assertIn("FEAT-01: InvoiceService", q("step", "PROC-01#2"))
        self.assertIn("FEAT-01", self.tool("system_map.py", "search", "dunning").stdout)
        self.assertTrue((self.root / "docs/wiki/map/objects/Opportunity.md").exists())

    def test_lint_unknown_name_stale_map_and_unmapped_change(self):
        self.feature([{"type": "apexclass", "name": "InvoiceServcie"}])
        self.tool("system_map.py", "generate")
        r = self.tool("system_map.py", "lint")
        self.assertIn("InvoiceServcie", r.stdout)
        self.feature([{"type": "apexclass", "name": "InvoiceService"}])
        self.tool("system_map.py", "generate")
        self.assertEqual(self.tool("system_map.py", "lint").returncode, 0)
        sh(self.root, "git", "add", "-A")
        sh(self.root, "git", "commit", "-qm", "map")
        sh(self.root, "git", "switch", "-qc", "feature/X")
        (self.root / "force-app/main/default/classes/PaymentService.cls").write_text("public with sharing class PaymentService {}")
        r = self.tool("system_map.py", "lint", "--changed")
        self.assertIn("out of date", r.stdout)
        self.assertIn("PaymentService' is not in any feature", r.stdout)

    def test_question_set(self):
        self.feature([{"type": "apexclass", "name": "InvoiceService"}])
        self.tool("system_map.py", "generate")
        (self.root / "docs/wiki/_data/map/questions.yaml").write_text(yaml.safe_dump({"questions": [
            {"q": "What writes Billing_Ready__c?", "query": ["writes", "Opportunity.Billing_Ready__c"], "expect": ["Opp_Before"]},
            {"q": "Where is billing handled?", "query": ["search", "billing"], "expect": ["FEAT-01"]},
            {"q": "Deliberately wrong", "query": ["writes", "Opportunity.Nope__c"], "expect": ["X"]}]}))
        out = self.tool("system_map.py", "questions").stdout
        self.assertIn("2/3 answered", out)


class ContextPackTest(Base):
    def test_execution_order_and_writers(self):
        (self.root / "docs/tickets/T-2.md").write_text("---\nkey: T-2\ntitle: x\nmetadata:\n"
            "  - {type: field, name: Opportunity.Billing_Ready__c, state: existing}\n  - {type: class, name: InvoiceService, state: existing}\n---\n")
        r = self.tool("context_pack.py", "T-2")
        self.assertEqual(r.returncode, 0, r.stderr)
        text = (self.root / "docs/tests/T-2/context.md").read_text()
        self.assertIn("Opportunity on update: flow:Opp_Before → trigger:OpportunityTrigger", text)
        self.assertIn("Opportunity.Billing_Ready__c written by: flow:Opp_Before [high]", text)
        self.assertIn("InvoiceServiceTest", text)
        self.assertIn("Setup Audit Trail", text)


class ImpactTest(Base):
    def setUp(self):
        super().setUp()
        (self.root / "docs/tickets/T-1.md").write_text("---\nkey: T-1\nmetadata:\n  - {type: class, name: InvoiceService, state: existing}\n"
                                                         "  - {type: field, name: Invoice__c.Amount__c, state: existing}\n---\n")
        d = self.root / "docs/tests/T-1"
        d.mkdir(parents=True)
        (d / "agreed.yaml").write_text(yaml.safe_dump({"cases": [{"id": "C-01", "status": "accepted",
                                                                   "automation": {"type": "apex", "test": "InvoiceServiceTest.createsInvoice"}}]}))
        self.d = d

    def run_file(self, name, outcomes):
        p = self.tmp / name
        p.write_text(json.dumps({"result": {"tests": [{"FullName": k, "Outcome": v} for k, v in outcomes.items()]}}))
        return str(p)

    def snap(self, name, data):
        p = self.tmp / name
        p.write_text(json.dumps(data))
        return str(p)

    def test_flags_unapproved_changes_and_accepts_approved(self):
        base_run = self.run_file("b.json", {"AccountTest.keepsOwner": "Pass", "OldTest.gone": "Pass", "InvoiceServiceTest.createsInvoice": "Fail"})
        base_snap = self.snap("bs.json", {"Account.001A": {"Rating": "Hot"}, "Invoice__c.a01": {"Amount__c": 1}})
        self.tool("impact.py", "baseline", "T-1", "--file", base_run, "--snapshot", base_snap)
        sh(self.root, "git", "switch", "-qc", "feature/T-1")
        (self.root / "force-app/main/default/classes/InvoiceService.cls").write_text("public with sharing class InvoiceService {}")
        (self.root / "force-app/main/default/classes/OpportunityHandler.cls").write_text("public with sharing class OpportunityHandler {}")
        now_run = self.run_file("n.json", {"AccountTest.keepsOwner": "Fail", "InvoiceServiceTest.createsInvoice": "Pass"})
        now_snap = self.snap("ns.json", {"Account.001A": {"Rating": "Cold"}, "Invoice__c.a01": {"Amount__c": 2}})
        self.tool("impact.py", "compare", "T-1", "--file", now_run, "--snapshot", now_snap, "--iter", "1")
        doc = yaml.safe_load((self.d / "impact/iter-1.yaml").read_text())
        cls = {i["item"]: i["class"] for i in doc["impacts"]}
        self.assertEqual(cls["AccountTest.keepsOwner"], "unapproved")
        self.assertEqual(cls["OldTest.gone"], "unapproved")
        self.assertEqual(cls["InvoiceServiceTest.createsInvoice"], "in_scope")
        self.assertEqual(cls["Account.001A.Rating"], "unapproved")
        self.assertEqual(cls["Invoice__c.a01.Amount__c"], "in_scope")
        self.assertEqual(cls["OpportunityHandler"], "unapproved")
        self.assertNotIn("InvoiceService", cls)
        self.assertEqual(self.tool("impact.py", "check", "T-1").returncode, 1)
        ids = [i["id"] for i in doc["impacts"] if i["class"] == "unapproved"]
        (self.d / "impact-approvals.yaml").write_text(yaml.safe_dump({"approvals": [
            {"id": i, "approved_by": "Tech Lead", "date": "2026-11-23", "reason": "expected"} for i in ids]}))
        self.assertEqual(self.tool("impact.py", "check", "T-1").returncode, 0)


class RecordingTest(Base):
    def test_devtools_and_playwright(self):
        dev = self.tmp / "create-invoice.json"
        dev.write_text(json.dumps({"title": "Create invoice", "steps": [
            {"type": "setViewport", "width": 1200},
            {"type": "navigate", "url": "https://x.sandbox.lightning.force.com/006A"},
            {"type": "click", "selectors": [["aria/Create Invoice"], ["#btn"]]},
            {"type": "change", "value": "100", "selectors": [["aria/Amount"]]},
            {"type": "waitForElement", "selectors": [["aria/Invoice created"]]}]}))
        pw = self.tmp / "reject.spec.ts"
        pw.write_text("test('Reject open opportunity', async ({ page }) => {\n  await page.goto('https://x/006B');\n"
                      "  await page.getByRole('button', { name: 'Create Invoice' }).click();\n});\n")
        r = sh(self.root, sys.executable, str(PKG / "tools/recording_to_cases.py"), "T-1", str(dev), str(pw), "--project", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        cases = yaml.safe_load((self.root / "docs/tests/T-1/tester.draft.yaml").read_text())["cases"]
        self.assertEqual(cases[0]["title"], "Create invoice")
        self.assertIn("click 'Create Invoice'", cases[0]["when"])
        self.assertIn("enter '100' in 'Amount'", cases[0]["when"])
        self.assertIn("'Invoice created' is shown", cases[0]["then"])
        self.assertEqual(cases[1]["title"], "Reject open opportunity")
        self.assertIn("INFERRED", cases[1]["then"])
        self.assertFalse((self.root / "docs/tests/T-1/tester.yaml").exists())


class UatTest(Base):
    def setUp(self):
        super().setUp()
        cfg_p = self.root / "guardrails.project.yaml"
        cfg = yaml.safe_load(cfg_p.read_text())
        cfg["orgs"]["production"] = ["prod"]
        cfg["uat"] = {"personas": {"sales_rep": {"alias": "uat-rep"}, "boss": {"alias": "prod"}}}
        cfg_p.write_text(yaml.safe_dump(cfg))
        self.facts = self.tmp / "facts.json"
        self.facts.write_text(json.dumps({"uat-rep": {"IsSandbox": True}, "prod": {"IsSandbox": False}}))
        bin_ = self.tmp / "bin"
        bin_.mkdir()
        (bin_ / "sf").write_text('#!/bin/sh\necho \'{"result": {"url": "https://x.sandbox.my.salesforce.com/secur/frontdoor.jsp?sid=SECRET"}}\'\n')
        report = {"suites": [{"title": "invoice", "specs": [
            {"title": "C-03 rep creates invoice", "tests": [{"results": [{"status": "passed", "attachments": [{"path": "shot.png"}]}]}]},
            {"title": "C-04 rep sees error", "tests": [{"results": [{"status": "failed", "error": {"message": "expected error banner\nmore"}}]}]}],
            "suites": []}], "note": "logged in via https://x.sandbox.my.salesforce.com/secur/frontdoor.jsp?sid=SECRET"}
        (bin_ / "npx").write_text("#!/bin/sh\ncat <<'EOF'\n" + json.dumps(report) + "\nEOF\n")
        for f in bin_.iterdir():
            f.chmod(0o755)
        self.env = {**__import__("os").environ, "PATH": f"{bin_}:{__import__('os').environ['PATH']}", "SFG_ORG_FACTS": str(self.facts)}
        d = self.root / "docs/tests/T-1"
        d.mkdir(parents=True)
        mk = lambda cid: {"id": cid, "status": "accepted", "level": "uat", "automation": {"type": "manual", "test": "-"}}
        (d / "agreed.yaml").write_text(yaml.safe_dump({"cases": [mk("C-03"), mk("C-04"), mk("C-05"),
                                                                  {"id": "C-01", "status": "accepted", "level": "unit"}]}))
        self.d = d

    def uat(self, *args):
        return sh(self.root, sys.executable, str(PKG / "tools/uat.py"), *args, "--project", str(self.root), env=self.env)

    def test_refuses_production_persona(self):
        r = self.uat("run", "T-1", "boss", "--iter", "1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("production", r.stderr)

    def test_run_scrubs_login_url_and_import_maps_cases(self):
        r = self.uat("run", "T-1", "sales_rep", "--iter", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("SECRET", r.stdout + r.stderr)
        rep = (self.d / "uat/sales_rep-iter-1.json").read_text()
        self.assertNotIn("SECRET", rep)
        self.uat("import", "T-1", "--iter", "1")
        res = yaml.safe_load((self.d / "results/iter-1.yaml").read_text())["results"]
        self.assertEqual(res["C-03"]["status"], "pass")
        self.assertIn("shot.png", res["C-03"]["evidence"])
        self.assertEqual(res["C-04"]["status"], "fail")
        self.assertIn("expected error banner", res["C-04"]["note"])
        self.assertEqual(res["C-05"]["status"], "blocked")
        self.assertNotIn("C-01", res)


class OrgLimitsGuardTest(Base):
    def setUp(self):
        super().setUp()
        cfg_p = self.root / "guardrails.project.yaml"
        cfg = yaml.safe_load(cfg_p.read_text())
        cfg["orgs"].update(write_allowed=["dev"], production=["prod"])
        cfg_p.write_text(yaml.safe_dump(cfg))
        self.cfg_p = cfg_p
        self.facts = self.tmp / "facts.json"
        self.facts.write_text(json.dumps({"dev": {"IsSandbox": True}, "prod": {"IsSandbox": False}}))
        self.limits = self.tmp / "limits.json"

    def set(self, dev_pct, prod_pct=100):
        lim = lambda pct: {"DailyApiRequests": {"max": 1000, "remaining": pct * 10}}
        self.limits.write_text(json.dumps({"dev": lim(dev_pct), "prod": lim(prod_pct)}))
        (self.root / ".sfg/limits.json").unlink(missing_ok=True)

    def guard(self, cmd):
        env = {**__import__("os").environ, "SFG_ORG_FACTS": str(self.facts), "SFG_ORG_LIMITS": str(self.limits)}
        return sh(self.root, sys.executable, str(PKG / "tools/org_guard.py"), "check", cmd, "--project", str(self.root), env=env)

    def test_reserve_blocks_reads_and_writes_but_not_recovery_commands(self):
        self.set(80)
        self.assertEqual(self.guard("sf data query -q 'SELECT Id FROM Account' --target-org dev").returncode, 0)
        self.assertEqual(self.guard("sf project deploy start --target-org dev").returncode, 0)
        self.set(30)
        r = self.guard("sf data query -q 'SELECT Id FROM Account' --target-org dev")
        self.assertEqual(r.returncode, 1)
        self.assertIn("HG-12", r.stdout)
        self.assertIn("300/1000", r.stdout)
        self.assertEqual(self.guard("sf project deploy start --target-org dev").returncode, 1)
        self.assertEqual(self.guard("sf org list limits --target-org dev").returncode, 0)
        self.assertEqual(self.guard("sf config get target-org").returncode, 0)
        self.assertIn("BLOCK", (self.root / ".sfg/guard-log.md").read_text())

    def test_production_reads_need_higher_reserve_and_unknown_limits_fail_closed(self):
        self.set(80, prod_pct=70)
        r = self.guard("sf data query -q 'SELECT Id FROM Account' --target-org prod")
        self.assertEqual(r.returncode, 1)
        self.assertIn("80% reserve", r.stdout)
        r = self.guard("sf data query -q 'SELECT Id FROM Account' --target-org other")
        self.assertEqual(r.returncode, 1)
        self.assertIn("fail closed", r.stdout)

    def test_disabled_policy_and_show(self):
        self.set(10)
        cfg = yaml.safe_load(self.cfg_p.read_text())
        cfg["orgs"]["limits"] = {"enabled": False}
        self.cfg_p.write_text(yaml.safe_dump(cfg))
        self.assertEqual(self.guard("sf data query -q 'SELECT Id FROM Account' --target-org dev").returncode, 0)
        env = {**__import__("os").environ, "SFG_ORG_LIMITS": str(self.limits)}
        out = sh(self.root, sys.executable, str(PKG / "tools/org_limits.py"), "show", "dev", "--project", str(self.root), env=env).stdout
        self.assertIn("DailyApiRequests: 100/1000", out)


if __name__ == "__main__":
    unittest.main()


class BaselineManifestTest(Base):
    def test_copied_valid_and_retrieve_is_read_only(self):
        import xml.etree.ElementTree as ET
        sys.path.insert(0, str(PKG / "tools"))
        from org_guard import classify
        f = self.root / "manifest/baseline-package.xml"
        self.assertTrue(f.exists(), "init_project.py copies the baseline manifest")
        ns = {"m": "http://soap.sforce.com/2006/04/metadata"}
        pkg = ET.parse(f).getroot()
        names = [t.findtext("m:name", namespaces=ns) for t in pkg.findall("m:types", ns)]
        self.assertEqual(len(names), len(set(names)), "each type once")
        for t in pkg.findall("m:types", ns):
            self.assertTrue(t.findall("m:members", ns), t.findtext("m:name", namespaces=ns))
        for needed in ("ApexClass", "ApexTrigger", "Flow", "Workflow", "CustomObject", "LightningComponentBundle",
                       "PermissionSet"):
            self.assertIn(needed, names, "system_map.py and scoring read this type")
        objects = [m.text for t in pkg.findall("m:types", ns) if t.findtext("m:name", namespaces=ns) == "CustomObject"
                   for m in t.findall("m:members", ns)]
        self.assertIn("*", objects)
        self.assertIn("Account", objects, "standard objects are named; * does not match them")
        self.assertRegex(pkg.findtext("m:version", namespaces=ns), r"^\d+\.0$")
        kind, _ = classify(["project", "retrieve", "start", "--manifest", str(f), "--target-org", "eval"])
        self.assertEqual(kind, "read")


class McpGuardTest(OrgLimitsGuardTest):
    def hook(self, tool, tin):
        env = {**__import__("os").environ, "SFG_ORG_FACTS": str(self.facts), "SFG_ORG_LIMITS": str(self.limits)}
        payload = json.dumps({"tool_name": tool, "tool_input": tin, "cwd": str(self.root)})
        return subprocess.run([sys.executable, str(PKG / "tools/org_guard.py"), "--hook"], input=payload,
                              capture_output=True, text=True, env=env, cwd=self.root)

    def test_only_salesforce_mcp_servers_are_guarded(self):
        self.set(100)
        for tool in ("mcp__ccd_turn__update_plan", "mcp__slack__send_message", "mcp__atlassian__createJiraIssue"):
            self.assertEqual(self.hook(tool, {"org": "prod"}).returncode, 0, tool)
        self.assertEqual(self.hook("mcp__salesforce__deploy_metadata", {"usernameOrAlias": "prod"}).returncode, 2)
        self.assertEqual(self.hook("mcp__salesforce__deploy_metadata", {"usernameOrAlias": "dev"}).returncode, 0)
        self.assertEqual(self.hook("mcp__crm__deploy_metadata", {"usernameOrAlias": "prod"}).returncode, 0)
        cfg = yaml.safe_load(self.cfg_p.read_text())
        cfg["orgs"]["mcp_servers"] = ["crm"]
        self.cfg_p.write_text(yaml.safe_dump(cfg))
        self.assertEqual(self.hook("mcp__crm__deploy_metadata", {"usernameOrAlias": "prod"}).returncode, 2,
                         "a Salesforce server listed in orgs.mcp_servers is guarded")


class SetupProjectTest(unittest.TestCase):
    ANSWERS = {"path": "existing-org", "team_profile": "small", "devs": 2, "admins": 1, "approver": "Jane",
               "pm": "Pat", "tech_lead": "Lee", "source_alias": "acme-prod", "source_kind": "production",
               "production": [], "write_allowed": ["acme-dev"], "standard_objects": ["Quote", "Account"],
               "base_branch": "main"}

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "proj"
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def setup(self, answers, *extra):
        f = self.tmp / "a.yaml"
        f.write_text(yaml.safe_dump(answers))
        return sh(PKG, sys.executable, "tools/setup_project.py", str(self.root), "--answers", str(f),
                  "--no-login", "--no-retrieve", *extra)

    def test_fills_config_manifest_and_dx_project_and_reruns_cleanly(self):
        for _ in range(2):
            r = self.setup(self.ANSWERS)
            self.assertIn("Still for humans", r.stdout, r.stderr)
        cfg = yaml.safe_load((self.root / "guardrails.project.yaml").read_text())
        self.assertEqual(cfg["roles"]["approver"], "Jane")
        self.assertEqual(cfg["orgs"]["production"], ["acme-prod"], "production source is listed as production")
        self.assertEqual(cfg["orgs"]["evaluation_readonly"], ["acme-prod"], "existing org is read-only (HG-08)")
        self.assertEqual(cfg["orgs"]["write_allowed"], ["acme-dev"])
        self.assertEqual(cfg["approval"]["status"], "DRAFT", "setup never approves (AI-01)")
        self.assertEqual(cfg["architecture"]["structure_level"], "pending", "decisions stay with humans")
        manifest = (self.root / "manifest/baseline-package.xml").read_text()
        self.assertEqual(manifest.count("<members>Quote</members>"), 1)
        self.assertEqual(manifest.count("<members>Account</members>"), 1)
        self.assertTrue(json.loads((self.root / "sfdx-project.json").read_text())["sourceApiVersion"])
        self.assertTrue((self.root / ".git/hooks/pre-commit").exists())

    def test_production_cannot_be_write_allowed(self):
        r = self.setup({**self.ANSWERS, "write_allowed": ["acme-prod"]})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("HG-09/HG-08", r.stderr)

    def test_terminal_prompts(self):
        typed = "new-org\nsolo\n1\n0\nJane\n\n\ndev1\nsandbox\n\n\ndev1\n\n\n"
        r = subprocess.run([sys.executable, str(PKG / "tools/setup_project.py"), str(self.root), "--no-login",
                            "--no-retrieve"], input=typed, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        cfg = yaml.safe_load((self.root / "guardrails.project.yaml").read_text())
        self.assertEqual(cfg["path"], "new-org")
        self.assertEqual(cfg["orgs"]["write_allowed"], ["dev1"])
        self.assertEqual(cfg["orgs"]["evaluation_readonly"], [], "new org: nothing under evaluation")
