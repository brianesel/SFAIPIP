#!/usr/bin/env python3
"""Org limits: discover each org's daily limits and keep a reserve AI never spends (HG-12).

usage:
  org_limits.py show <alias> [--project DIR]     refresh and print the watched limits
  org_limits.py check <alias> [--project DIR]    exit 1 when a watched limit is below the reserve

Source: `sf org list limits --target-org <alias> --json` (max + remaining per limit; the 24-hour limits are rolling).
Cache: .sfg/limits.json, refreshed every `refresh_every` org commands or `refresh_minutes`, whichever comes first.
Policy: guardrails.project.yaml → orgs.limits (defaults below). Production aliases use production_reserve_pct.
Test fixture: env SFG_ORG_LIMITS=<json file> {alias: {LimitName: {max, remaining}}}.
Used by tools/org_guard.py (every sf command) and tools/pipeline.py (usage per step, run budget).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

DEFAULTS = {"enabled": True, "watch": ["DailyApiRequests", "DailyAsyncApexExecutions"], "reserve_pct": 50,
            "production_reserve_pct": 80, "refresh_every": 25, "refresh_minutes": 15, "run_budget": 3000}


def policy(root):
    f = root / "guardrails.project.yaml"
    orgs = ((yaml.safe_load(f.read_text()) or {}).get("orgs") or {}) if f.exists() and yaml else {}
    return {**DEFAULTS, **(orgs.get("limits") or {})}, set(orgs.get("production") or [])


def fetch(alias, root):
    """Live limits {name: {max, remaining}} or None when they can't be read."""
    fx = os.environ.get("SFG_ORG_LIMITS")
    if fx:
        return (json.loads(Path(fx).read_text()) or {}).get(alias)
    try:
        r = subprocess.run(["sf", "org", "list", "limits", "--target-org", alias, "--json"],
                           cwd=root, capture_output=True, text=True, timeout=90)
        rows = json.loads(r.stdout or "{}").get("result") or []
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    out = {x["name"]: {"max": x.get("max"), "remaining": x.get("remaining")} for x in rows if isinstance(x, dict) and x.get("name")}
    return out or None


def cache_file(root):
    return root / ".sfg/limits.json"


def load_cache(root):
    try:
        return json.loads(cache_file(root).read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(root, cache):
    cache_file(root).parent.mkdir(exist_ok=True)
    cache_file(root).write_text(json.dumps(cache, indent=2))


def current(alias, root, count=False, force=False):
    """Cached limits for alias, refreshed when stale. count=True records one more org command."""
    pol, _ = policy(root)
    cache = load_cache(root)
    entry = cache.get(alias) or {}
    entry["commands"] = entry.get("commands", 0) + (1 if count else 0)
    stale = (force or not entry.get("limits") or entry["commands"] >= pol["refresh_every"]
             or time.time() - entry.get("at", 0) > pol["refresh_minutes"] * 60)
    if stale:
        live = fetch(alias, root)
        entry = {"at": time.time(), "commands": 0, "limits": live} if live else {**entry, "limits": None}
    cache[alias] = entry
    save_cache(root, cache)
    return entry.get("limits")


def check(alias, root, count=False):
    """(ok, reasons) — reasons name HG-12 and the limit below the reserve."""
    pol, prod = policy(root)
    if not pol["enabled"]:
        return True, []
    limits = current(alias, root, count=count)
    if not limits:
        return False, [f"HG-12 could not read daily limits for '{alias}' (`sf org list limits`) — blocked (fail closed)"]
    reserve = pol["production_reserve_pct"] if alias in prod else pol["reserve_pct"]
    reasons = []
    for name in pol["watch"]:
        lim = limits.get(name)
        if not lim or not lim.get("max"):
            continue
        pct = 100.0 * lim["remaining"] / lim["max"]
        if pct < reserve:
            reasons.append(f"HG-12 '{alias}' {name}: {lim['remaining']}/{lim['max']} left ({pct:.0f}%) is below the "
                           f"{reserve}% reserve kept for people and integrations — AI org commands stop until it recovers "
                           "(24-hour rolling window) or a human changes orgs.limits")
    return not reasons, reasons


def remaining(alias, root, name="DailyApiRequests"):
    lim = (current(alias, root, force=True) or {}).get(name)
    return lim.get("remaining") if lim else None


def main():
    a = sys.argv[1:]
    root = Path(a[a.index("--project") + 1] if "--project" in a else ".").resolve()
    if len(a) >= 2 and a[0] == "show":
        limits = current(a[1], root, force=True)
        if not limits:
            sys.exit(f"could not read limits for {a[1]}")
        pol, prod = policy(root)
        print(f"Limits for {a[1]} (reserve {pol['production_reserve_pct'] if a[1] in prod else pol['reserve_pct']}%):")
        for name in pol["watch"]:
            lim = limits.get(name) or {}
            print(f"- {name}: {lim.get('remaining')}/{lim.get('max')} remaining")
    elif len(a) >= 2 and a[0] == "check":
        ok, reasons = check(a[1], root)
        print("✅ within reserve" if ok else "\n".join(reasons))
        sys.exit(0 if ok else 1)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
