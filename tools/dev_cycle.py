#!/usr/bin/env python3
"""Dev + test loop per ticket. See workflow/phases/06-dev.md.

usage:
  dev_cycle.py start <KEY>                      entry check + scaffold docs/tests/<KEY>/
  dev_cycle.py align <KEY> [--check]            compare tester.yaml vs ai.yaml → alignment.md + agreed.yaml draft;
                                                --check validates agreed.yaml
  dev_cycle.py import-apex <KEY> --file F.json  new results/iter-N.yaml from `sf apex run test --result-format json`
  dev_cycle.py report <KEY>                     AC status, failures, review findings, loop guard, appends iterations.md
  dev_cycle.py dod <KEY> [--pre-pr]             Definition of Done (G4); --pre-pr skips the human-only steps
                                                (status done, reviewed_by, pr) so the pipeline can open the PR
Common option: --project DIR (default .)
Exit 1 when the step's check fails.
"""
import datetime as dt
import difflib
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_check import check_signoff  # noqa: E402
from status import g0, g1  # noqa: E402
from ticket_lint import MetaIndex, lint_file, parse  # noqa: E402

PKG = Path(__file__).resolve().parents[1]
TSCHEMA = yaml.safe_load((PKG / "guardrails" / "schemas" / "test-case-schema.yaml").read_text())
RSCHEMA = yaml.safe_load((PKG / "guardrails" / "schemas" / "review-schema.yaml").read_text())
LOOP_GUARD = 3
MATCH_RATIO = 0.5


# ---------- helpers ----------
def load_yaml(p: Path, default=None):
    return yaml.safe_load(p.read_text()) if p.exists() else default


def project_cfg(root):
    return load_yaml(root / "guardrails.project.yaml", {}) or {}


def find_ticket(root, key):
    for f in sorted((root / "docs/tickets").glob("*.md")):
        if f.name.startswith("_"):
            continue  # examples / templates
        fm, _ = parse(f)
        if fm and (fm.get("key") == key or f.stem == key):
            return f, fm
    sys.exit(f"Ticket {key} not found in docs/tickets/")


def ac_ids(fm):
    return [f"AC-{i}" for i in range(1, len(fm.get("acceptance_criteria") or []) + 1)]


def tdir(root, key):
    return root / "docs/tests" / key


def out(lines, fail):
    print("\n".join(lines))
    sys.exit(1 if fail else 0)


def case_text(c):
    return " ".join(str(c.get(k, "")) for k in ("title", "given", "when", "then")).lower()


def required_categories(fm):
    rc = TSCHEMA["required_categories"]
    req = set(rc["always"])
    for m in fm.get("metadata") or []:
        req |= set(rc["when_metadata_type"].get(m.get("type"), []))
    if str(fm.get("access", "none")).strip().lower() != "none":
        req |= set(rc["when_access_not_none"])
    if str(fm.get("migration_items", "none")).strip().lower() != "none":
        req |= set(rc["when_migration_items"])
    return req


def validate_cases(cases, acs, label):
    errs = []
    for c in cases or []:
        cid = c.get("id", "?")
        if not set(c.get("ac") or []) <= set(acs) or not c.get("ac"):
            errs.append(f"{label} {cid}: ac must be a non-empty subset of {acs}")
        if c.get("category") not in TSCHEMA["categories"]:
            errs.append(f"{label} {cid}: category '{c.get('category')}' invalid")
        if c.get("level") not in TSCHEMA["levels"]:
            errs.append(f"{label} {cid}: level '{c.get('level')}' invalid")
        auto = c.get("automation") or {}
        if auto.get("type") not in TSCHEMA["automation_types"]:
            errs.append(f"{label} {cid}: automation.type must be apex|jest|manual")
        elif auto["type"] != "manual" and not auto.get("test"):
            errs.append(f"{label} {cid}: automated case needs automation.test (Class.method)")
        for k in ("given", "when", "then"):
            if not c.get(k):
                errs.append(f"{label} {cid}: {k} missing")
    return errs


# ---------- start ----------
def cmd_start(root, key):
    L, fail = [f"# Dev start: {key}"], False
    cfg = project_cfg(root)
    checks = [("G0", g0(cfg) if cfg else ["guardrails.project.yaml missing"]),
              ("G1", g1(cfg, root) if cfg else ["guardrails.project.yaml missing"]),
              ("G2", check_signoff(root)[1])]
    f, fm = find_ticket(root, key)
    r = lint_file(f, {"root": root, "meta": MetaIndex(root, "force-app", None)}, stage="ready")
    checks.append(("G3 ticket ready", r["fail"] + r["todo_ready"]))
    for name, probs in checks:
        L.append(f"{name}: {'✅' if not probs else '❌'}")
        L += [f"  - {p}" for p in probs]
        fail |= bool(probs)
    for p in ("docs/wiki/pattern-register.md", "docs/design/migration-plan.md"):
        if not (root / p).exists():
            L.append(f"❌ {p} missing")
            fail = True
    if fail:
        L.append("\nNot started. Fix the above first.")
        out(L, True)
    d = tdir(root, key)
    (d / "results").mkdir(parents=True, exist_ok=True)
    acs = ac_ids(fm)
    for name in ("tester.yaml", "ai.yaml"):
        p = d / name
        if not p.exists():
            p.write_text(yaml.safe_dump({"ticket": key, "source": name.split(".")[0], "author": "",
                                         "ac_reference": dict(zip(acs, fm.get("acceptance_criteria") or [])),
                                         "cases": []}, sort_keys=False, allow_unicode=True))
    text = f.read_text()
    if re.search(r"^status:\s*ready\s*$", text, re.M):
        f.write_text(re.sub(r"^status:\s*ready\s*$", "status: in_progress", text, count=1, flags=re.M))
    (root / ".sfg").mkdir(exist_ok=True)
    (root / ".sfg/active-ticket").write_text(key + "\n")
    L += [f"\n✅ Started. Folder: docs/tests/{key}/ · active ticket set · ticket status → in_progress.",
          f"Required test categories: {', '.join(sorted(required_categories(fm)))}",
          "Next: tester fills tester.yaml, AI fills ai.yaml (blind to each other), then `align`."]
    out(L, False)


# ---------- align ----------
def cmd_align(root, key, check_only):
    _, fm = find_ticket(root, key)
    acs, d = ac_ids(fm), tdir(root, key)
    if check_only:
        return align_check(d, fm, acs)
    tester = (load_yaml(d / "tester.yaml", {}) or {}).get("cases") or []
    ai = (load_yaml(d / "ai.yaml", {}) or {}).get("cases") or []
    errs = validate_cases(tester, acs, "tester") + validate_cases(ai, acs, "ai")
    if not tester or not ai:
        errs.append("both tester.yaml and ai.yaml need cases (independent sets)")
    if errs:
        out([f"# Align {key}: input invalid"] + [f"- {e}" for e in errs], True)

    pairs, used_ai = [], set()
    for t in tester:
        best, score = None, 0.0
        for a in ai:
            if a["id"] in used_ai or a["category"] != t["category"] or not set(a["ac"]) & set(t["ac"]):
                continue
            s = difflib.SequenceMatcher(None, case_text(t), case_text(a)).ratio()
            if s > score:
                best, score = a, s
        if best and score >= MATCH_RATIO:
            pairs.append((t, best, score))
            used_ai.add(best["id"])
    matched_t = {t["id"] for t, _, _ in pairs}
    t_only = [t for t in tester if t["id"] not in matched_t]
    a_only = [a for a in ai if a["id"] not in used_ai]

    allc = tester + ai
    ac_gaps = [ac for ac in acs if not any(ac in c["ac"] for c in allc)]
    cat_gaps = sorted(required_categories(fm) - {c["category"] for c in allc})

    L = [f"# Test alignment — {key}", "",
         f"Tester cases: {len(tester)} · AI cases: {len(ai)} · matched: {len(pairs)} · tester-only: {len(t_only)} · AI-only: {len(a_only)}",
         "", "## Found by both (likely solid)", "", "| Tester | AI | AC | Category | Similarity |", "|---|---|---|---|---|"]
    L += [f"| {t['id']} {t['title']} | {a['id']} {a['title']} | {','.join(t['ac'])} | {t['category']} | {s:.2f} |" for t, a, s in pairs] or ["| – | – | – | – | – |"]
    L += ["", "## Tester-only (AI missed — check why: domain knowledge?)", ""]
    L += [f"- {t['id']} [{t['category']}] {t['title']} ({','.join(t['ac'])})" for t in t_only] or ["- none"]
    L += ["", "## AI-only (tester missed — check: real risk or noise?)", ""]
    L += [f"- {a['id']} [{a['category']}] {a['title']} ({','.join(a['ac'])})" for a in a_only] or ["- none"]
    L += ["", "## Gaps", ""]
    L += [f"- ❌ {ac} has no test case: {fm['acceptance_criteria'][int(ac[3:]) - 1]}" for ac in ac_gaps]
    L += [f"- ❌ required category missing: {c}" for c in cat_gaps]
    if not ac_gaps and not cat_gaps:
        L.append("- none")
    L += ["", "Next: tester + dev set every case in agreed.yaml to accepted/rejected (+reason), then `align --check`."]

    agreed, n = [], 1
    for t, a, _ in pairs:
        agreed.append({"id": f"C-{n:02d}", **{k: t[k] for k in ("ac", "category", "title", "given", "when", "then", "level", "automation")},
                       "origin": [t["id"], a["id"]], "status": "proposed", "reason": ""})
        n += 1
    for c in t_only + a_only:
        agreed.append({"id": f"C-{n:02d}", **{k: c[k] for k in ("ac", "category", "title", "given", "when", "then", "level", "automation")},
                       "origin": [c["id"]], "status": "proposed", "reason": ""})
        n += 1
    ag = d / "agreed.yaml"
    if ag.exists():
        L.append("\n⚠ agreed.yaml exists — not overwritten. Draft written to agreed.draft.yaml.")
        ag = d / "agreed.draft.yaml"
    ag.write_text(yaml.safe_dump({"ticket": key, "waived_categories": {}, "cases": agreed},
                                 sort_keys=False, allow_unicode=True))
    (d / "alignment.md").write_text("\n".join(L) + "\n")
    out(L, bool(ac_gaps or cat_gaps))


def align_check(d, fm, acs, quiet=False):
    ag = load_yaml(d / "agreed.yaml")
    errs = []
    if not ag:
        errs.append("agreed.yaml missing (run align first)")
    else:
        cases = ag.get("cases") or []
        errs += validate_cases(cases, acs, "agreed")
        origins = [o for c in cases for o in c.get("origin") or []]
        if not any(o.startswith("T-") for o in origins) or not any(o.startswith("A-") for o in origins):
            errs.append("agreed set must draw on both tester (T-) and AI (A-) cases")
        for c in cases:
            if c.get("status") not in ("accepted", "rejected"):
                errs.append(f"{c.get('id')}: status '{c.get('status')}' — decide accepted/rejected")
            if c.get("status") == "rejected" and not c.get("reason"):
                errs.append(f"{c.get('id')}: rejected without reason")
        acc = [c for c in cases if c.get("status") == "accepted"]
        for ac in acs:
            if not any(ac in c.get("ac", []) for c in acc):
                errs.append(f"{ac}: no accepted case")
        waived = ag.get("waived_categories") or {}
        for cat in sorted(required_categories(fm) - {c["category"] for c in acc}):
            if not waived.get(cat):
                errs.append(f"required category '{cat}' has no accepted case (or waive it with a reason)")
    if quiet:
        return errs
    out([f"# Agreed test set check: {'✅ valid' if not errs else '❌'}"] + [f"- {e}" for e in errs], bool(errs))


# ---------- results ----------
def iterations(d):
    files = sorted((d / "results").glob("iter-*.yaml"), key=lambda p: int(re.findall(r"\d+", p.stem)[0]))
    return [(f, load_yaml(f, {})) for f in files]


def cmd_import_apex(root, key, file):
    d = tdir(root, key)
    ag = load_yaml(d / "agreed.yaml") or sys.exit("agreed.yaml missing")
    data = json.loads(Path(file).read_text())
    res = data.get("result", data)
    outcomes = {}
    for t in res.get("tests", []):
        name = t.get("FullName") or f"{(t.get('ApexClass') or {}).get('Name', '')}.{t.get('MethodName', '')}"
        outcomes[name] = (t.get("Outcome"), t.get("Message") or "")
    cov = {}
    for c in (res.get("coverage") or {}).get("coverage", []) or []:
        if c.get("name") is not None:
            cov[c["name"]] = c.get("coveredPercent")
    its = iterations(d)
    n = len(its) + 1
    prev = its[-1][1].get("results", {}) if its else {}
    results = {}
    for c in ag.get("cases", []):
        if c.get("status") != "accepted":
            continue
        auto = c.get("automation") or {}
        if auto.get("type") == "apex":
            o = outcomes.get(auto.get("test"))
            if o is None:
                results[c["id"]] = {"status": "blocked", "evidence": file, "note": f"test {auto.get('test')} not in run"}
            else:
                results[c["id"]] = {"status": "pass" if o[0] == "Pass" else "fail", "evidence": file, "note": o[1][:200]}
        else:
            results[c["id"]] = prev.get(c["id"]) or {"status": "blocked", "evidence": "", "note": "manual/jest: fill in"}
    doc = {"iteration": n, "date": dt.date.today().isoformat(), "build": "", "results": results, "coverage": cov}
    p = d / "results" / f"iter-{n}.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    print(f"Wrote {p.relative_to(root)}: {sum(r['status'] == 'pass' for r in results.values())}/{len(results)} pass. "
          f"Fill manual/jest cases, set build, then `report`.")


# ---------- review ----------
def latest_review(d):
    files = sorted((d / "review").glob("iter-*.yaml"), key=lambda p: int(re.findall(r"\d+", p.stem)[0]))
    return (files[-1], load_yaml(files[-1], {}) or {}) if files else (None, None)


def validate_review(doc):
    errs = []
    if not isinstance(doc, dict):
        return ["review file is not a mapping"]
    for f in doc.get("findings") or []:
        fid = f.get("id", "?")
        for k in ("rule", "file", "severity", "evidence", "fix", "status"):
            if f.get(k) in (None, ""):
                errs.append(f"review {fid}: {k} missing")
        if f.get("severity") not in RSCHEMA["severities"]:
            errs.append(f"review {fid}: severity '{f.get('severity')}' invalid")
        if f.get("status") not in RSCHEMA["statuses"]:
            errs.append(f"review {fid}: status '{f.get('status')}' invalid")
        if f.get("status") == "disputed" and not f.get("dispute"):
            errs.append(f"review {fid}: disputed without a reason in 'dispute'")
    return errs


def open_blocking(doc):
    return [f for f in (doc or {}).get("findings") or []
            if f.get("severity") == "blocking" and f.get("status") in ("open", "disputed")]


def ac_status(fm, ag, latest):
    acc = [c for c in ag.get("cases", []) if c.get("status") == "accepted"]
    res = (latest or {}).get("results", {})
    rows = []
    for i, ac in enumerate(ac_ids(fm)):
        cs = [c for c in acc if ac in c["ac"]]
        st = [res.get(c["id"], {}).get("status", "not run") for c in cs]
        rows.append((ac, fm["acceptance_criteria"][i], cs, st, bool(cs) and all(s == "pass" for s in st)))
    return rows


def cmd_report(root, key):
    _, fm = find_ticket(root, key)
    d = tdir(root, key)
    ag = load_yaml(d / "agreed.yaml") or sys.exit("agreed.yaml missing")
    its = iterations(d)
    if not its:
        sys.exit("No results yet (import-apex or write results/iter-1.yaml)")
    f, latest = its[-1]
    rows = ac_status(fm, ag, latest)
    rf, review = latest_review(d)
    blocking = open_blocking(review)
    done = all(r[4] for r in rows) and not blocking
    L = [f"# Iteration {latest.get('iteration')} — {key} ({latest.get('date')})", "",
         f"**Verdict: {'✅ all acceptance criteria pass → run `dod`' if done else '❌ not yet — next iteration'}**", "",
         "| AC | Achieved | Cases |", "|---|---|---|"]
    for ac, text, cs, st, ok in rows:
        L.append(f"| {ac} | {'✅' if ok else '❌'} | " + ", ".join(f"{c['id']}:{s}" for c, s in zip(cs, st)) + " |")
    fails = [(cid, r) for cid, r in latest.get("results", {}).items() if r.get("status") != "pass"]
    if fails:
        L += ["", "## Feedback for next iteration", "Classify each: code defect → implement · test wrong → tester+dev agree · AC wrong → change request · env/data → fix setup", ""]
        for cid, r in fails:
            streak = 0
            for _, it in reversed(its):
                if it.get("results", {}).get(cid, {}).get("status") in ("fail", "blocked"):
                    streak += 1
                else:
                    break
            guard = f" ⛔ failing {streak} iterations in a row → escalate (tech lead + PM)" if streak >= LOOP_GUARD else ""
            L.append(f"- {cid} {r.get('status')}: {r.get('note', '')} [evidence: {r.get('evidence', '')}]{guard}")
    if review is not None:
        L += ["", f"## Tech-lead review ({rf.name})", ""]
        L += [f"- ❌ {e}" for e in validate_review(review)]
        findings = review.get("findings") or []
        L += [f"- {f.get('id')} [{f.get('severity')}/{f.get('status')}] {f.get('rule')} {f.get('file')}:{f.get('line', 0)} — {f.get('fix')}"
              for f in findings] or ["- no findings"]
        if blocking:
            L.append(f"\n{len(blocking)} blocking finding(s) open or disputed → not done")
    log = d / "iterations.md"
    if not log.exists():
        log.write_text("| Iter | Date | Build | Pass | Fail/blocked | AC achieved |\n|---|---|---|---|---|---|\n")
    for _, it in its:  # log every iteration not logged yet
        if any(line.startswith(f"| {it.get('iteration')} |") for line in log.read_text().splitlines()):
            continue
        res_it = it.get("results", {})
        r_rows = ac_status(fm, ag, it)
        log.write_text(log.read_text() + (
            f"| {it.get('iteration')} | {it.get('date')} | {it.get('build', '')} | "
            f"{sum(r.get('status') == 'pass' for r in res_it.values())} | "
            f"{sum(r.get('status') != 'pass' for r in res_it.values())} | {sum(r[4] for r in r_rows)}/{len(r_rows)} |\n"))
    out(L, not done)


# ---------- dod ----------
def cmd_dod(root, key, pre_pr=False):
    tf, fm = find_ticket(root, key)
    d = tdir(root, key)
    cfg = project_cfg(root)
    cov_min = ((cfg.get("dev") or {}).get("class_coverage_min")) or 85
    checks = []
    acs = ac_ids(fm)
    errs = align_check(d, fm, acs, quiet=True)
    checks.append(("Agreed test set valid", errs))
    ag = load_yaml(d / "agreed.yaml", {}) or {}
    its = iterations(d)
    latest = its[-1][1] if its else None
    if not latest:
        checks.append(("All acceptance criteria pass", ["no test results"]))
    else:
        rows = ac_status(fm, ag, latest)
        checks.append(("All acceptance criteria pass", [f"{ac} not achieved" for ac, _, _, _, ok in rows if not ok]))
    missing = []
    src = root / "force-app"
    for c in ag.get("cases", []):
        auto = c.get("automation") or {}
        if c.get("status") == "accepted" and auto.get("type") == "apex" and "." in str(auto.get("test")):
            cls, meth = auto["test"].split(".", 1)
            files = list(src.rglob(f"{cls}.cls")) if src.exists() else []
            if not files or not re.search(rf"\b{re.escape(meth)}\s*\(", files[0].read_text()):
                missing.append(f"{auto['test']} not found in source")
    checks.append(("Automated tests exist in source", missing))
    cov_errs = []
    cov = (latest or {}).get("coverage") or {}
    for m in fm.get("metadata") or []:
        if m.get("type") == "class" and not m["name"].endswith("Test"):
            v = cov.get(m["name"])
            if v is None:
                cov_errs.append(f"{m['name']}: no coverage data (import-apex with --code-coverage)")
            elif v < cov_min:
                cov_errs.append(f"{m['name']}: {v}% < {cov_min}%")
    checks.append((f"Class coverage ≥ {cov_min}%", cov_errs))
    ca = d / "code-analyzer.json"
    if not ca.exists():
        checks.append(("Code Analyzer: 0 sev 1–2", ["code-analyzer.json missing (run analyzer on changed files)"]))
    else:
        data = json.loads(ca.read_text())
        viol = data.get("violations", data if isinstance(data, list) else [])
        high = [v for v in viol if int(v.get("severity", 5)) <= 2]
        checks.append(("Code Analyzer: 0 sev 1–2", [f"{len(high)} sev 1–2 findings"] if high else []))
    _, review = latest_review(d)
    checks.append(("No open blocking review findings", validate_review(review) + [
        f"{f.get('id')} {f.get('rule')} {f.get('file')}" for f in open_blocking(review)] if review is not None
        else ["no tech-lead review (review/iter-N.yaml)"]))
    r = lint_file(tf, {"root": root, "meta": MetaIndex(root, "force-app", None)}, stage="ready")
    lint_errs = r["fail"] + r["todo_ready"]
    if fm.get("status") != "done" and not pre_pr:
        lint_errs.append("set status: done (+ reviewed_by, pr) once the PR is reviewed")
    checks.append(("Ticket lint (done)", lint_errs))
    tr = root / "docs/delivery/traceability.md"
    checks.append(("Traceability updated", [] if tr.exists() and key in tr.read_text() else [f"{key} not in traceability.md"]))
    fail = any(p for _, p in checks)
    title = "Pre-PR Done check" if pre_pr else "Definition of Done (G4)"
    L = [f"# {title} — {key}: {'✅ ' + ('ready for PR' if pre_pr else 'DONE') if not fail else '❌ not done'}", ""]
    for name, probs in checks:
        L.append(f"{'✅' if not probs else '❌'} {name}")
        L += [f"   - {p}" for p in probs]
    out(L, fail)


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    cmd, key = a[0], a[1]
    root = Path(a[a.index("--project") + 1] if "--project" in a else ".").resolve()
    if cmd == "start":
        cmd_start(root, key)
    elif cmd == "align":
        cmd_align(root, key, "--check" in a)
    elif cmd == "import-apex":
        cmd_import_apex(root, key, a[a.index("--file") + 1])
    elif cmd == "report":
        cmd_report(root, key)
    elif cmd == "dod":
        cmd_dod(root, key, "--pre-pr" in a)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
