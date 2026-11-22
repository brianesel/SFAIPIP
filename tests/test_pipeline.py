"""End-to-end tests for tools/pipeline.py with a fake agent runner. Run: python3 -m unittest discover tests"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

PKG = Path(__file__).resolve().parents[1]
KEY = "STORY-9"


def sh(cwd, *args, env=None):
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, env=env)


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "proj"
        sh(PKG, sys.executable, "tools/init_project.py", str(self.root))
        cfg_p = self.root / "guardrails.project.yaml"
        cfg = yaml.safe_load(cfg_p.read_text())
        cfg.update(path="new-org", team_profile="solo")
        cfg["roles"]["approver"] = "Approver A"
        cfg["orgs"].update(production=["prod"], write_allowed=["dev"])
        cfg["architecture"] = {k: "lean" if k == "structure_level" else "n/a" for k in cfg["architecture"]}
        cfg["approval"] = {"status": "APPROVED", "approved_by": "Approver A", "date": "2026-11-23"}
        cfg_p.write_text(yaml.safe_dump(cfg, sort_keys=False))
        so = self.root / "docs/design/design-signoff.md"
        text = so.read_text().replace("Status: DRAFT", "Status: APPROVED").replace("Approved-by:", "Approved-by: Approver A")
        text = re.sub(r"^Date:\s*$", "Date: 2026-11-23", text, flags=re.M)
        text = re.sub(r"\| (\w+-\d+) \| \| open \| \| \|", r"| \1 | decided in workshop | decided | [high] | |", text)
        so.write_text(text)
        (self.root / "docs/design/requirements.md").write_text("# Requirements\n\n- REQ-001 Invoice from opportunity\n")
        (self.root / "docs/decisions/ADR-001.md").write_text("# ADR-001\n")
        (self.root / "docs/design/integration-inventory.md").unlink()  # no integrations in this ticket
        self.limits = self.tmp / "limits.json"
        self.set_limits(15000)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text("#!/bin/sh\necho https://github.com/example/repo/pull/1\n")
        gh.chmod(0o755)
        remote = self.tmp / "remote.git"
        sh(self.tmp, "git", "init", "-q", "--bare", str(remote))
        for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@example.com"), ("config", "user.name", "T"),
                     ("add", "-A"), ("commit", "-qm", "init"), ("remote", "add", "origin", str(remote)), ("push", "-q", "origin", "main")):
            sh(self.root, "git", *args)

    def set_limits(self, remaining, max_=15000):
        self.limits.write_text(json.dumps({"dev": {"DailyApiRequests": {"max": max_, "remaining": remaining},
                                                   "DailyAsyncApexExecutions": {"max": 250000, "remaining": 250000}}}))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_pipeline(self, mode="good", *extra):
        env = {**os.environ, "SFG_AGENT_CMD": f"{sys.executable} {PKG / 'tests/fake_agent.py'}", "SFG_FAKE_MODE": mode,
               "PATH": f"{self.bin}:{os.environ['PATH']}", "SFG_ORG_FACTS": "", "SFG_ORG_LIMITS": str(self.limits),
               "SFG_FAKE_COST": str(getattr(self, "cost", 0))}
        return sh(self.root, sys.executable, str(PKG / "tools/pipeline.py"), "run", KEY, "--project", str(self.root), *extra, env=env)

    def d(self):
        return self.root / "docs/tests" / KEY

    def fill_tester_cases(self, uat=False):
        p = self.d() / "tester.yaml"
        doc = yaml.safe_load(p.read_text())
        doc["cases"] = [
            {"id": "T-01", "ac": ["AC-1"], "category": "happy", "title": "creates invoice for closed-won", "given": "an opportunity",
             "when": "the rep clicks Create invoice", "then": "the expected outcome", "level": "unit",
             "automation": {"type": "apex", "test": "InvoiceServiceTest.createsInvoice"}},
            {"id": "T-02", "ac": ["AC-2"], "category": "negative", "title": "rejects open opportunity", "given": "an opportunity",
             "when": "the rep clicks Create invoice", "then": "the expected outcome", "level": "unit",
             "automation": {"type": "apex", "test": "InvoiceServiceTest.rejectsOpen"}}]
        if uat:
            doc["cases"].append({"id": "T-03", "ac": ["AC-1"], "category": "ui", "title": "rep creates invoice in the UI",
                                 "given": "a closed-won opportunity", "when": "the rep clicks Create invoice",
                                 "then": "the invoice page opens", "level": "uat", "automation": {"type": "manual", "test": "-"}})
        p.write_text(yaml.safe_dump(doc))

    def human_accepts_all(self):
        p = self.d() / "agreed.yaml"
        doc = yaml.safe_load(p.read_text())
        for c in doc["cases"]:
            c["status"] = "accepted"
        p.write_text(yaml.safe_dump(doc))

    def to_dev_loop(self, mode="good", uat=False):
        r = self.run_pipeline(mode, "--request", "Rep needs an invoice from a closed-won opportunity")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("tester.yaml", r.stdout)
        self.assertFalse((self.root / ".blind-violation").exists(), "test designer saw tester.yaml (AI-03)")
        self.fill_tester_cases(uat)
        r = self.run_pipeline(mode)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("agreed.yaml", r.stdout)
        self.human_accepts_all()

    def test_happy_path_opens_pr(self):
        self.to_dev_loop()
        r = self.run_pipeline()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PR opened", r.stdout)
        log = sh(self.root, "git", "log", "--format=%s", "feature/" + KEY).stdout
        self.assertIn(f"{KEY} iter-1: 2/2 pass, 0 blocking [PASSING]", log)
        self.assertIn(f"{KEY}: ticket Ready, agreed test set", log)
        remote = sh(self.root, "git", "ls-remote", "origin", "feature/" + KEY).stdout
        self.assertTrue(remote.strip(), "feature branch not pushed")
        self.assertTrue((self.d() / "pr-body.md").exists())
        state = yaml.safe_load((self.d() / "pipeline.yaml").read_text())
        self.assertEqual(state["phase"], "pr_open")
        r = self.run_pipeline()
        self.assertEqual(r.returncode, 0)
        self.assertIn("already open", r.stdout)

    def test_intake_questions_wait_for_answers(self):
        r = self.run_pipeline("questions", "--request", "Invoice from opportunity")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("questions.md", r.stdout)
        r = self.run_pipeline("questions")
        self.assertEqual(r.returncode, 3)
        self.assertIn("answer the open questions", r.stdout)
        q = self.d() / "questions.md"
        q.write_text(q.read_text().replace("  A:\n", "  A: Closed Won\n"))
        r = self.run_pipeline("questions")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("tester.yaml", r.stdout)

    def test_stuck_developer_escalates_and_commits_failures(self):
        self.to_dev_loop("stuck")
        r = self.run_pipeline("stuck")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("stuck", r.stdout)
        esc = (self.d() / "escalation.md").read_text()
        self.assertIn("AI-04", esc)
        log = sh(self.root, "git", "log", "--format=%s", "feature/" + KEY).stdout
        self.assertIn("[FAILING]", log)
        r = self.run_pipeline("stuck")
        self.assertEqual(r.returncode, 3)
        self.assertIn("open escalation", r.stdout)

    def test_loop_guard_stops_after_three_failing_iterations(self):
        self.to_dev_loop("failing")
        r = self.run_pipeline("failing")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("loop_guard", r.stdout)
        state = yaml.safe_load((self.d() / "pipeline.yaml").read_text())
        self.assertEqual(state["iteration"], 3)
        log = sh(self.root, "git", "log", "--format=%s", "feature/" + KEY).stdout
        self.assertEqual(log.count("[FAILING]"), 3)
        esc = self.d() / "escalation.md"
        esc.write_text(esc.read_text().replace("Status: open", "Status: resolved")
                       .replace("Decided-by:\n", "Decided-by: Tech Lead\n").replace("Decision:\n", "Decision: test data fixed\n"))
        r = self.run_pipeline("good")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(list((self.d() / "escalations").glob("*.md")))

    def test_blocking_review_finding_forces_next_iteration(self):
        self.to_dev_loop("review_blocking_once")
        r = self.run_pipeline("review_blocking_once")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        log = sh(self.root, "git", "log", "--format=%s", "feature/" + KEY).stdout
        self.assertIn(f"{KEY} iter-1: 2/2 pass, 1 blocking [FAILING]", log)
        self.assertIn(f"{KEY} iter-2: 2/2 pass, 0 blocking [PASSING]", log)
        self.assertIn("R-01", (self.d() / "feedback.md").read_text())

    def log(self):
        return sh(self.root, "git", "log", "--format=%s", "feature/" + KEY).stdout

    def test_characterization_then_baseline_before_change(self):
        self.to_dev_loop("char")
        r = self.run_pipeline("char")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("characterization.yaml", r.stdout)
        p = self.d() / "characterization.yaml"
        doc = yaml.safe_load(p.read_text())
        doc["cases"][0]["status"] = "accepted"
        p.write_text(yaml.safe_dump(doc))
        r = self.run_pipeline("char")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        log = self.log().splitlines()
        i0 = log.index(f"{KEY} iter-0: characterization tests")
        ib = log.index(f"{KEY}: baseline before change")
        i1 = next(i for i, l in enumerate(log) if l.startswith(f"{KEY} iter-1:"))
        self.assertTrue(i1 < ib < i0, log)  # git log is newest first

    def test_unapproved_impact_goes_back_to_developer_then_loop_guard(self):
        self.to_dev_loop("impact_unapproved")
        r = self.run_pipeline("impact_unapproved")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("loop_guard", r.stdout)
        sys.path.insert(0, str(PKG / "tools"))
        import impact
        iid = impact.item_id("scope", "Unrelated")
        self.assertIn(iid, (self.d() / "escalation.md").read_text())
        self.assertIn(iid, (self.d() / "feedback.md").read_text())
        self.assertEqual(self.log().count("2/2 pass, 0 blocking [FAILING]"), 3)

    def test_approved_impact_lets_pr_open(self):
        self.to_dev_loop("impact")
        sys.path.insert(0, str(PKG / "tools"))
        import impact
        (self.d() / "impact-approvals.yaml").write_text(yaml.safe_dump({"approvals": [
            {"id": impact.item_id("scope", "Unrelated"), "approved_by": "Tech Lead", "date": "2026-11-23", "reason": "shared helper"}]}))
        r = self.run_pipeline("impact")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        body = (self.d() / "pr-body.md").read_text()
        self.assertIn("approved by Tech Lead", body)
        self.assertIn("docs/wiki/map", body)

    def test_uat_cases_run_as_persona(self):
        self.to_dev_loop("good", uat=True)
        r = self.run_pipeline("good")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("agent uat-tester", r.stdout)
        res = yaml.safe_load((self.d() / "results/iter-1.yaml").read_text())["results"]
        uat = [v for v in res.values() if "png" in v.get("evidence", "")]
        self.assertEqual(len(uat), 1)
        self.assertEqual(uat[0]["status"], "pass")

    def test_recording_draft_is_offered(self):
        r = self.run_pipeline("good", "--request", "Invoice")
        (self.d() / "tester.draft.yaml").write_text("cases: []\n")
        r = self.run_pipeline("good")
        self.assertIn("tester.draft.yaml", r.stdout)

    def test_run_budget_stops_and_records_usage(self):
        cfg_p = self.root / "guardrails.project.yaml"
        cfg = yaml.safe_load(cfg_p.read_text())
        cfg["orgs"]["limits"] = {"run_budget": 1000}
        cfg_p.write_text(yaml.safe_dump(cfg, sort_keys=False))
        self.cost = 600
        r = self.run_pipeline("good", "--request", "Invoice from opportunity")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("budget", r.stdout)
        esc = (self.d() / "escalation.md").read_text()
        self.assertIn("1200 org API requests", esc)
        state = yaml.safe_load((self.d() / "pipeline.yaml").read_text())
        self.assertEqual(state["api_usage"]["intake-1-intake"], 600)

    def test_reserve_blocks_before_agent_runs(self):
        self.set_limits(5000)  # 33% left, default reserve 50%
        r = self.run_pipeline("good", "--request", "Invoice from opportunity")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("limits", r.stdout)
        self.assertIn("HG-12", (self.d() / "escalation.md").read_text())
        self.assertFalse((self.root / ".agent-calls").exists(), "an agent ran below the reserve")

    def test_developer_editing_agreed_set_is_reverted_and_escalated(self):
        self.to_dev_loop()
        fake = PKG / "tests/fake_agent.py"
        tamper = self.tmp / "tamper_agent.py"
        tamper.write_text(fake.read_text().replace("PKG = Path(__file__).resolve().parents[1]", f"PKG = Path({str(PKG)!r})").replace(
            'elif agent == "developer":\n',
            'elif agent == "developer":\n    (d / "agreed.yaml").write_text("cases: []\\n")\n'))
        env = {**os.environ, "SFG_AGENT_CMD": f"{sys.executable} {tamper}", "PATH": f"{self.bin}:{os.environ['PATH']}",
               "SFG_ORG_LIMITS": str(self.limits)}
        r = sh(self.root, sys.executable, str(PKG / "tools/pipeline.py"), "run", KEY, "--project", str(self.root), env=env)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("guardrail", r.stdout)
        self.assertIn("accepted", (self.d() / "agreed.yaml").read_text())


if __name__ == "__main__":
    unittest.main()
