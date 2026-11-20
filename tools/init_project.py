#!/usr/bin/env python3
"""Start a project: copy templates/project into TARGET, add AGENTS.md + CLAUDE.md + git hook.
Never overwrites existing files."""
import shutil
import stat
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def copy_tree(src: Path, dst: Path):
    for f in src.rglob("*"):
        if f.is_dir():
            continue
        t = dst / f.relative_to(src)
        if t.exists():
            print(f"skip (exists): {t}")
            continue
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, t)
        print(f"created: {t}")


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: init_project.py /path/to/project")
    target = Path(sys.argv[1]).resolve()
    target.mkdir(parents=True, exist_ok=True)
    copy_tree(PKG / "templates" / "project", target)
    copy_tree(PKG / "best-practices" / "architecture" / "decisions", target / "docs" / "decisions")
    for name, body in {
        "AGENTS.md": (PKG / "AGENTS.md").read_text(),
        "CLAUDE.md": f"@AGENTS.md\n\nSF AI development pipeline package: {PKG}\n",
    }.items():
        t = target / name
        if not t.exists():
            t.write_text(body)
            print(f"created: {t}")
    hooks = target / ".git" / "hooks"
    if hooks.exists():
        h = hooks / "pre-commit"
        if not h.exists():
            h.write_text(f'#!/bin/sh\npython3 "{PKG}/tools/gate_check.py" --ci\n')
            h.chmod(h.stat().st_mode | stat.S_IEXEC)
            print(f"created: {h}")
    else:
        print("no .git yet: run `git init`, then rerun to install the pre-commit gate")


if __name__ == "__main__":
    main()
