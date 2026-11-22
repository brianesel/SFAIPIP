#!/usr/bin/env python3
"""Impact detection: what changed outside the ticket. See workflow/processes/automated-pipeline.md §9.

usage:
  impact.py baseline <KEY> --file RUN.json [--snapshot SNAP.json]   before any production change → baseline.yaml
  impact.py compare  <KEY> --file RUN.json --iter N [--snapshot SNAP.json] [--base BRANCH]   → impact/iter-N.yaml
  impact.py check    <KEY>                                            exit 1 if the latest impact file has unapproved items
Common option: --project DIR (default .)

RUN.json: `sf apex run test --test-level RunLocalTests --result-format json` output.
SNAP.json: {"<Object>.<RecordId>": {"<Field>": value}} — records touched by the regression scenarios.
Layers: behaviour (an existing test changed outcome or disappeared) · data (a field changed outside the ticket's
fields) · scope (a component changed that is not in the ticket's metadata). Each item is in_scope, approved
(docs/tests/<KEY>/impact-approvals.yaml, written by a human only, AI-01) or unapproved (blocks).
"""
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dev_cycle  # noqa: E402


def outcomes(file):
    data = json.loads(Path(file).read_text())
    res = data.get("result", data)
    out = {}
    for t in res.get("tests", []):
        name = t.get("FullName") or f"{(t.get('ApexClass') or {}).get('Name', '')}.{t.get('MethodName', '')}"
        out[name] = t.get("Outcome")
    return out


def snapshot(file):
    return json.loads(Path(file).read_text()) if file else {}


def item_id(layer, item):
    return "I-" + hashlib.sha1(f"{layer}|{item}".encode()).hexdigest()[:8]


def ticket_scope(root, key):
    _, fm = dev_cycle.find_ticket(root, key)
    names = {m["name"] for m in fm.get("metadata") or [] if m.get("name")}
    fields = {n for n in names if "." in n}
    d = dev_cycle.tdir(root, key)
    tests = set()
    for f in ("agreed.yaml", "characterization.yaml"):
        for c in (dev_cycle.load_yaml(d / f, {}) or {}).get("cases") or []:
            if c.get("status") == "accepted" and "." in str((c.get("automation") or {}).get("test")):
                tests.add(c["automation"]["test"])
    return names, fields, tests


def approvals(d):
    return dev_cycle.impact_approvals(d)


def component(path):
    name = Path(path).name
    for suffix in ("-meta.xml",):
        name = name.removesuffix(suffix)
    return name.split(".")[0]


def changed_components(root, base):
    r = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD", "--", "force-app"], cwd=root, capture_output=True, text=True)
    w = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", "force-app"], cwd=root, capture_output=True, text=True)
    files = set(r.stdout.split()) | {l[3:] for l in w.stdout.splitlines()}
    return sorted({component(f) for f in files if f})


def cmd_baseline(root, key, run, snap):
    d = dev_cycle.tdir(root, key)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
    doc = {"date": dt.date.today().isoformat(), "commit": commit, "tests": outcomes(run), "snapshot": snapshot(snap)}
    (d / "baseline.yaml").write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    print(f"Baseline: {len(doc['tests'])} tests, {len(doc['snapshot'])} records → docs/tests/{key}/baseline.yaml")


def cmd_compare(root, key, run, snap, n, base):
    d = dev_cycle.tdir(root, key)
    bl = dev_cycle.load_yaml(d / "baseline.yaml") or sys.exit("baseline.yaml missing — run `impact.py baseline` first")
    names, fields, tests = ticket_scope(root, key)
    shorts = {x.split(".")[-1] for x in names} | {t.split(".")[0] for t in tests}
    ok = approvals(d)
    now, items = outcomes(run), []

    def add(layer, item, before, after, in_scope, why):
        iid = item_id(layer, item)
        cls = "in_scope" if in_scope else "approved" if iid in ok else "unapproved"
        reason = why if in_scope else (ok[iid]["reason"] if iid in ok else "not explained by the ticket")
        items.append({"id": iid, "layer": layer, "item": item, "before": before, "after": after, "class": cls, "reason": reason})

    for t, before in sorted((bl.get("tests") or {}).items()):
        after = now.get(t, "missing")
        if after != before:
            add("behaviour", t, before, after, t in tests, "test is in the agreed or characterization set")
    snap_now = snapshot(snap)
    for rec, vals in sorted((bl.get("snapshot") or {}).items()):
        obj = rec.split(".")[0]
        for field, before in sorted(vals.items()):
            after = (snap_now.get(rec) or {}).get(field)
            if after != before:
                add("data", f"{rec}.{field}", before, after, f"{obj}.{field}" in fields, "field is in the ticket's metadata")
    for comp in changed_components(root, base):
        if comp not in shorts:
            add("scope", comp, "unchanged", "changed", False, "")
    doc = {"iteration": n, "date": dt.date.today().isoformat(), "impacts": items,
           "unapproved": sum(i["class"] == "unapproved" for i in items)}
    (d / "impact").mkdir(exist_ok=True)
    (d / "impact" / f"iter-{n}.yaml").write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    print(f"Impact iteration {n}: {len(items)} item(s), {doc['unapproved']} unapproved")
    for i in items:
        print(f"- {i['id']} [{i['class']}] {i['layer']}: {i['item']} {i['before']} → {i['after']}")


def cmd_check(root, key):
    left = dev_cycle.unapproved_impacts(dev_cycle.tdir(root, key))
    if left is None:
        sys.exit("no impact report yet")
    print(f"Unapproved impacts: {len(left)}")
    for i in left:
        print(f"- {i['id']} {i['layer']}: {i['item']} {i['before']} → {i['after']}")
    sys.exit(1 if left else 0)


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    opt = lambda flag: a[a.index(flag) + 1] if flag in a else None
    root = Path(opt("--project") or ".").resolve()
    cmd, key = a[0], a[1]
    if cmd == "baseline":
        cmd_baseline(root, key, opt("--file"), opt("--snapshot"))
    elif cmd == "compare":
        cmd_compare(root, key, opt("--file"), opt("--snapshot"), int(opt("--iter")), opt("--base") or "main")
    elif cmd == "check":
        cmd_check(root, key)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
