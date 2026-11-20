#!/usr/bin/env python3
"""Workflow status: which gates pass, what blocks the next phase.

usage: status.py [--project PATH]
G0  guardrails.project.yaml: baseline, path, team profile, approver named
G1  project guardrails approved; no override on a gate check; waivers complete and not expired
G2  design sign-off approved (same check as gate_check.py)
G3  per ticket in the tracker (Definition of Ready), not checked here
"""
import datetime as dt
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_check import check_signoff  # noqa: E402

RUBRIC = Path(__file__).resolve().parent.parent / "guardrails" / "rubric"


def gate_ids():
    ids = set()
    for f in RUBRIC.glob("*.yaml"):
        if f.name == "pillars.yaml":
            continue
        for c in yaml.safe_load(f.read_text())["checks"]:
            if c["type"] == "gate":
                ids.add(c["id"])
    return ids


def g0(cfg):
    p = []
    if not str(cfg.get("baseline", "")).startswith("sf-ai-dev-pipeline@"):
        p.append("baseline not pinned (sf-ai-dev-pipeline@<version>)")
    if cfg.get("path") not in ("existing-org", "new-org"):
        p.append("path not set (existing-org | new-org)")
    if cfg.get("team_profile") not in ("solo", "small", "multi-team"):
        p.append("team_profile not set (solo | small | multi-team)")
    if not (cfg.get("roles") or {}).get("approver"):
        p.append("approver not named")
    orgs = cfg.get("orgs") or {}
    if not orgs.get("production"):
        p.append("orgs.production not set (prod guard needs the production alias)")
    return p


def g1(cfg, root):
    p = []
    gates = gate_ids()
    today = dt.date.today()
    for o in cfg.get("overrides") or []:
        if o.get("check") in gates:
            p.append(f"override on hard gate not allowed: {o['check']} (use a scoped waiver)")
        for k in ("reason", "owner", "review"):
            if not o.get(k):
                p.append(f"override {o.get('check')}: missing {k}")
    for w in cfg.get("waivers") or []:
        for k in ("scope", "exit", "owner", "expires"):
            if not w.get(k):
                p.append(f"waiver {w.get('check')}: missing {k}")
        exp = w.get("expires")
        if exp and dt.date.fromisoformat(str(exp)) < today:
            p.append(f"waiver {w.get('check')} expired {exp} → counts as failed gate")
    for f in ("docs/design/migration-plan.md", "docs/wiki/pattern-register.md"):
        if not (root / f).exists():
            p.append(f"{f} missing")
    for k, v in (cfg.get("architecture") or {}).items():
        if str(v).strip().lower() in ("pending", "", "none"):
            p.append(f"architecture.{k} pending → a named human chooses on the decision card (PR-15)")
    ap = cfg.get("approval") or {}
    if str(ap.get("status", "")).upper() != "APPROVED" or not ap.get("approved_by") or not ap.get("date"):
        p.append("project guardrails not approved (approval.status/approved_by/date)")
    return p


def main():
    args = sys.argv[1:]
    root = Path(args[args.index("--project") + 1] if "--project" in args else ".").resolve()
    f = root / "guardrails.project.yaml"
    if not f.exists():
        print("G0 ❌ guardrails.project.yaml missing → run init_project.py, then phases/intake.md")
        sys.exit(1)
    cfg = yaml.safe_load(f.read_text()) or {}
    results = [("G0 intake", g0(cfg)), ("G1 project guardrails", g1(cfg, root))]
    ok2, p2 = check_signoff(root)
    results.append(("G2 design sign-off", p2))
    blocked = False
    for name, probs in results:
        if blocked:
            print(f"{name}: ⏸ waiting for previous gate")
            continue
        if probs:
            print(f"{name}: ❌")
            for x in probs:
                print(f"  - {x}")
            blocked = True
        else:
            print(f"{name}: ✅")
    print("G3 ready per ticket: run tools/ticket_lint.py · G4 per ticket: tools/dev_cycle.py dod <KEY>")
    sys.exit(1 if blocked else 0)


if __name__ == "__main__":
    main()
