#!/usr/bin/env python3
"""Context pack for a ticket: what is already known about the area it touches.
See workflow/processes/automated-pipeline.md §7. Read-only: never writes to an org.

usage: context_pack.py <KEY> [--project DIR] [--org ALIAS] [--request-file F]
  Names come from the ticket's `metadata` list when the ticket exists, else from words in the request.
  --org adds dependencies from the Tooling API (MetadataComponentDependency), read-only query.
Writes docs/tests/<KEY>/context.md. Every item names its source (PR-02).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ticket_lint import parse  # noqa: E402

MAX_HITS = 10


def ticket_for(root, key):
    for f in sorted((root / "docs/tickets").glob("*.md")) if (root / "docs/tickets").exists() else []:
        if f.name.startswith("_"):
            continue
        fm, _ = parse(f)
        if fm and (fm.get("key") == key or f.stem == key):
            return f, fm
    return None, None


def names_from(fm, request):
    if fm and fm.get("metadata"):
        return [m["name"] for m in fm["metadata"] if m.get("name")]
    return sorted(set(re.findall(r"\b[A-Za-z][A-Za-z0-9_]*__[cer]\b|\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b", request or "")))


def short(name):
    return name.split(".")[-1]


def related_tickets(root, key, names):
    hits = []
    for f in sorted((root / "docs/tickets").glob("*.md")) if (root / "docs/tickets").exists() else []:
        if f.name.startswith("_") or f.stem == key:
            continue
        text = f.read_text(encoding="utf-8")
        found = [n for n in names if short(n) in text]
        if found:
            fm, _ = parse(f)
            hits.append(f"- {(fm or {}).get('key', f.stem)}: {(fm or {}).get('title', '')} — mentions {', '.join(found)} [source: {f.relative_to(root)}]")
    return hits[:MAX_HITS]


def source_files(root, names):
    src = root / "force-app"
    if not src.exists():
        return {}
    out = {}
    for n in names:
        s = short(n)
        files = [p for p in src.rglob(f"{s}.*") if p.is_file()]
        if files:
            out[n] = sorted({p.relative_to(root) for p in files})
    return out


def git_history(root, files):
    if not files:
        return []
    r = subprocess.run(["git", "log", "--oneline", f"-n{MAX_HITS}", "--", *map(str, files)],
                       cwd=root, capture_output=True, text=True)
    return [f"- {l} [source: git log]" for l in r.stdout.splitlines()] if r.returncode == 0 else []


def covering_tests(root, names):
    src = root / "force-app"
    if not src.exists():
        return []
    hits = []
    tests = [p for p in src.rglob("*.cls") if re.search(r"@isTest|@IsTest|testMethod", p.read_text(errors="ignore"))]
    for n in names:
        s = short(n)
        cov = [t.stem for t in tests if t.stem != s and re.search(rf"\b{re.escape(s)}\b", t.read_text(errors="ignore"))]
        if cov:
            hits.append(f"- {n}: {', '.join(sorted(cov)[:MAX_HITS])} [source: grep force-app test classes]")
    return hits


def dependencies(root, org, names):
    if not org:
        return ["- not queried (no --org given) [dunno: rerun with --org <alias>]"]
    out = []
    for n in names:
        q = ("SELECT MetadataComponentName, MetadataComponentType FROM MetadataComponentDependency "
             f"WHERE RefMetadataComponentName = '{short(n).replace(chr(39), '')}'")
        r = subprocess.run(["sf", "data", "query", "--use-tooling-api", "--query", q, "--target-org", org, "--json"],
                           cwd=root, capture_output=True, text=True)
        try:
            recs = json.loads(r.stdout).get("result", {}).get("records", [])
        except json.JSONDecodeError:
            out.append(f"- {n}: query failed [dunno: {r.stderr.strip()[:120]}]")
            continue
        refs = sorted({f"{x['MetadataComponentType']}:{x['MetadataComponentName']}" for x in recs})
        out.append(f"- {n}: {', '.join(refs[:MAX_HITS * 2]) or 'no references found'} "
                   f"[source: Tooling API MetadataComponentDependency, {org}]")
    return out


def build(root, key, org=None, request=""):
    tf, fm = ticket_for(root, key)
    names = names_from(fm, request)
    files = source_files(root, names)
    L = [f"# Context pack — {key}", "",
         f"Basis: {'ticket ' + str(tf.relative_to(root)) + ' metadata' if fm and fm.get('metadata') else 'request text (draft, refresh after the ticket is Ready)'}",
         f"Names: {', '.join(names) or 'none found'}", "",
         "## Related tickets", *(related_tickets(root, key, names) or ["- none found [source: docs/tickets]"]), "",
         "## Source files", *([f"- {n}: {', '.join(map(str, fs))}" for n, fs in files.items()] or ["- none in force-app (new components?)"]), "",
         "## Recent history of these files", *(git_history(root, [f for fs in files.values() for f in fs]) or ["- none [source: git log]"]), "",
         "## Tests that reference these components", *(covering_tests(root, names) or ["- none found"]), "",
         "## Dependencies (who references these components)", *dependencies(root, org, names), "",
         "## Known constraints",
         "- read docs/wiki/pattern-register.md and docs/decisions/ before building [source: project docs]", ""]
    out = root / "docs/tests" / key / "context.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L))
    return out


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        sys.exit(__doc__)
    opt = lambda flag: a[a.index(flag) + 1] if flag in a else None
    root = Path(opt("--project") or ".").resolve()
    request = Path(opt("--request-file")).read_text() if opt("--request-file") else ""
    print(f"Wrote {build(root, a[0], opt('--org'), request).relative_to(root)}")


if __name__ == "__main__":
    main()
