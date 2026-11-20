#!/usr/bin/env python3
"""Weekly pipeline report (markdown). Read-only.

usage: weekly_report.py [--project DIR] [--source force-app] [--org ALIAS]
Writes docs/reports/weekly-<date>.md and prints it.
Sections: gates · ticket readiness · open change requests · waivers/overrides due · score trend.
"""
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_check import check_signoff  # noqa: E402
from status import g0, g1  # noqa: E402
from ticket_lint import MetaIndex, lint_file  # noqa: E402

SOON_DAYS = 30


def gates(root, cfg):
    rows = []
    if cfg is None:
        return [("G0", "❌ guardrails.project.yaml missing")]
    for name, probs in (("G0 intake", g0(cfg)), ("G1 project guardrails", g1(cfg, root)),
                        ("G2 design sign-off", check_signoff(root)[1])):
        rows.append((name, "✅" if not probs else "❌ " + "; ".join(probs[:3]) + (" …" if len(probs) > 3 else "")))
    return rows


def tickets(root, source, org):
    tdir = root / "docs/tickets"
    files = [f for f in sorted(tdir.glob("*.md")) if not f.name.startswith("_")] if tdir.exists() else []
    ctx = {"root": root, "meta": MetaIndex(root, source, org)}
    res = [lint_file(f, ctx) for f in files]
    return res


def due(cfg, today):
    out = []
    for w in (cfg or {}).get("waivers") or []:
        exp = w.get("expires")
        if not exp:
            continue
        d = dt.date.fromisoformat(str(exp))
        if d < today:
            out.append(f"🔴 waiver {w.get('check')} EXPIRED {exp} (exit {w.get('exit')}, owner {w.get('owner')})")
        elif (d - today).days <= SOON_DAYS:
            out.append(f"🟡 waiver {w.get('check')} expires {exp} (exit {w.get('exit')}, owner {w.get('owner')})")
    for o in (cfg or {}).get("overrides") or []:
        rv = o.get("review")
        if rv and dt.date.fromisoformat(str(rv)) <= today:
            out.append(f"🟡 override {o.get('check')} review date {rv} reached (owner {o.get('owner')})")
    return out


def trend(root):
    hist = sorted((root / "docs/wiki/_data/history").glob("scores-*.json")) if (root / "docs/wiki/_data/history").exists() else []
    if not hist:
        return ["No score history yet (run score.py)."]
    cur = json.loads(hist[-1].read_text())
    prev = json.loads(hist[-2].read_text()) if len(hist) > 1 else None
    L = [f"Latest: {cur.get('date')} · org {cur['org']['score']} {cur['org']['band']}"
         + (f" (prev {prev.get('date')}: {prev['org']['score']})" if prev else "")]
    L.append("")
    L.append("| Pillar | Score | Target | Δ vs prev |")
    L.append("|---|---|---|---|")
    for k, v in cur["pillars"].items():
        if "score" not in v:
            continue
        pv = prev["pillars"].get(k, {}).get("score") if prev else None
        delta = "–" if pv is None or v["score"] is None else f"{v['score'] - pv:+.1f}"
        L.append(f"| {v['name']} | {v['score']} | {v.get('target')} | {delta} |")
    return L


def main():
    a = sys.argv[1:]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    root = Path(opt("--project", ".")).resolve()
    today = dt.date.today()
    cfg_f = root / "guardrails.project.yaml"
    cfg = yaml.safe_load(cfg_f.read_text()) if cfg_f.exists() else None

    L = [f"# Weekly guardrails report — {today}", ""]
    L += ["## Gates", "", "| Gate | Status |", "|---|---|"]
    L += [f"| {g} | {s} |" for g, s in gates(root, cfg)]

    res = tickets(root, opt("--source", "force-app"), opt("--org"))
    L += ["", "## Tickets", ""]
    if not res:
        L.append("No tickets in docs/tickets/.")
    else:
        by_status = Counter(r.get("status", "?") for r in res)
        L.append("By status: " + " · ".join(f"{k} {v}" for k, v in sorted(by_status.items())))
        broken = [r for r in res if r["fail"]]
        not_ready = [r for r in res if not r["fail"] and not r["ready"] and r.get("status") in ("draft", "needs_refinement")]
        L.append(f"Ready: {sum(1 for r in res if r['ready'])} · not ready yet: {len(not_ready)} · failing lint: {len(broken)}")
        if broken:
            L += ["", "Failing (fix before next refinement):"]
            for r in broken:
                L.append(f"- {r['key']} [{r.get('status')}]: " + "; ".join(r["fail"][:3]) + (" …" if len(r["fail"]) > 3 else ""))
        crs = [r for r in res if r.get("type") == "cr" and r.get("status") != "done"]
        L += ["", "## Open change requests", ""]
        if not crs:
            L.append("None.")
        for r in crs:
            fm = yaml.safe_load(Path(r["file"]).read_text().split("---", 2)[1])
            L.append(f"- {r['key']} · {fm.get('cr_size')} → {fm.get('cr_decider')} · {fm.get('approval') or 'decision pending'} · {fm.get('title')}")

    L += ["", "## Waivers and overrides due", ""]
    d = due(cfg, today)
    L += d if d else ["Nothing due in the next 30 days."]
    L += ["", "## Score trend", ""]
    L += trend(root)

    text = "\n".join(L) + "\n"
    out = root / "docs/reports"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"weekly-{today}.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
