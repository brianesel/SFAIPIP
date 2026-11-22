#!/usr/bin/env python3
"""UAT as a real user: run Playwright specs logged in as a persona, import the results. Phase 3.
See workflow/processes/automated-pipeline.md §13.

usage:
  uat.py run <KEY> <persona> --iter N [--specs DIR] [--project DIR]
      Verifies the persona's org alias is a sandbox (never production), gets a one-time login URL with
      `sf org open --url-only`, runs `npx playwright test DIR --reporter=json` with it in env SFG_UAT_START_URL,
      saves the report to docs/tests/<KEY>/uat/<persona>-iter-N.json with the login URL removed.
      The URL is never printed; agents never see passwords or session ids.
  uat.py import <KEY> --iter N [--project DIR]
      Maps every uat report of iteration N to accepted `level: uat` cases (case id C-nn in the test title)
      and writes their status + evidence into docs/tests/<KEY>/results/iter-N.yaml.

Personas: guardrails.project.yaml → uat.personas: {<persona>: {alias: <sf alias authenticated as that sandbox user>,
profile: ..., permission_sets: [...]}}. A human creates the users and runs `sf org login web --alias <alias>` once.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dev_cycle  # noqa: E402
import org_guard  # noqa: E402


def persona_alias(root, persona):
    cfg = dev_cycle.project_cfg(root)
    p = ((cfg.get("uat") or {}).get("personas") or {}).get(persona)
    if not p or not p.get("alias"):
        sys.exit(f"persona '{persona}' not in guardrails.project.yaml → uat.personas")
    alias = p["alias"]
    if alias in ((cfg.get("orgs") or {}).get("production") or []):
        sys.exit(f"persona alias '{alias}' is a production org (HG-09)")
    facts = org_guard.org_facts(alias, root)
    if not facts or facts.get("IsSandbox") is not True:
        sys.exit(f"persona alias '{alias}' is not a verified sandbox (HG-11)")
    return alias


def cmd_run(root, key, persona, n, specs):
    alias = persona_alias(root, persona)
    r = subprocess.run(["sf", "org", "open", "--url-only", "--target-org", alias, "--json"], cwd=root, capture_output=True, text=True)
    try:
        url = json.loads(r.stdout)["result"]["url"]
    except (json.JSONDecodeError, KeyError, TypeError):
        sys.exit(f"could not get a login URL for persona '{persona}' (alias {alias}); run `sf org login web --alias {alias}`")
    spec_dir = specs or f"tests/uat/{key}"
    run = subprocess.run(["npx", "playwright", "test", spec_dir, "--reporter=json"], cwd=root, capture_output=True, text=True,
                         env={**os.environ, "SFG_UAT_START_URL": url, "SFG_UAT_PERSONA": persona})
    report = run.stdout.replace(url, "<login-url removed>")
    out = dev_cycle.tdir(root, key) / "uat" / f"{persona}-iter-{n}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    print(f"UAT {persona}: playwright exit {run.returncode} → {out.relative_to(root)}")


def specs_in(report):
    stack, out = list(report.get("suites") or []), []
    while stack:
        s = stack.pop()
        stack += s.get("suites") or []
        out += s.get("specs") or []
    return out


def cmd_import(root, key, n):
    d = dev_cycle.tdir(root, key)
    ag = dev_cycle.load_yaml(d / "agreed.yaml") or sys.exit("agreed.yaml missing")
    found = {}
    for rep in sorted((d / "uat").glob(f"*-iter-{n}.json")):
        try:
            data = json.loads(rep.read_text() or "{}")
        except json.JSONDecodeError:
            continue
        for spec in specs_in(data):
            for cid in re.findall(r"\bC-\d+\b", spec.get("title", "")):
                results = [res for t in spec.get("tests") or [] for res in t.get("results") or []]
                ok = bool(results) and all(res.get("status") == "passed" for res in results)
                files = [a.get("path") for res in results for a in res.get("attachments") or [] if a.get("path")]
                err = next((res.get("error", {}).get("message", "") for res in results if res.get("error")), "")
                found[cid] = {"status": "pass" if ok else "fail", "evidence": ", ".join([str(rep.relative_to(root))] + files),
                              "note": f"persona {rep.name.split('-iter-')[0]}" + (f": {err.splitlines()[0][:150]}" if err else "")}
    p = d / "results" / f"iter-{n}.yaml"
    doc = dev_cycle.load_yaml(p, {}) or {"iteration": n, "date": dt.date.today().isoformat(), "build": "", "results": {}}
    uat = [c for c in ag.get("cases") or [] if c.get("status") == "accepted" and c.get("level") == "uat"]
    for c in uat:
        doc["results"][c["id"]] = found.get(c["id"]) or {"status": "blocked", "evidence": "", "note": f"no UAT spec titled with {c['id']}"}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    passed = sum(doc["results"][c["id"]]["status"] == "pass" for c in uat)
    print(f"UAT import iteration {n}: {passed}/{len(uat)} uat cases pass → {p.relative_to(root)}")


def main():
    a = sys.argv[1:]
    root = Path(".").resolve()
    if "--project" in a:
        i = a.index("--project")
        root, a = Path(a[i + 1]).resolve(), a[:i] + a[i + 2:]
    opt = lambda flag: a[a.index(flag) + 1] if flag in a else None
    if len(a) >= 4 and a[0] == "run":
        cmd_run(root, a[1], a[2], int(opt("--iter")), opt("--specs"))
    elif len(a) >= 2 and a[0] == "import":
        cmd_import(root, a[1], int(opt("--iter")))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
