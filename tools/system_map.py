#!/usr/bin/env python3
"""System map: processes, features and automation of the org. See workflow/processes/system-map.md.

usage:
  system_map.py generate [--project DIR]                 automation layer from force-app → docs/wiki/_data/map/map.json + pages
  system_map.py query writes <Object.Field>              what writes a field
  system_map.py query fires <Object> <create|update|delete>   what runs, in order
  system_map.py query used-by <Name>                     components and features that use a component
  system_map.py query tests <FEAT-nn>                    tests that prove a feature
  system_map.py query step <PROC-nn#k>                   features and components behind a process step
  system_map.py query impact <Name>                      references (2 levels) → features → processes → tests
  system_map.py search <words...>                        full-text over written pages, features, tickets (SQLite FTS5)
  system_map.py lint [--changed] [--base BRANCH]         names exist; generated layer current; changed components mapped
  system_map.py questions                                run docs/wiki/_data/map/questions.yaml, report pass rate
Generated files are never edited by hand. Written text lives in docs/wiki/map/processes/*.md and features/*.md.
"""
import datetime as dt
import json
import re
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ticket_lint import parse  # noqa: E402

NS = "{http://soap.sforce.com/2006/04/metadata}"
EVENTS = ("create", "update", "delete")
# Salesforce order of execution, record-triggered automation only [med: simplified; see the
# Apex Developer Guide "Triggers and Order of Execution" for the full list]
PHASES = ["before-save flow", "before trigger", "validation rule", "after trigger", "workflow field update",
          "after-save flow"]
FLOW_EVENTS = {"Create": ["create"], "Update": ["update"], "CreateAndUpdate": ["create", "update"], "Delete": ["delete"]}
TRIGGER_EVENTS = {"insert": "create", "update": "update", "delete": "delete", "undelete": "create"}


def paths(root):
    m = root / "docs/wiki/map"
    return {"src": root / "force-app", "pages": m, "data": root / "docs/wiki/_data/map",
            "features": m / "features", "processes": m / "processes"}


def x(el, tag):
    found = el.find(NS + tag) if el is not None else None
    return found.text if found is not None and found.text else ""


# ---------- generate ----------
def scan(root):
    p = paths(root)
    comps, writers, objects, entry = {}, {}, {}, []
    order = lambda: {e: [] for e in EVENTS}

    def add_writer(field, name, ctype, conf):
        writers.setdefault(field, []).append({"name": name, "type": ctype, "confidence": conf})

    def add_order(obj, event, phase, name, ctype):
        objects.setdefault(obj, order())[event].append({"phase": phase, "type": ctype, "name": name})

    src = p["src"]
    files = sorted(f for f in src.rglob("*") if f.is_file()) if src.exists() else []
    for f in files:
        rel = str(f.relative_to(root))
        if f.name.endswith(".flow-meta.xml"):
            name = f.name.removesuffix(".flow-meta.xml")
            t = ET.parse(f).getroot()
            start = t.find(NS + "start")
            obj, ttype = x(start, "object"), x(start, "triggerType")
            comps[name] = {"type": "flow", "path": rel, "object": obj, "trigger": ttype, "status": x(t, "status")}
            if obj and ttype in ("RecordBeforeSave", "RecordAfterSave", "RecordBeforeDelete"):
                phase = "before-save flow" if ttype != "RecordAfterSave" else "after-save flow"
                events = ["delete"] if ttype == "RecordBeforeDelete" else FLOW_EVENTS.get(x(start, "recordTriggerType"), [])
                for e in events:
                    add_order(obj, e, phase, name, "flow")
            for ru in t.findall(NS + "recordUpdates") + t.findall(NS + "recordCreates"):
                target = x(ru, "object") or (obj if x(ru, "inputReference") == "$Record" else "")
                for ia in ru.findall(NS + "inputAssignments"):
                    add_writer(f"{target or '?'}.{x(ia, 'field')}", name, "flow", "high" if target else "med")
            for asg in t.findall(NS + "assignments"):
                for item in asg.findall(NS + "assignmentItems"):
                    ref = x(item, "assignToReference")
                    if ref.startswith("$Record.") and obj:
                        add_writer(f"{obj}.{ref.split('.', 1)[1]}", name, "flow", "high")
        elif f.suffix == ".trigger":
            m = re.search(r"trigger\s+(\w+)\s+on\s+(\w+)\s*\(([^)]*)\)", f.read_text(errors="ignore"), re.I)
            if m:
                name, obj = m.group(1), m.group(2)
                comps[name] = {"type": "trigger", "path": rel, "object": obj}
                for ev in m.group(3).split(","):
                    when, what = (ev.strip().lower().split() + ["", ""])[:2]
                    if what in TRIGGER_EVENTS:
                        add_order(obj, TRIGGER_EVENTS[what], f"{when} trigger", name, "trigger")
        elif f.name.endswith(".validationRule-meta.xml"):
            name, obj = f.name.removesuffix(".validationRule-meta.xml"), f.parent.parent.name
            active = x(ET.parse(f).getroot(), "active") != "false"
            comps[f"{obj}.{name}"] = {"type": "validationrule", "path": rel, "object": obj, "active": active}
            if active:
                for e in ("create", "update"):
                    add_order(obj, e, "validation rule", f"{obj}.{name}", "validationrule")
        elif f.name.endswith(".workflow-meta.xml"):
            obj = f.name.removesuffix(".workflow-meta.xml")
            for fu in ET.parse(f).getroot().findall(NS + "fieldUpdates"):
                name = f"{obj}.{x(fu, 'fullName')}"
                comps[name] = {"type": "workflowfieldupdate", "path": rel, "object": obj}
                add_writer(f"{obj}.{x(fu, 'field')}", name, "workflowfieldupdate", "high")
                for e in ("create", "update"):
                    add_order(obj, e, "workflow field update", name, "workflowfieldupdate")
        elif f.suffix == ".cls":
            name, text = f.stem, f.read_text(errors="ignore")
            is_test = bool(re.search(r"@isTest", text, re.I))
            comps[name] = {"type": "apexclass", "path": rel, "test": is_test}
            if is_test:
                continue
            for fld in sorted(set(re.findall(r"\b\w+\.(\w+__c)\s*=(?!=)", text))):
                add_writer(f"?.{fld}", name, "apexclass", "med")
            kinds = [k for k, rx in (("aura", r"@AuraEnabled"), ("invocable", r"@InvocableMethod"), ("rest", r"@RestResource"),
                                     ("schedulable", r"implements[^{]*\bSchedulable\b"),
                                     ("batch", r"implements[^{]*\bDatabase\.Batchable\b"),
                                     ("queueable", r"implements[^{]*\bQueueable\b")) if re.search(rx, text, re.I)]
            entry += [{"name": name, "kind": k} for k in kinds]
        elif f.suffix == ".js" and "/lwc/" in rel and f.stem == f.parent.name:
            comps[f.stem] = {"type": "lwc", "path": rel}
            entry.append({"name": f.stem, "kind": "ui"})
    for obj in objects.values():
        for e in EVENTS:
            obj[e].sort(key=lambda r: PHASES.index(r["phase"]))
    return comps, writers, objects, entry


def references(root, comps):
    texts = {n: (root / c["path"]).read_text(errors="ignore") for n, c in comps.items() if "." not in n}
    refs = {}
    for n in texts:
        if len(n) < 4:
            continue
        rx = re.compile(rf"\b{re.escape(n)}\b")
        users = sorted(m for m, t in texts.items() if m != n and rx.search(t))
        if users:
            refs[n] = users
    return refs


def written(root, folder):
    out = {}
    for f in sorted(folder.glob("*.md")) if folder.exists() else []:
        fm, body = parse(f)
        if fm and fm.get("id"):
            out[fm["id"]] = {**fm, "path": str(f.relative_to(root)), "text": body or ""}
    return out


def generated_tests(root, feature):
    tests = []
    for key in feature.get("tickets") or []:
        ag = root / "docs/tests" / str(key) / "agreed.yaml"
        for c in ((yaml.safe_load(ag.read_text()) or {}).get("cases") or []) if ag.exists() else []:
            t = (c.get("automation") or {}).get("test")
            if c.get("status") == "accepted" and t and t != "-":
                tests.append(t)
    return sorted(set(tests))


def build(root):
    comps, writers, objects, entry = scan(root)
    p = paths(root)
    features, processes = written(root, p["features"]), written(root, p["processes"])
    for f in features.values():
        f["tests_generated"] = generated_tests(root, f)
    automation = {"components": comps, "field_writers": writers, "objects": objects, "entry_points": entry,
                  "refs": references(root, comps)}
    return automation, features, processes


def cmd_generate(root):
    automation, features, processes = build(root)
    p = paths(root)
    p["data"].mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
    (p["data"] / "map.json").write_text(json.dumps({"automation": automation, "features": features, "processes": processes},
                                                   indent=1, sort_keys=True, default=str))
    (p["data"] / "generated-at.yaml").write_text(yaml.safe_dump({"commit": commit or "uncommitted", "source": "force-app",
                                                                 "date": dt.date.today().isoformat()}))
    (p["pages"] / "objects").mkdir(parents=True, exist_ok=True)
    for obj, events in sorted(automation["objects"].items()):
        L = [f"# {obj}", "", "Generated by `tools/system_map.py generate` — do not edit.", ""]
        for e in EVENTS:
            L += [f"## On {e}", "", "| # | Phase | Type | Name |", "|---|---|---|---|"]
            L += [f"| {i} | {r['phase']} | {r['type']} | {r['name']} |" for i, r in enumerate(events[e], 1)] or ["| – | – | – | – |"]
            L.append("")
        fw = {k: v for k, v in automation["field_writers"].items() if k.startswith(obj + ".")}
        L += ["## Field writers", "", "| Field | Written by |", "|---|---|"]
        L += [f"| {k} | " + ", ".join(f"{w['type']}:{w['name']} [{w['confidence']}]" for w in v) + " |" for k, v in sorted(fw.items())] or ["| – | – |"]
        (p["pages"] / "objects" / f"{obj}.md").write_text("\n".join(L) + "\n")
    rel = lambda v: Path(v["path"]).relative_to("docs/wiki/map")
    idx = ["# System map", "", "Generated by `tools/system_map.py generate` — do not edit. Written pages: `processes/`, `features/`.", ""]
    for title, rows in (
            ("Processes", [f"- [{k} {v.get('name', '')}]({rel(v)})" for k, v in sorted(processes.items())]),
            ("Features", [f"- [{k}]({rel(v)}) — {v.get('purpose', '')} ({v.get('status', '')})" for k, v in sorted(features.items())]),
            ("Objects with automation", [f"- [{o}](objects/{o}.md)" for o in sorted(automation["objects"])]),
            ("Entry points", [f"- {e['kind']}: {e['name']}" for e in automation["entry_points"]])):
        idx += [f"## {title}", *(rows or ["- none"]), ""]
    (p["pages"] / "index.md").write_text("\n".join(idx))
    print(f"Map: {len(automation['components'])} components, {len(automation['objects'])} objects, "
          f"{len(features)} features, {len(processes)} processes → docs/wiki/_data/map/map.json")


def load(root):
    f = paths(root)["data"] / "map.json"
    if not f.exists():
        sys.exit("map.json missing — run `system_map.py generate`")
    return json.loads(f.read_text())


# ---------- query ----------
def features_using(m, names):
    return sorted(k for k, f in m["features"].items()
                  if any(c.get("name") in names for c in f.get("components") or [] if isinstance(c, dict)))


def feature_tests(f):
    t = f.get("tests") or {}
    return sorted(set((t.get("automated") or []) + (t.get("uat") or []) + (f.get("tests_generated") or [])))


def query(m, kind, args):
    a = m["automation"]
    if kind == "writes":
        field = args[0]
        short = "?." + field.split(".")[-1]
        return [f"{w['type']}:{w['name']} [{w['confidence']}]" for k in (field, short) for w in a["field_writers"].get(k, [])]
    if kind == "fires":
        obj, event = args[0], args[1]
        return [f"{i}. {r['phase']}: {r['type']}:{r['name']}" for i, r in enumerate((a["objects"].get(obj) or {}).get(event, []), 1)]
    if kind == "used-by":
        return [f"component: {u}" for u in a["refs"].get(args[0], [])] + [f"feature: {f}" for f in features_using(m, {args[0]})]
    if kind == "tests":
        return feature_tests(m["features"].get(args[0]) or {})
    if kind == "step":
        pid, n = args[0].split("#")
        proc = m["processes"].get(pid) or {}
        step = next((s for s in proc.get("steps") or [] if str(s.get("n")) == n), {})
        out = []
        for fid in step.get("features") or []:
            comps = [c.get("name") for c in (m["features"].get(fid) or {}).get("components") or [] if isinstance(c, dict)]
            out.append(f"{fid}: {', '.join(comps)}")
        return out
    if kind == "impact":
        level1 = set(a["refs"].get(args[0], []))
        level2 = {u for n in level1 for u in a["refs"].get(n, [])} - level1 - {args[0]}
        feats = features_using(m, {args[0]} | level1 | level2)
        procs = sorted(pid for pid, pr in m["processes"].items()
                       if any(fid in (s.get("features") or []) for s in pr.get("steps") or [] for fid in feats))
        tests = sorted({t for fid in feats for t in feature_tests(m["features"][fid])})
        return ([f"references: {u}" for u in sorted(level1)] + [f"references (2nd level): {u}" for u in sorted(level2)]
                + [f"feature: {f}" for f in feats] + [f"process: {p}" for p in procs] + [f"re-run test: {t}" for t in tests])
    sys.exit(f"unknown query '{kind}'")


def search(root, m, words):
    docs = []
    for k, f in m["features"].items():
        docs.append((k, f"{k} {f.get('purpose', '')} {' '.join(f.get('aliases') or [])} {f.get('text', '')}"))
    for k, pr in m["processes"].items():
        docs.append((k, f"{k} {pr.get('name', '')} {' '.join(s.get('name', '') for s in pr.get('steps') or [])} {pr.get('text', '')}"))
    for f in sorted((root / "docs/tickets").glob("*.md")) if (root / "docs/tickets").exists() else []:
        fm, body = parse(f)
        if fm:
            docs.append((str(fm.get("key", f.stem)), f"{fm.get('title', '')} {fm.get('user_story', '')} {body or ''}"))
    for f in sorted((root / "docs/wiki").glob("*.md")) if (root / "docs/wiki").exists() else []:
        docs.append((str(f.relative_to(root)), f.read_text(errors="ignore")))
    con = sqlite3.connect(":memory:")
    try:
        con.execute("CREATE VIRTUAL TABLE d USING fts5(id, body, tokenize='porter')")
        con.executemany("INSERT INTO d VALUES (?, ?)", docs)
        q = " OR ".join('"' + w.replace('"', "") + '"' for w in words)
        return [r[0] for r in con.execute("SELECT id FROM d WHERE d MATCH ? ORDER BY rank LIMIT 20", (q,))]
    except sqlite3.OperationalError:  # no FTS5 in this Python build → plain substring match
        return [k for k, body in docs if any(w.lower() in body.lower() for w in words)][:20]


# ---------- lint ----------
def changed(root, base):
    r = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD", "--", "force-app"], cwd=root, capture_output=True, text=True)
    w = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", "force-app"], cwd=root, capture_output=True, text=True)
    return sorted(set(r.stdout.split()) | {l[3:] for l in w.stdout.splitlines()})


def lint(root, only_changed=False, base="main"):
    errs = []
    automation, features, processes = build(root)
    comps = automation["components"]
    for fid, f in features.items():
        for c in f.get("components") or []:
            name = c.get("name") if isinstance(c, dict) else c
            if name not in comps and not (isinstance(c, dict) and c.get("state") == "planned"):
                errs.append(f"{fid}: component '{name}' not found in force-app (AI-02)")
        for pref in f.get("processes") or []:
            if str(pref).split("#")[0] not in processes:
                errs.append(f"{fid}: process '{pref}' has no page")
    for pid, pr in processes.items():
        for s in pr.get("steps") or []:
            for fid in s.get("features") or []:
                if fid not in features:
                    errs.append(f"{pid} step {s.get('n')}: feature '{fid}' has no page")
    data = paths(root)["data"] / "map.json"
    if not data.exists():
        errs.append("map.json missing — run `system_map.py generate`")
    elif json.loads(data.read_text()).get("automation") != json.loads(json.dumps(automation, sort_keys=True, default=str)):
        errs.append("generated layer out of date — run `system_map.py generate` and commit")
    if only_changed:
        mapped = {c.get("name") for f in features.values() for c in f.get("components") or [] if isinstance(c, dict)}
        by_path = {c["path"]: n for n, c in comps.items()}
        for path in changed(root, base):
            name = by_path.get(path) or by_path.get(path.removesuffix("-meta.xml"))
            if name and not comps[name].get("test") and name not in mapped:
                errs.append(f"changed component '{name}' is not in any feature (PR-12)")
    return errs


def cmd_questions(root):
    m = load(root)
    qf = paths(root)["data"] / "questions.yaml"
    qs = (yaml.safe_load(qf.read_text()) or {}).get("questions") or [] if qf.exists() else []
    if not qs:
        sys.exit(f"no questions in {qf.relative_to(root)}")
    ok = 0
    for q in qs:
        kind, args = q["query"][0], q["query"][1:]
        got = search(root, m, args) if kind == "search" else query(m, kind, args)
        hit = all(any(e in g for g in got) for e in q.get("expect") or [])
        ok += hit
        print(f"{'✅' if hit else '❌'} {q['q']} → {got[:5]}")
    print(f"Question set: {ok}/{len(qs)} answered ({100 * ok // len(qs)}%)")


def main():
    a = sys.argv[1:]
    root = Path(".").resolve()
    if "--project" in a:
        i = a.index("--project")
        root, a = Path(a[i + 1]).resolve(), a[:i] + a[i + 2:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "generate":
        cmd_generate(root)
    elif a[0] == "query" and len(a) >= 3:
        print("\n".join(query(load(root), a[1], a[2:])) or "no results")
    elif a[0] == "search" and len(a) >= 2:
        print("\n".join(search(root, load(root), a[1:])) or "no results")
    elif a[0] == "lint":
        base = a[a.index("--base") + 1] if "--base" in a else "main"
        errs = lint(root, "--changed" in a, base)
        print("✅ system map lint passed" if not errs else "❌ system map lint\n" + "\n".join(f"- {e}" for e in errs))
        sys.exit(1 if errs else 0)
    elif a[0] == "questions":
        cmd_questions(root)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
