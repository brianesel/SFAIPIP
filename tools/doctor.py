#!/usr/bin/env python3
"""Setup check for the SF AI development pipeline: machine + (optional) project.

usage: doctor.py [--project DIR]
Prints ✅ / ⚠ / ❌ per check with the fix. Exit 1 if any ❌.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
rows, bad = [], False


def add(ok, name, detail="", fix=""):
    global bad
    mark = {True: "✅", None: "⚠", False: "❌"}[ok]
    bad |= ok is False
    rows.append(f"{mark} {name}{' — ' + detail if detail else ''}{chr(10) + '     fix: ' + fix if fix and ok is not True else ''}")


def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return (r.stdout + r.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def machine():
    v = sys.version_info
    add(v >= (3, 10), "Python ≥ 3.10", f"{v.major}.{v.minor}", "install Python 3.10+ (Flow rules in Code Analyzer need it too)")
    try:
        import yaml  # noqa: F401
        add(True, "PyYAML")
    except ImportError:
        add(False, "PyYAML", "missing", "pip install pyyaml")
    add(bool(shutil.which("git")), "git", "", "install git")
    sf = run(["sf", "--version"])
    add(bool(sf), "Salesforce CLI (sf)", (sf or "").splitlines()[0] if sf else "not found", "npm install -g @salesforce/cli")
    if sf:
        plugins = run(["sf", "plugins"]) or ""
        add("code-analyzer" in plugins, "Code Analyzer plugin", "", "sf plugins install code-analyzer")
    j = run(["java", "-version"])
    m = re.search(r'version "(\d+)', j or "")
    add(bool(m) and int(m.group(1)) >= 11, "Java ≥ 11 (PMD engine)", m.group(0) if m else "not found", "install a JDK 11+ (e.g. Temurin 17)")
    n = run(["node", "--version"])
    nm = re.match(r"v(\d+)", n or "")
    add(bool(nm) and int(nm.group(1)) >= 18, "Node ≥ 18 (ESLint engine)", n or "not found", "install Node 18+")
    cc = run(["claude", "--version"])
    add(True if cc else None, "Claude Code CLI", cc or "not found (only needed for hooks + skills)",
        "npm install -g @anthropic-ai/claude-code")
    if cc:
        lst = run(["claude", "plugin", "list"]) or ""
        add(True if "sf-ai-dev-pipeline" in lst else None, "Plugin installed in Claude Code",
            "" if "sf-ai-dev-pipeline" in lst else "not installed",
            f"/plugin marketplace add {PKG}  then  /plugin install sf-ai-dev-pipeline@sf-ai-dev-pipeline")


def project(root: Path):
    import yaml
    f = root / "guardrails.project.yaml"
    if not f.exists():
        add(False, "guardrails.project.yaml", "missing", f"python3 {PKG}/tools/init_project.py {root}")
        return
    cfg = yaml.safe_load(f.read_text()) or {}
    pin = str(cfg.get("baseline", ""))
    ver = json.loads((PKG / ".claude-plugin/plugin.json").read_text())["version"]
    add(pin == f"sf-ai-dev-pipeline@{ver}" or (None if pin.startswith("sf-ai-dev-pipeline@") else False),
        "Baseline pin", pin or "missing", f"set baseline: sf-ai-dev-pipeline@{ver} (upgrade deliberately, PR-11)")
    orgs = cfg.get("orgs") or {}
    add(bool(orgs.get("production")), "orgs.production set (prod guard)", str(orgs.get("production")),
        "add your production alias under orgs.production")
    add(True if orgs.get("write_allowed") else None, "orgs.write_allowed (sandbox lock)", str(orgs.get("write_allowed")),
        "add sandbox aliases; check each with tools/org_guard.py verify <alias>")
    mcp = root / ".mcp.json"
    if mcp.exists():
        t = mcp.read_text()
        add(not ("ALLOW_ALL_ORGS" in t or "REPLACE_WITH" in t or any(p and p in t for p in (orgs.get("production") or []))),
            "DX MCP server org scope", "", "set --orgs to write-allowed sandbox aliases only (no ALLOW_ALL_ORGS, no prod alias)")
    hook = root / ".git/hooks/pre-commit"
    add(hook.exists(), "git pre-commit gate", "", f"git init, then rerun python3 {PKG}/tools/init_project.py {root}")
    add((root / "AGENTS.md").exists() and (root / "CLAUDE.md").exists(), "AGENTS.md + CLAUDE.md", "", "rerun init_project.py")
    add(True if (root / ".sfg/rules-inventory.json").exists() else None, "Analyzer rule inventory", "",
        f"python3 {PKG}/tools/rule_map.py inventory && python3 {PKG}/tools/rule_map.py generate")
    add(True if (root / ".github/workflows").exists() else None, "CI workflow", "",
        f"copy {PKG}/ci/github-actions.yml to .github/workflows/")


def main():
    a = sys.argv[1:]
    print("Machine")
    machine()
    print("\n".join(rows))
    if "--project" in a:
        rows.clear()
        root = Path(a[a.index("--project") + 1]).resolve()
        print(f"\nProject {root}")
        project(root)
        print("\n".join(rows))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
