#!/usr/bin/env python3
"""Turn UI recordings into a draft tester test set. See workflow/processes/automated-pipeline.md §8.

usage: recording_to_cases.py <KEY> RECORDING... [--project DIR]
  RECORDING: Chrome DevTools Recorder JSON export (*.json) or a Playwright codegen / test script (*.ts, *.js, *.py).
Writes docs/tests/<KEY>/tester.draft.yaml — one case per recording. The tester fills `ac`, confirms every
`then` marked INFERRED, and saves the result as tester.yaml. A draft never counts as the tester's set.
"""
import json
import re
import sys
from pathlib import Path

import yaml

INFERRED = "INFERRED — tester must confirm the expected result"


def selector_label(step):
    for group in step.get("selectors") or []:
        for s in group if isinstance(group, list) else [group]:
            if str(s).startswith("aria/"):
                return str(s)[5:]
    groups = step.get("selectors") or [[""]]
    first = groups[0]
    return str(first[0] if isinstance(first, list) else first)


def from_devtools(path):
    rec = json.loads(Path(path).read_text())
    start, actions, checks = "", [], []
    for s in rec.get("steps") or []:
        t = s.get("type")
        if t == "navigate" and not start:
            start = s.get("url", "")
        elif t == "navigate":
            actions.append(f"go to {s.get('url', '')}")
        elif t in ("click", "doubleClick"):
            actions.append(f"click '{selector_label(s)}'")
        elif t == "change":
            actions.append(f"enter '{s.get('value', '')}' in '{selector_label(s)}'")
        elif t == "keyDown" and s.get("key") in ("Enter", "Tab"):
            actions.append(f"press {s['key']}")
        elif t == "waitForElement":
            checks.append(f"'{selector_label(s)}' is shown")
        elif t == "waitForExpression":
            checks.append(f"expression holds: {s.get('expression', '')}")
        for a in s.get("assertedEvents") or []:
            if a.get("type") == "navigation" and a.get("title"):
                checks.append(f"page '{a['title']}' opens")
    return rec.get("title") or Path(path).stem, start, actions, checks


PW_ACTION = re.compile(r"""(get_by_\w+|getBy\w+|locator)\((.+?)\)\.(click|fill|check|select_option|selectOption|press)\((.*?)\)""")
PW_EXPECT = re.compile(r"""expect\((.+?)\)\.(to_\w+|to\w+|not\.\w+)\((.*?)\)""")
PW_GOTO = re.compile(r"""\.goto\(\s*['"]([^'"]+)['"]""")


def from_playwright(path):
    start, actions, checks = "", [], []
    for line in Path(path).read_text().splitlines():
        if (m := PW_GOTO.search(line)):
            if start:
                actions.append(f"go to {m.group(1)}")
            else:
                start = m.group(1)
        elif (m := PW_EXPECT.search(line)):
            checks.append(f"{m.group(1).strip()} {m.group(2)} {m.group(3).strip()}".strip())
        elif (m := PW_ACTION.search(line)):
            target = m.group(2).strip()
            verb, arg = m.group(3), m.group(4).strip()
            actions.append(f"{verb} {target}" + (f" with {arg}" if arg else ""))
    title = re.search(r"""test\(\s*['"]([^'"]+)['"]""", Path(path).read_text())
    return (title.group(1) if title else Path(path).stem), start, actions, checks


def to_case(i, path):
    title, start, actions, checks = (from_devtools if path.suffix == ".json" else from_playwright)(path)
    return {"id": f"T-{i:02d}", "ac": [], "category": "ui", "title": title,
            "given": f"user starts at {start or 'the recorded start page'} (recording: {path.name})",
            "when": "; ".join(actions) or "the recorded steps",
            "then": "; ".join(checks) if checks else INFERRED,
            "level": "uat", "automation": {"type": "manual", "test": "-"},
            "source": f"recording {path.name}"}


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    root = Path(".").resolve()
    if "--project" in a:
        i = a.index("--project")
        root = Path(a[i + 1]).resolve()
        a = a[:i] + a[i + 2:]
    files = [Path(x) for x in a[1:]]
    cases = [to_case(i, f) for i, f in enumerate(files, 1)]
    out = root / "docs/tests" / a[0] / "tester.draft.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump({"ticket": a[0], "source": "recordings (draft)", "author": "",
                                   "note": "Fill ac for every case, confirm INFERRED results, then save as tester.yaml.",
                                   "cases": cases}, sort_keys=False, allow_unicode=True))
    inferred = sum(c["then"] == INFERRED for c in cases)
    print(f"Wrote {out.relative_to(root)}: {len(cases)} case(s), {inferred} with an inferred result to confirm")


if __name__ == "__main__":
    main()
