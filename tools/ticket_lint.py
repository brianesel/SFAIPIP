#!/usr/bin/env python3
"""Lint tickets (markdown + YAML front matter) against guardrails/schemas/ticket-schema.yaml.

usage: ticket_lint.py [PATHS...] [--project DIR] [--stage auto|create|ready]
                      [--source force-app] [--org ALIAS] [--quiet]
  PATHS default: <project>/docs/tickets
  --stage auto (default): create checks always; ready checks are enforced when status is
          ready/in_progress/done, otherwise listed as "to reach Ready".
  --org: verify standard objects/fields with `sf sobject describe` (read-only).
Exit 1 if any ticket fails its enforced checks. G3 = ready stage passes.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

PKG = Path(__file__).resolve().parents[1]
SCHEMA = yaml.safe_load((PKG / "guardrails" / "schemas" / "ticket-schema.yaml").read_text())
EMPTY = (None, "", [], {}, "TBD", "tbd", "?")
READY_STATUSES = {"ready", "in_progress", "done"}
PILLARS = ["trust", "reliability", "opex", "cost", "fairness"]
META_TYPES = ["object", "field", "class", "trigger", "flow", "lwc", "permissionset", "other"]


def parse(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None, text
    _, fm, body = text.split("---", 2)
    return yaml.safe_load(fm) or {}, body


def fields_for(ttype):
    out = []
    for f in SCHEMA["common"] + SCHEMA["by_type"].get(ttype, []):
        if "types" in f and ttype not in f["types"]:
            continue
        out.append(f)
    return out


# ---------- metadata existence ----------
class MetaIndex:
    def __init__(self, root: Path, source: str, org: str | None):
        self.src = root / source
        self.org = org
        self._describe = {}

    def _glob(self, pattern):
        return self.src.exists() and any(self.src.rglob(pattern))

    def in_source(self, mtype, name):
        if mtype == "object":
            return self._glob(f"objects/{name}/{name}.object-meta.xml") or self._glob(f"objects/{name}")
        if mtype == "field":
            if "." not in name:
                return False
            obj, fld = name.split(".", 1)
            return self._glob(f"objects/{obj}/fields/{fld}.field-meta.xml")
        pat = {"class": f"classes/{name}.cls", "trigger": f"triggers/{name}.trigger",
               "flow": f"flows/{name}.flow-meta.xml", "lwc": f"lwc/{name}",
               "permissionset": f"permissionsets/{name}.permissionset-meta.xml"}.get(mtype)
        return bool(pat) and self._glob(pat)

    def in_org(self, mtype, name):
        """True/False from org describe, None if not checkable."""
        if not self.org or mtype not in ("object", "field"):
            return None
        obj = name.split(".", 1)[0]
        if obj not in self._describe:
            try:
                r = subprocess.run(["sf", "sobject", "describe", "--sobject", obj, "--target-org", self.org, "--json"],
                                   capture_output=True, text=True, timeout=120)
                data = json.loads(r.stdout or "{}")
                res = data.get("result") or {}
                self._describe[obj] = {f["name"] for f in res.get("fields", [])} if res else None
            except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
                self._describe[obj] = "error"
        d = self._describe[obj]
        if d == "error":
            return None
        if d is None:
            return False
        return True if mtype == "object" else name.split(".", 1)[1] in d


# ---------- checks ----------
def is_empty(v):
    return v in EMPTY or (isinstance(v, str) and not v.strip())


def check_value(f, v, ctx):
    k = f["kind"]
    name = f["field"]
    errs = []
    if k == "enum":
        allowed = SCHEMA["enums"][name]
        if v not in allowed:
            errs.append(f"{name}: '{v}' not in {allowed}")
    elif k == "title":
        if len(str(v)) > SCHEMA["limits"]["title_max"]:
            errs.append(f"title > {SCHEMA['limits']['title_max']} chars")
        if not re.match(r"^\[[^\]]+\]\s+\S", str(v)):
            errs.append("title must be '[Area] outcome'")
    elif k == "list":
        if not isinstance(v, list):
            errs.append(f"{name}: must be a list")
    elif k == "number":
        if not isinstance(v, (int, float)):
            errs.append(f"{name}: must be a number")
    elif k == "bool":
        if not isinstance(v, bool):
            errs.append(f"{name}: must be true/false")
    elif k == "ac":
        if not isinstance(v, list) or not v:
            errs.append("acceptance_criteria: must be a non-empty list")
        else:
            for i, ac in enumerate(v, 1):
                low = str(ac).lower()
                if not all(w in low for w in ("given", "when", "then")):
                    errs.append(f"acceptance_criteria #{i}: needs Given/When/Then")
            if not any("(negative)" in str(ac).lower() for ac in v):
                errs.append("acceptance_criteria: needs ≥1 negative case tagged '(negative)'")
    elif k == "pillars":
        if not isinstance(v, dict) or set(v) != set(PILLARS):
            errs.append(f"pillar_impact: needs exactly {PILLARS}")
        else:
            for p, e in v.items():
                if str(e) not in SCHEMA["enums"]["pillar_effect"]:
                    errs.append(f"pillar_impact.{p}: '{e}' not in + 0 -")
    elif k == "estimate":
        if isinstance(v, (int, float)):
            if v > SCHEMA["limits"]["max_points"]:
                errs.append(f"estimate {v} > {SCHEMA['limits']['max_points']} points → split")
        elif v not in SCHEMA["enums"]["estimate"]:
            errs.append(f"estimate '{v}' not in S/M/L (XL → split)")
    elif k == "pattern":
        if not isinstance(v, dict) or v.get("follows") not in ("current", "target") \
                or not re.match(r"^ADR-\d+", str(v.get("adr", ""))):
            errs.append("pattern: needs {follows: current|target, adr: ADR-nnn}")
        elif ctx["root"]:
            adr = str(v["adr"]).split()[0]
            if not list((ctx["root"] / "docs/decisions").glob(f"{adr}*.md")):
                errs.append(f"pattern: {adr} not found in docs/decisions/")
    elif k == "metadata":
        if not isinstance(v, list) or not v:
            errs.append("metadata: list of {type, name, state}")
        else:
            for m in v:
                errs += check_meta(m, ctx)
    return errs


def check_meta(m, ctx):
    if not isinstance(m, dict) or not m.get("name") or m.get("type") not in META_TYPES \
            or m.get("state") not in SCHEMA["enums"]["metadata_state"]:
        return [f"metadata entry {m}: needs type ({'/'.join(META_TYPES)}), name, state (existing/new)"]
    idx, t, n, s = ctx["meta"], m["type"], m["name"], m["state"]
    if t == "other":
        ctx["warn"].append(f"metadata {n}: type 'other' not verified")
        return []
    found = idx.in_source(t, n)
    if not found:
        org = idx.in_org(t, n)
        found = bool(org) if org is not None else None
    if s == "existing" and found is False:
        return [f"metadata {t} {n}: marked existing but not found in source/org (typo, invented, or not retrieved)"]
    if s == "existing" and found is None:
        custom = "__" in n or t in ("class", "trigger", "flow", "lwc", "permissionset")
        if custom:
            return [f"metadata {t} {n}: marked existing but not in source (retrieve it, or check the name)"]
        ctx["warn"].append(f"metadata {n}: standard name not verified (pass --org to check)")
    if s == "new" and found and ctx.get("status") not in ("in_progress", "done"):
        return [f"metadata {t} {n}: marked new but already exists"]
    return []


def check_links(fm, ctx):
    errs = []
    root = ctx["root"]
    req_file = root / "docs/design/requirements.md"
    mig_file = root / "docs/design/migration-plan.md"
    reqs = fm.get("req") or []
    if reqs and req_file.exists():
        text = req_file.read_text()
        cr_dir = root / "docs/delivery"
        for r in reqs:
            r = str(r)
            if r.startswith("REQ-") and not re.search(rf"\b{re.escape(r)}\b", text):
                errs.append(f"req: {r} not in requirements.md")
            if r.startswith("CR-") and not list(cr_dir.glob(f"{r}*")) and not list((root / "docs/tickets").glob(f"{r}*")):
                errs.append(f"req: {r} has no CR file")
    mig = fm.get("migration_items")
    if mig not in EMPTY and str(mig).lower() != "none" and mig_file.exists():
        text = mig_file.read_text()
        for m in re.findall(r"M-\d+", str(mig)):
            if not re.search(rf"\b{m}\b", text):
                errs.append(f"migration_items: {m} not in migration-plan.md")
    return errs


def cr_expected(fm):
    pct = fm.get("scope_pct") or 0
    eff = fm.get("effort_days") or 0
    if fm.get("guardrail_change") or fm.get("new_process") or pct > 10:
        return "large", "approver"
    if fm.get("design_change") or eff > 1:
        return "medium", "change_board"
    return "small", "pm_tl"


def lint_file(path: Path, ctx, stage="auto"):
    fm, body = parse(path)
    res = {"file": str(path), "key": path.stem, "fail": [], "todo_ready": [], "warn": []}
    ctx["warn"] = res["warn"]
    if fm is None:
        res["fail"].append("no YAML front matter")
        return res
    res["key"] = fm.get("key", path.stem)
    res["status"] = fm.get("status", "draft")
    res["type"] = fm.get("type")
    ctx["status"] = res["status"]
    if res["type"] not in SCHEMA["enums"]["type"]:
        res["fail"].append(f"type '{res['type']}' not in {SCHEMA['enums']['type']}")
        return res
    if res["status"] not in SCHEMA["statuses"]:
        res["fail"].append(f"status '{res['status']}' not in {SCHEMA['statuses']}")
    enforce_ready = stage == "ready" or (stage == "auto" and res["status"] in READY_STATUSES)
    for f in fields_for(res["type"]):
        v = fm.get(f["field"])
        if f["required_at"] == "done" and res["status"] != "done":
            continue
        target = res["fail"] if f["required_at"] in ("create", "done") or enforce_ready else res["todo_ready"]
        if is_empty(v):
            target.append(f"{f['field']}: missing")
            continue
        if str(v).lower() == "none" and f["kind"] == "text":
            continue
        for e in check_value(f, v, ctx):
            target.append(e)
    if ctx["root"]:
        res["fail"] += check_links(fm, ctx)
    if res["type"] == "cr" and fm.get("cr_size") and fm.get("cr_decider"):
        size, decider = cr_expected(fm)
        if (fm["cr_size"], fm["cr_decider"]) != (size, decider):
            res["fail"].append(f"cr routing: rule says {size} → {decider}, ticket says {fm['cr_size']} → {fm['cr_decider']}")
    for i in range(1, 6):
        if not re.search(rf"^##\s*{i}\.", body, re.M):
            res["warn"].append(f"body section '## {i}.' missing")
    res["ready"] = not res["fail"] and not res["todo_ready"]
    return res


def main():
    a = sys.argv[1:]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    root = Path(opt("--project", ".")).resolve()
    stage = opt("--stage", "auto")
    paths = [Path(p) for p in a if not p.startswith("--") and p not in
             {opt("--project"), opt("--stage"), opt("--source"), opt("--org")}]
    if not paths:
        paths = [root / "docs/tickets"]
    files = []
    for p in paths:
        files += sorted(p.glob("*.md")) if p.is_dir() else [p]
    files = [f for f in files if not f.name.startswith("_")]
    ctx = {"root": root, "meta": MetaIndex(root, opt("--source", "force-app"), opt("--org"))}
    any_fail = False
    for f in files:
        r = lint_file(f, ctx, stage)
        mark = "❌" if r["fail"] else ("✅ ready" if r["ready"] else "🟡 created, not ready")
        print(f"{r['key']} [{r.get('type')}/{r.get('status')}] {mark}")
        for e in r["fail"]:
            print(f"   ✗ {e}")
        if "--quiet" not in a:
            for e in r["todo_ready"]:
                print(f"   · to reach Ready: {e}")
            for e in r["warn"]:
                print(f"   ! {e}")
        any_fail |= bool(r["fail"])
    print(f"\n{len(files)} tickets checked")
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
