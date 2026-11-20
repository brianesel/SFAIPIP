#!/usr/bin/env python3
"""Build gate: no write to force-app/ until docs/design/design-signoff.md is approved.

Modes
  --hook   Claude Code PreToolUse hook. Reads tool JSON on stdin. Exit 2 = block (reason on stderr).
  --ci     git pre-commit / CI. Blocks if staged/changed files touch force-app/ and sign-off fails.
  (none)   Print sign-off status for the project in --project (default cwd). Exit 1 if not approved.

Sign-off passes when:
  - 'Status: APPROVED', non-empty 'Approved-by:' and 'Date:'
  - no must-decide row with status 'open'
  - no must-decide row tagged [low] or [dunno]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

SIGNOFF = Path("docs/design/design-signoff.md")
GUARDED = "force-app/"


def find_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "sfdx-project.json").exists() or (p / SIGNOFF).exists():
            return p
    return start


def check_signoff(root: Path):
    f = root / SIGNOFF
    if not f.exists():
        return False, [f"{SIGNOFF} missing. Run discovery first (workflow/phases/02-discovery.md)."]
    text = f.read_text(encoding="utf-8")
    problems = []
    field = lambda name: (re.search(rf"^{name}:[ \t]*(.*)$", text, re.M) or [None, ""])[1].strip()
    if field("Status").upper() != "APPROVED":
        problems.append(f"Status is '{field('Status') or 'empty'}', needs APPROVED.")
    if not field("Approved-by"):
        problems.append("Approved-by is empty.")
    if not field("Date"):
        problems.append("Date is empty.")
    section = text.split("## Must-decide", 1)[1].split("\n## ", 1)[0] if "## Must-decide" in text else ""
    for line in section.splitlines():
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells[0].lower() == "id":
            continue
        low = line.lower()
        if re.search(r"\|\s*open\s*\|", low):
            problems.append(f"Open item: {cells[0]}")
        elif "[low]" in low or "[dunno]" in low:
            problems.append(f"Low-confidence item: {cells[0]}")
        elif len(cells) > 1 and not cells[1]:
            problems.append(f"No decision text: {cells[0]}")
    problems += check_integrations(root)
    return not problems, problems


def check_integrations(root: Path):
    """Integration inventory: every interface row decided (ARCH-002, decided per interface)."""
    f = root / "docs/design/integration-inventory.md"
    if not f.exists():
        return []
    lines = [l for l in f.read_text(encoding="utf-8").splitlines() if l.startswith("|")]
    if len(lines) < 3:
        return []
    head = [c.strip().lower() for c in lines[0].strip("|").split("|")]
    if "status" not in head:
        return []
    si = head.index("status")
    sti = head.index("style") if "style" in head else None
    out = []
    for l in lines[2:]:
        cells = [c.strip() for c in l.strip("|").split("|")]
        if len(cells) <= si or not cells[0]:
            continue
        if cells[si].lower() in ("", "pending"):
            out.append(f"Integration {cells[0]}: style not decided (ARCH-002, per interface)")
        elif sti is not None and not cells[sti]:
            out.append(f"Integration {cells[0]}: decided but Style empty")
    return out


def check_dev_tests(root: Path):
    """If dev.require_agreed_tests is on: active ticket must have a valid agreed test set."""
    try:
        import yaml
        cfg = yaml.safe_load((root / "guardrails.project.yaml").read_text()) or {}
    except Exception:
        return []
    if not (cfg.get("dev") or {}).get("require_agreed_tests"):
        return []
    act = root / ".sfg/active-ticket"
    if not act.exists():
        return ["No active ticket. Run: dev_cycle.py start <KEY>"]
    key = act.read_text().strip()
    import dev_cycle  # lazy: dev_cycle imports this module
    _, fm = dev_cycle.find_ticket(root, key)
    errs = dev_cycle.align_check(root / "docs/tests" / key, fm, dev_cycle.ac_ids(fm), quiet=True)
    return [f"{key}: agreed test set not valid → {e}" for e in errs]


def block(problems):
    msg = "BUILD GATE: not allowed to write force-app/ yet.\n- " + "\n- ".join(problems)
    msg += "\nGuardrails: PR-01 (ask before build), PR-08 (tests before code). See workflow/project-map.md."
    return msg


def hook_mode():
    data = json.load(sys.stdin)
    path = (data.get("tool_input") or {}).get("file_path", "")
    if GUARDED not in path.replace("\\", "/"):
        sys.exit(0)
    root = find_root(Path(data.get("cwd") or ".").resolve())
    ok, problems = check_signoff(root)
    if ok:
        problems = check_dev_tests(root)
    if problems:
        print(block(problems), file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


def ci_mode():
    try:
        out = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True).stdout
        if not out.strip():  # CI: compare to default branch
            out = subprocess.run(["git", "diff", "--name-only", "origin/HEAD...HEAD"],
                                 capture_output=True, text=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        out = ""
    if not any(f.startswith(GUARDED) or f"/{GUARDED}" in f for f in out.splitlines()):
        sys.exit(0)
    ok, problems = check_signoff(find_root(Path.cwd()))
    if not ok:
        print(block(problems), file=sys.stderr)
        sys.exit(1)


def main():
    args = sys.argv[1:]
    if "--hook" in args:
        hook_mode()
    elif "--ci" in args:
        ci_mode()
    else:
        root = Path(args[args.index("--project") + 1]) if "--project" in args else Path.cwd()
        ok, problems = check_signoff(find_root(root.resolve()))
        print("Sign-off: APPROVED ✅" if ok else block(problems))
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
