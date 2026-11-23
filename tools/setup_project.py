#!/usr/bin/env python3
"""Guided project setup: init → project facts into guardrails.project.yaml → org login → baseline retrieve.

usage:
  setup_project.py [PROJECT_DIR]                      ask in the terminal (Enter keeps the shown default)
  setup_project.py [PROJECT_DIR] --answers FILE       take answers from a YAML file (used by the sfg-setup skill)
  options: --no-login  --no-retrieve

Safe to rerun: existing files are kept, filled values are offered as defaults, logged-in orgs are skipped.
Only reads from orgs. Never sets approval. Records the branching and sandbox strategy only as the answer of the
named human given in `decided_by` (ARCH-008/009, PR-15); "pending" leaves the decision open.
Answers file keys: path, team_profile, devs, admins, approver, pm, tech_lead, source_alias, source_kind,
source_url, production, branching_strategy, sandbox_strategy, decided_by, dev_aliases, integration_alias,
uat_alias, staging_alias, write_allowed, standard_objects, base_branch, login, retrieve.
"""
import datetime as dt
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
           "source_kind": ("production", "sandbox"),
           "branching_strategy": ("trunk", "environment-branches", "gitflow", "keep-existing", "pending"),
           "sandbox_strategy": ("lean", "standard", "governed", "keep-existing", "pending")}
# branching-environments.md: stages per sandbox strategy (type) and branch per stage per branching strategy
STAGES = {"lean": [("uat", "partial-copy")],
          "standard": [("integration", "developer-pro"), ("uat", "partial-copy")],
          "governed": [("integration", "developer-pro"), ("uat", "partial-copy"), ("staging", "full")]}
BRANCH = {"trunk": {"integration": "main", "uat": "main (release tag)", "staging": "main (release tag)", "production": "main (release tag)"},
          "environment-branches": {"integration": "integration", "uat": "uat", "staging": "staging", "production": "main"},
          "gitflow": {"integration": "develop", "uat": "release/*", "staging": "release/*", "production": "main"}}
PR_TARGET = {"trunk": "main", "environment-branches": "integration", "gitflow": "develop"}


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
    print("\n1/4 Project and team")
    a["path"] = ask("path", "Existing org or new org? (existing-org | new-org)", cfg.get("path") or "existing-org", answers)
    a["team_profile"] = ask("team_profile", "Team profile (solo | small | multi-team)", cfg.get("team_profile") or "small", answers)
    a["devs"] = ask("devs", "Number of developers", team.get("devs") or 1, answers)
    a["admins"] = ask("admins", "Number of admins", team.get("admins") or 0, answers)
    print("\n2/4 People who decide (names; they approve, the AI never does)")
    a["approver"] = ask("approver", "Customer approver (signs G1/G2)", roles.get("approver") or "", answers)
    a["pm"] = ask("pm", "Project manager", roles.get("pm") or "", answers)
    a["tech_lead"] = ask("tech_lead", "Tech lead", roles.get("tech_lead") or "", answers)
    print("\n3/4 Orgs (aliases are local names for `sf`)")
    src_default = (orgs.get("evaluation_readonly") or orgs.get("production") or [""])[0]
    a["source_alias"] = ask("source_alias", "Org to retrieve the baseline from (alias)", src_default, answers)
    kind_default = "production" if a["source_alias"] in (orgs.get("production") or []) or not a["source_alias"] else "sandbox"
    a["source_kind"] = ask("source_kind", "Is that org production or a sandbox?", kind_default, answers)
    a["source_url"] = ask("source_url", "My Domain login URL (empty = standard login URL)", "", answers)
    prod_default = sorted(set(orgs.get("production") or []) | ({a["source_alias"]} if a["source_kind"] == "production" else set()))
    a["production"] = ask("production", "All production aliases (comma-separated)", prod_default, answers)

    arch = cfg.get("architecture") or {}
    envs = {e.get("stage"): e for e in ((cfg.get("delivery") or {}).get("environments") or []) if isinstance(e, dict)}
    print("\n4/4 Branching and sandboxes (your team's decision; options: best-practices/architecture/branching-environments.md)")
    print("    Signals: DevOps Center → environment-branches · solo/small with CI → trunk · release trains → gitflow")
    a["branching_strategy"] = ask("branching_strategy", "Branching strategy (trunk | environment-branches | gitflow | keep-existing | pending)",
                                  arch.get("branching_strategy") or "pending", answers)
    print("    Sandboxes: lean = dev → UAT → prod · standard = dev → integration → UAT → prod · governed = + staging (Full)")
    a["sandbox_strategy"] = ask("sandbox_strategy", "Sandbox strategy (lean | standard | governed | keep-existing | pending)",
                                arch.get("sandbox_strategy") or "pending", answers)
    decided = {a["branching_strategy"], a["sandbox_strategy"]} - {"pending"}
    a["decided_by"] = ask("decided_by", "Who made this decision (name)", a["tech_lead"], answers) if decided else ""
    if decided and not a["decided_by"]:
        sys.exit("decided_by: a named human records the decision (PR-15); answer 'pending' to decide later")
    a["dev_aliases"] = ask("dev_aliases", "Developer sandbox aliases (comma-separated)",
                           [e["alias"] for e in envs.values() if e.get("stage") == "dev" and e.get("alias")], answers)
    for stage, _ in STAGES.get(a["sandbox_strategy"], []):
        a[f"{stage}_alias"] = ask(f"{stage}_alias", f"{stage.upper()} sandbox alias", (envs.get(stage) or {}).get("alias") or "", answers)
    ai_default = orgs.get("write_allowed") or [x for x in a["dev_aliases"] + [a.get("integration_alias", "")] if x]
    a["write_allowed"] = ask("write_allowed", "Sandbox aliases the AI may write to (dev/integration only)", ai_default, answers)
    a["standard_objects"] = ask("standard_objects", "Standard objects to add to the baseline manifest besides the 15 listed (comma-separated)", [], answers)
    branch_default = PR_TARGET.get(a["branching_strategy"]) or (cfg.get("dev") or {}).get("base_branch") or "main"
    a["base_branch"] = ask("base_branch", "Branch pull requests target", branch_default, answers)
    return a


def environments(a):
    """Promotion chain for delivery.environments, or None when the strategies are not both decided here."""
    if a["sandbox_strategy"] not in STAGES or a["branching_strategy"] not in BRANCH:
        return None
    br = BRANCH[a["branching_strategy"]]
    ai = set(a["write_allowed"])
    chain = [{"stage": "dev", "alias": x, "type": "developer", "branch": "feature/<KEY>", "ai_writes": x in ai}
             for x in a["dev_aliases"]]
    for stage, kind in STAGES[a["sandbox_strategy"]]:
        alias = a.get(f"{stage}_alias", "")
        chain.append({"stage": stage, "alias": alias, "type": kind, "branch": br[stage], "ai_writes": alias in ai})
    chain.append({"stage": "production", "alias": (a["production"] or [""])[0], "type": "production",
                  "branch": br["production"], "ai_writes": False})
    return chain


def validate(a):
    clash = set(a["write_allowed"]) & (set(a["production"]) | ({a["source_alias"]} if a["path"] == "existing-org" else set()))
    if clash:
        sys.exit(f"HG-09/HG-08: {', '.join(sorted(clash))} cannot be write-allowed: production or under evaluation")
    later = {a.get("uat_alias"), a.get("staging_alias")} - {"", None}
    if set(a["write_allowed"]) & later:
        sys.exit(f"HG-11: {', '.join(sorted(set(a['write_allowed']) & later))} is a UAT/staging sandbox; the AI writes only "
                 "to dev and integration sandboxes (branching-environments.md rule 3)")
    if a["source_kind"] == "production" and a["source_alias"] and a["source_alias"] not in a["production"]:
        a["production"].append(a["source_alias"])


def set_environments(text, chain):
    """Replace the delivery.environments value (one line or a block of `- {...}` items) with the chain."""
    items = "".join("\n    - {" + ", ".join(f"{k}: {json.dumps(v)}" for k, v in e.items()) + "}" for e in chain)
    pat = re.compile(r"^(  environments:)[ ]*(\[\])?([ ]*#[^\n]*)?((?:\n    - [^\n]*)*)", re.M)
    if not pat.search(text):
        sys.exit("guardrails.project.yaml has no `delivery.environments:` line; re-copy it from the template")
    def repl(m):
        note = "   " + m.group(3).lstrip() if m.group(3) else ""
        return f"{m.group(1)}{note}{items}" if chain else f"{m.group(1)} []{note}"
    return pat.sub(repl, text, count=1)


def record_decision(root, card, choice, who):
    f = root / "docs/decisions" / card
    if choice == "pending" or not f.exists():
        return
    t = f.read_text()
    for field, val in (("Status", "decided"), ("Decided-by", who), ("Date", dt.date.today().isoformat()), ("Choice", choice)):
        t = re.sub(rf"^{field}:[^\n<]*", f"{field}: {val}".ljust(25) if field != "Decided-by" else f"{field}: {val}", t, count=1, flags=re.M)
    f.write_text(t)
    print(f"recorded: {f.name} = {choice} (decided by {who})")


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
    t = set_key(t, "branching_strategy", a["branching_strategy"], 2)
    t = set_key(t, "sandbox_strategy", a["sandbox_strategy"], 2)
    chain = environments(a)
    if chain is not None:
        t = set_environments(t, chain)
    yaml.safe_load(t)
    f.write_text(t)
    print(f"updated: {f}")
    record_decision(root, "ARCH-008-branching-strategy.md", a["branching_strategy"], a["decided_by"])
    record_decision(root, "ARCH-009-sandbox-strategy.md", a["sandbox_strategy"], a["decided_by"])


def ensure_dx_project(root):
    manifest = root / "manifest/baseline-package.xml"
    version = re.search(r"<version>([\d.]+)</version>", manifest.read_text()).group(1)
    f = root / "sfdx-project.json"
    if not f.exists():
        f.write_text(json.dumps({"packageDirectories": [{"path": "force-app", "default": True}], "name": root.name,
                                 "namespace": "", "sfdcLoginUrl": LOGIN_URL["production"], "sourceApiVersion": version},
                                indent=2) + "\n")
        print(f"created: {f}")
    # sf refuses to run when a package directory listed in sfdx-project.json is missing (MissingPackageDirectoryError)
    for d in dx_problems(root, create=True):
        print(f"warning: {d}")
    fi = root / ".forceignore"
    if not fi.exists():
        fi.write_text("# files the Salesforce CLI skips on deploy and retrieve\n**/jsconfig.json\n**/.eslintrc.json\n**/__tests__/**\n")
        print(f"created: {fi}")


def dx_problems(root, create=False):
    """What stops `sf project retrieve start` from running in root; with create=True, add missing package folders."""
    f = root / "sfdx-project.json"
    if not f.exists():
        return ["sfdx-project.json missing"]
    try:
        dirs = [d.get("path") for d in json.loads(f.read_text()).get("packageDirectories") or []]
    except (ValueError, AttributeError) as e:
        return [f"sfdx-project.json unreadable: {e}"]
    if not dirs or not all(dirs):
        return ["sfdx-project.json has no packageDirectories path"]
    problems = []
    for d in dirs:
        p = root / d
        if not p.is_dir():
            if create:
                (p / "main" / "default").mkdir(parents=True, exist_ok=True)
                print(f"created: {p}/main/default")
            else:
                problems.append(f"package directory '{d}' from sfdx-project.json does not exist")
    if not (root / "manifest/baseline-package.xml").exists():
        problems.append("manifest/baseline-package.xml missing")
    return problems


def manual_retrieve_help(root, alias, problems):
    print("\nRetrieve skipped — the project is not ready for the Salesforce CLI:")
    for p in problems:
        print(f"  - {p}")
    print(f"Fix it, or retrieve by hand in {root}:\n"
          f"  python3 {PKG}/tools/org_limits.py show {alias}\n"
          f"  sf project retrieve start --manifest manifest/baseline-package.xml --target-org {alias}\n"
          f"  python3 {PKG}/tools/system_map.py generate\n"
          "then rerun setup with --no-retrieve to finish the checks.")


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
    problems = dx_problems(root)
    if problems:
        return manual_retrieve_help(root, alias, problems)
    if run(root, "sh", str(PKG / "tools/sf-safe"), "project", "retrieve", "start",
           "--manifest", "manifest/baseline-package.xml", "--target-org", alias, check=False):
        return manual_retrieve_help(root, alias, ["the retrieve command failed (see its error above)"])
    run(root, py, str(PKG / "tools/system_map.py"), "generate", "--project", str(root))
    print("Check the retrieve output above for types that refused `*` and list those by name.")
    return True


STEPS = ["Copy the project files", "Answer the project questions", "Write the config and the DX project",
         "Log in to the orgs", "Retrieve the baseline metadata", "Check the project (doctor)"]


class Progress:
    MARK = {"done": "[x]", "skipped": "[-]", "failed": "[!]", "todo": "[ ]"}

    def __init__(self):
        self.state = ["todo"] * len(STEPS)

    def finish(self, n, state="done", note=""):
        self.state[n - 1] = state
        nxt = next((i for i, s in enumerate(self.state) if s == "todo"), None)
        print("\n── Setup progress " + "─" * 30)
        for i, (name, s) in enumerate(zip(STEPS, self.state)):
            mark = "[>]" if i == nxt else self.MARK[s]
            print(f" {mark} {i + 1}. {name}" + (f" ({s})" if s in ("skipped", "failed") else ""))
        print(f"{state.capitalize()}: step {n}/{len(STEPS)}, {STEPS[n - 1]}" + (f" ({note})" if note else "") + ".")
        print(f"Next: step {nxt + 1}, {STEPS[nxt]}." if nxt is not None else "Next: setup is complete.")
        print("─" * 48)


def congrats(root, a, prog):
    todo = []
    if prog.state[3] != "done":
        todo.append("Log in to the orgs: `sf org login web --alias <alias> --instance-url <url>` (you sign in, in the browser).")
    if prog.state[4] != "done" and a["source_alias"]:
        todo.append(f"Retrieve the baseline: rerun this setup, or follow the manual retrieve in the README (org '{a['source_alias']}').")
    todo.append("Still for humans: decide the architecture cards in docs/decisions/ARCH-*.md "
                "(structure level, trigger framework, ...) with the named decider.")
    if a["path"] == "existing-org":
        todo.append("Assess the existing org (read-only): in Claude Code, /sfg-assess, which scores it and writes docs/wiki/.")
    else:
        todo.append("Start discovery: in Claude Code, /sfg-discover, which asks the business questions and logs them in docs/design/.")
    todo += ["Ask \"where are we?\" (/sfg-workflow) any time to see the phase and the next step.",
             "Add UAT personas and fill approval in guardrails.project.yaml when the customer is ready (humans approve, never the AI).",
             "Commit the setup: `git add -A && git commit -m \"Set up SF AI pipeline\"`."]
    print("\n🎉 Congratulations, the setup is done!" + (" (some steps were skipped; they come first below)" if prog.state[3:5] != ["done", "done"] else ""))
    print(f"Project: {root}\nSuggested next actions:")
    for i, t in enumerate(todo, 1):
        print(f"  {i}. {t}")


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
    prog = Progress()
    init_project.init(root)
    prog.finish(1)

    cfg = yaml.safe_load((root / "guardrails.project.yaml").read_text()) or {}
    a = collect(cfg, answers)
    validate(a)
    prog.finish(2)

    write_config(root, a)
    ensure_dx_project(root)
    add_standard_objects(root, a["standard_objects"])
    prog.finish(3)

    if "--no-login" not in flags and ask("login", "\nLog in to the orgs now?", True, answers):
        login(root, a, answers)
        prog.finish(4)
    else:
        prog.finish(4, "skipped", "run `sf org login web --alias <alias>` yourself, then rerun")

    if a["source_alias"] and "--no-retrieve" not in flags and \
            ask("retrieve", f"Retrieve the baseline metadata from '{a['source_alias']}' now (read-only)?", True, answers):
        if not logged_in(root, a["source_alias"]):
            prog.finish(5, "failed", f"'{a['source_alias']}' is not logged in")
            sys.exit(f"'{a['source_alias']}' is not logged in: run `sf org login web --alias {a['source_alias']}` and rerun")
        ok = retrieve(root, a["source_alias"])
        prog.finish(5, "done" if ok else "skipped", "" if ok else "see the manual commands above")
    else:
        prog.finish(5, "skipped", "no source org" if not a["source_alias"] else "rerun without --no-retrieve when logged in")

    run(root, sys.executable, str(PKG / "tools/doctor.py"), "--project", str(root), check=False)
    prog.finish(6)
    congrats(root, a, prog)

if __name__ == "__main__":
    main()
