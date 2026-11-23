#!/usr/bin/env python3
"""Guided project setup: init → project facts into guardrails.project.yaml → org login → baseline retrieve.

usage:
  setup_project.py [PROJECT_DIR]                      ask in the terminal (Enter keeps the shown default)
  setup_project.py [PROJECT_DIR] --answers FILE       take answers from a YAML file (used by the sfg-setup skill)
  options: --no-login  --no-retrieve

Safe to rerun: existing files are kept, filled values are offered as defaults, logged-in orgs are skipped.
Only reads from orgs. Never sets approval or architecture decisions: those stay with the named humans (AI-01, PR-15).
Answers file keys: path, team_profile, devs, admins, approver, pm, tech_lead, source_alias, source_kind,
source_url, production, write_allowed, standard_objects, base_branch, login, retrieve.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))
import init_project  # noqa: E402

LOGIN_URL = {"production": "https://login.salesforce.com", "sandbox": "https://test.salesforce.com"}
CHOICES = {"path": ("existing-org", "new-org"), "team_profile": ("solo", "small", "multi-team"),
           "source_kind": ("production", "sandbox")}


def split(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


def ask(key, question, default, answers):
    if answers is not None:
        v = answers.get(key, default)
    else:
        shown = ", ".join(default) if isinstance(default, list) else default
        v = input(f"{question} [{shown}]: ").strip() or default
    if isinstance(default, list):
        v = split(v)
    elif isinstance(default, bool):
        v = v if isinstance(v, bool) else str(v).lower() in ("y", "yes", "true", "1")
    elif isinstance(default, int):
        v = int(v)
    else:
        v = str(v).strip()
    if key in CHOICES and v not in CHOICES[key]:
        sys.exit(f"{key}: '{v}' is not one of {', '.join(CHOICES[key])}")
    return v


def set_key(text, key, value, indent=None):
    """Replace `key: value` on its line, keeping indentation and the trailing comment."""
    if isinstance(value, list):
        val = "[" + ", ".join(value) + "]"
    elif isinstance(value, int):
        val = str(value)
    else:
        val = json.dumps(value)
    ind = r"[ ]*" if indent is None else " " * indent
    pat = re.compile(rf"^({ind}{re.escape(key)}:)[ ]*([^#\n]*?)([ ]*#.*)?$", re.M)
    if not pat.search(text):
        sys.exit(f"guardrails.project.yaml has no `{key}:` line; re-copy it from the template")
    return pat.sub(lambda m: f"{m.group(1)} {val}{m.group(3) or ''}", text, count=1)


def collect(cfg, answers):
    orgs, team, roles = cfg.get("orgs") or {}, cfg.get("team") or {}, cfg.get("roles") or {}
    a = {}
    print("\n1/3 Project and team")
    a["path"] = ask("path", "Existing org or new org? (existing-org | new-org)", cfg.get("path") or "existing-org", answers)
    a["team_profile"] = ask("team_profile", "Team profile (solo | small | multi-team)", cfg.get("team_profile") or "small", answers)
    a["devs"] = ask("devs", "Number of developers", team.get("devs") or 1, answers)
    a["admins"] = ask("admins", "Number of admins", team.get("admins") or 0, answers)
    print("\n2/3 People who decide (names; they approve, the AI never does)")
    a["approver"] = ask("approver", "Customer approver (signs G1/G2)", roles.get("approver") or "", answers)
    a["pm"] = ask("pm", "Project manager", roles.get("pm") or "", answers)
    a["tech_lead"] = ask("tech_lead", "Tech lead", roles.get("tech_lead") or "", answers)
    print("\n3/3 Orgs (aliases are local names for `sf`)")
    src_default = (orgs.get("evaluation_readonly") or orgs.get("production") or [""])[0]
    a["source_alias"] = ask("source_alias", "Org to retrieve the baseline from (alias)", src_default, answers)
    kind_default = "production" if a["source_alias"] in (orgs.get("production") or []) or not a["source_alias"] else "sandbox"
    a["source_kind"] = ask("source_kind", "Is that org production or a sandbox?", kind_default, answers)
    a["source_url"] = ask("source_url", "My Domain login URL (empty = standard login URL)", "", answers)
    prod_default = sorted(set(orgs.get("production") or []) | ({a["source_alias"]} if a["source_kind"] == "production" else set()))
    a["production"] = ask("production", "All production aliases (comma-separated)", prod_default, answers)
    a["write_allowed"] = ask("write_allowed", "Sandbox aliases the AI may write to (comma-separated)", orgs.get("write_allowed") or [], answers)
    a["standard_objects"] = ask("standard_objects", "Standard objects to add to the baseline manifest besides the 15 listed (comma-separated)", [], answers)
    a["base_branch"] = ask("base_branch", "Git base branch for PRs", (cfg.get("dev") or {}).get("base_branch") or "main", answers)
    return a


def validate(a):
    clash = set(a["write_allowed"]) & (set(a["production"]) | ({a["source_alias"]} if a["path"] == "existing-org" else set()))
    if clash:
        sys.exit(f"HG-09/HG-08: {', '.join(sorted(clash))} cannot be write-allowed: production or under evaluation")
    if a["source_kind"] == "production" and a["source_alias"] and a["source_alias"] not in a["production"]:
        a["production"].append(a["source_alias"])


def write_config(root, a):
    f = root / "guardrails.project.yaml"
    t = f.read_text()
    for k in ("path", "team_profile"):
        t = set_key(t, k, a[k], 0)
    t = set_key(t, "devs", a["devs"], 2)
    t = set_key(t, "admins", a["admins"], 2)
    for k in ("approver", "pm", "tech_lead"):
        t = set_key(t, k, a[k], 2)
    t = set_key(t, "production", a["production"], 2)
    t = set_key(t, "write_allowed", a["write_allowed"], 2)
    readonly = [a["source_alias"]] if a["path"] == "existing-org" and a["source_alias"] else []
    t = set_key(t, "evaluation_readonly", readonly, 2)
    t = set_key(t, "base_branch", a["base_branch"], 2)
    yaml.safe_load(t)
    f.write_text(t)
    print(f"updated: {f}")


def ensure_dx_project(root):
    manifest = root / "manifest/baseline-package.xml"
    version = re.search(r"<version>([\d.]+)</version>", manifest.read_text()).group(1)
    f = root / "sfdx-project.json"
    if f.exists():
        return
    f.write_text(json.dumps({"packageDirectories": [{"path": "force-app", "default": True}], "name": root.name,
                             "namespace": "", "sfdcLoginUrl": LOGIN_URL["production"], "sourceApiVersion": version},
                            indent=2) + "\n")
    print(f"created: {f}")


def add_standard_objects(root, names):
    f = root / "manifest/baseline-package.xml"
    t = f.read_text()
    block = re.search(r"<types>\s*(?:<members>[^<]*</members>\s*)+<name>CustomObject</name>", t).group(0)
    have = set(re.findall(r"<members>([^<]*)</members>", block))
    new = [n for n in names if n not in have]
    if not new:
        return
    add = "".join(f"<members>{n}</members>\n        " for n in new)
    t = t.replace(block, block.replace("<name>CustomObject</name>", add + "<name>CustomObject</name>"), 1)
    f.write_text(t)
    print(f"manifest: added {', '.join(new)}")


def run(root, *args, check=True):
    print("$ " + " ".join(args))
    r = subprocess.run(list(args), cwd=root)
    if check and r.returncode:
        sys.exit(f"stopped: `{' '.join(args)}` exited {r.returncode}")
    return r.returncode


def logged_in(root, alias):
    r = subprocess.run(["sf", "org", "display", "--target-org", alias, "--json"], cwd=root, capture_output=True, text=True)
    return r.returncode == 0


def login(root, a, answers):
    kinds = {x: "production" for x in a["production"]} | {x: "sandbox" for x in a["write_allowed"]}
    if a["source_alias"]:
        kinds[a["source_alias"]] = a["source_kind"]
    for alias, kind in kinds.items():
        if logged_in(root, alias):
            print(f"logged in: {alias}")
            continue
        url = a["source_url"] if alias == a["source_alias"] and a["source_url"] else LOGIN_URL[kind]
        if answers is None and not ask("_", f"Log in to '{alias}' ({kind}) in the browser now? (y/n)", True, None):
            print(f"skipped: run `sf org login web --alias {alias} --instance-url {url}` later")
            continue
        run(root, "sf", "org", "login", "web", "--alias", alias, "--instance-url", url)


def retrieve(root, alias):
    py = sys.executable
    run(root, py, str(PKG / "tools/org_limits.py"), "show", alias, "--project", str(root))
    run(root, py, str(PKG / "tools/org_limits.py"), "check", alias, "--project", str(root))
    run(root, "sh", str(PKG / "tools/sf-safe"), "project", "retrieve", "start",
        "--manifest", "manifest/baseline-package.xml", "--target-org", alias)
    run(root, py, str(PKG / "tools/system_map.py"), "generate", "--project", str(root))
    print("Check the retrieve output above for types that refused `*` and list those by name.")


def main():
    args = sys.argv[1:]
    answers = None
    if "--answers" in args:
        i = args.index("--answers")
        answers = yaml.safe_load(Path(args[i + 1]).read_text()) or {}
        del args[i:i + 2]
    flags = {x for x in args if x.startswith("--")}
    pos = [x for x in args if not x.startswith("--")]
    root = Path(pos[0] if pos else ".").expanduser().resolve()

    print(f"Project: {root}")
    init_project.init(root)

    cfg = yaml.safe_load((root / "guardrails.project.yaml").read_text()) or {}
    a = collect(cfg, answers)
    validate(a)
    write_config(root, a)
    ensure_dx_project(root)
    add_standard_objects(root, a["standard_objects"])

    if "--no-login" not in flags and ask("login", "\nLog in to the orgs now?", True, answers):
        login(root, a, answers)
    if a["source_alias"] and "--no-retrieve" not in flags and \
            ask("retrieve", f"Retrieve the baseline metadata from '{a['source_alias']}' now (read-only)?", True, answers):
        if not logged_in(root, a["source_alias"]):
            sys.exit(f"'{a['source_alias']}' is not logged in: run `sf org login web --alias {a['source_alias']}` and rerun")
        retrieve(root, a["source_alias"])

    run(root, sys.executable, str(PKG / "tools/doctor.py"), "--project", str(root), check=False)
    print("\nStill for humans: architecture decisions (docs/decisions/ARCH-*.md), UAT personas, and approval in "
          "guardrails.project.yaml. Next: start Claude Code in the project and ask \"where are we?\".")


if __name__ == "__main__":
    main()
