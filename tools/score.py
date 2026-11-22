#!/usr/bin/env python3
"""Score an org/project from rubric YAML + results JSON.

Flow: check -> aspect -> pillar -> org. Each check has ONE primary Well-Architected pillar.
Pillar scores are compared to project targets (profile). Priority uses gap = target - score.

results.json:
{
  "profile": "customer-facing",                 # optional, --profile wins
  "targets": {"fairness": "na"},                 # optional overrides
  "checks": {
    "tests.no_seealldata": {"pass": true, "evidence": "code-analyzer.json"},
    "tests.coverage":      {"value": 82, "evidence": "apex-test-run.json"},
    "tests.behavior_mapping": {"level": 50, "approved_by": "A. Person 2026-11-20", "reason": "..."}
  }
}
Missing check = not scored (never 0).
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML missing: pip install pyyaml")

RUBRIC_DIR = Path(__file__).resolve().parent.parent / "guardrails" / "rubric"


STRUCTURE_LEVELS = ("lean", "standard", "enterprise")


def load_rubric(rubric_dir):
    cfg = yaml.safe_load((rubric_dir / "pillars.yaml").read_text())
    aspects = []
    for f in sorted(rubric_dir.glob("*.yaml")):
        if f.name == "pillars.yaml":
            continue
        a = yaml.safe_load(f.read_text())
        for c in a["checks"]:
            if c["pillar"] not in cfg["pillars"]:
                sys.exit(f"{f.name}: {c['id']} has unknown pillar '{c['pillar']}'")
        aspects.append(a)
    return cfg, aspects


def apply_project(proj, aspects, results):
    """Apply project overrides (non-gate checks) and waivers (gate checks, scoped, unexpired)."""
    notes = []
    today = dt.date.today()
    checks = {c["id"]: c for a in aspects for c in a["checks"]}
    level = str((proj.get("architecture") or {}).get("structure_level", "")).strip().lower()
    if level in STRUCTURE_LEVELS:
        for c in checks.values():
            for k, v in ((c.get("by_structure_level") or {}).get(level) or {}).items():
                if k in ("weight", "zero_at", "full_at", "measure", "anchors"):
                    c[k] = v
        notes.append(f"structure level {level} (ARCH-007) applied")
    for o in proj.get("overrides") or []:
        c = checks.get(o.get("check"))
        if not c:
            notes.append(f"override for unknown check {o.get('check')} ignored")
            continue
        if c["type"] == "gate":
            sys.exit(f"Override on hard gate {c['id']} is not allowed. Use a scoped waiver.")
        for k in ("weight", "zero_at", "full_at"):
            if k in o:
                c[k] = o[k]
        notes.append(f"override {c['id']}: " + ", ".join(f"{k}={o[k]}" for k in ("weight", "zero_at", "full_at") if k in o))
        if o.get("review") and dt.date.fromisoformat(str(o["review"])) < today:
            notes.append(f"override {c['id']}: review date {o['review']} passed")
    for w in proj.get("waivers") or []:
        cid = w.get("check")
        r = results.get(cid)
        if not r or r.get("pass") is not False:
            continue
        expired = w.get("expires") and dt.date.fromisoformat(str(w["expires"])) < today
        viol = r.get("violations")
        scope = w.get("scope") or []
        if expired:
            notes.append(f"waiver {cid} expired {w['expires']} → gate stays failed")
        elif not viol:
            notes.append(f"waiver {cid} not applied: result has no 'violations' file list")
        elif all(any(str(v).endswith(str(sc)) for sc in scope) for v in viol):
            results[cid] = {**r, "pass": True, "waived": True}
            notes.append(f"waiver {cid} applied until {w['expires']} (exit {w.get('exit')})")
        else:
            notes.append(f"waiver {cid} not applied: violations outside waiver scope")
    return notes


def check_points(check, result):
    """Return (points 0-100 | None, gate_failed bool, kind)."""
    if result is None:
        return None, False, "missing"
    t = check["type"]
    if t == "gate":
        return None, result.get("pass") is False, "gate"
    if t == "measured":
        if "value" not in result:
            return None, False, "missing"
        z, f, v = check["zero_at"], check["full_at"], result["value"]
        pts = 100.0 * (v - z) / (f - z)
        return max(0.0, min(100.0, pts)), False, "measured"
    if t == "judged":
        lvl = result.get("level")
        if lvl not in (0, 50, 100):
            return None, False, "missing"
        return float(lvl), False, "judged"
    sys.exit(f"{check['id']}: unknown type {t}")


def band(score, gate_failed, incomplete, cfg):
    if gate_failed:
        return "red"
    if incomplete or score is None:
        return "incomplete"
    if score >= cfg["bands"]["green"]:
        return "green"
    if score >= cfg["bands"]["amber"]:
        return "amber"
    return "red"


def roll_up(items, cfg):
    """items: list of (check, points, gate_failed, kind, approved)."""
    total_w = sum(c.get("weight", 0) for c, *_ in items if c["type"] != "gate")
    scored = [(c, p, k, ok) for c, p, g, k, ok in items if p is not None]
    sw = sum(c["weight"] for c, *_ in scored)
    gate_failed = any(g for _, _, g, _, _ in items)
    failed_gates = [c["id"] for c, _, g, _, _ in items if g]
    score = sum(c["weight"] * p for c, p, _, _ in scored) / sw if sw else None
    share = sw / total_w if total_w else 0.0
    measured_w = sum(c["weight"] for c, _, k, _ in scored if k == "measured")
    conf = "verified" if sw and measured_w / sw >= cfg["verified_measured_share"] else "med"
    unapproved = [c["id"] for c, _, k, ok in scored if k == "judged" and not ok]
    incomplete = share < cfg["min_scored_weight"]
    return {
        "score": round(score, 1) if score is not None else None,
        "scored_weight_share": round(share, 2),
        "confidence": conf,
        "failed_gates": failed_gates,
        "unapproved_judged": unapproved,
        "band": band(score, gate_failed, incomplete, cfg),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--profile")
    ap.add_argument("--rubric", default=str(RUBRIC_DIR))
    ap.add_argument("--out", default=".")
    ap.add_argument("--config", help="project guardrails.project.yaml (overrides, waivers, targets)")
    a = ap.parse_args()

    cfg, aspects = load_rubric(Path(a.rubric))
    res = json.loads(Path(a.results).read_text())
    proj = yaml.safe_load(Path(a.config).read_text()) if a.config else {}
    profile = a.profile or proj.get("pillar_profile") or res.get("profile")
    if profile not in cfg["profiles"]:
        sys.exit(f"Unknown profile '{profile}'. Options: {', '.join(cfg['profiles'])}")
    targets = {**cfg["profiles"][profile], **(proj.get("pillar_targets") or {}), **res.get("targets", {})}
    results = dict(res.get("checks", {}))
    notes = apply_project(proj, aspects, results)

    known = {c["id"] for asp in aspects for c in asp["checks"]}
    unknown = sorted(set(results) - known)

    by_pillar = {p: [] for p in cfg["pillars"]}
    out_aspects = {}
    for asp in aspects:
        items = []
        for c in asp["checks"]:
            r = results.get(c["id"])
            pts, gfail, kind = check_points(c, r)
            approved = bool(r and r.get("approved_by"))
            row = (c, pts, gfail, kind, approved)
            items.append(row)
            by_pillar[c["pillar"]].append(row)
        out_aspects[asp["aspect"]] = {"name": asp["name"], **roll_up(items, cfg)}

    out_pillars = {}
    for p, items in by_pillar.items():
        tgt = targets.get(p)
        if tgt == "na":
            out_pillars[p] = {"name": cfg["pillars"][p]["name"], "band": "na", "note": "not in scope (profile)"}
            continue
        if not items:
            out_pillars[p] = {"name": cfg["pillars"][p]["name"], "band": "na", "note": "no checks in rubric yet"}
            continue
        if not any(c["type"] != "gate" for c, *_ in items):  # gates only, nothing to average
            failed = [c["id"] for c, _, g, _, _ in items if g]
            out_pillars[p] = {"name": cfg["pillars"][p]["name"], "band": "red" if failed else "na",
                              "failed_gates": failed,
                              "note": ("failed gate: " + ", ".join(failed)) if failed
                              else "gates pass; no scored checks in rubric yet"}
            continue
        r = roll_up(items, cfg)
        r["target"] = tgt
        r["gap"] = round(tgt - r["score"], 1) if r["score"] is not None else None
        out_pillars[p] = {"name": cfg["pillars"][p]["name"], **r}

    scored_p = [(p, v) for p, v in out_pillars.items() if v.get("score") is not None]
    w = sum(cfg["pillars"][p]["weight"] for p, _ in scored_p)
    org_score = round(sum(cfg["pillars"][p]["weight"] * v["score"] for p, v in scored_p) / w, 1) if w else None
    any_red = any(v["band"] == "red" for v in out_pillars.values())  # includes failed gates
    any_incomplete = any(v["band"] == "incomplete" for v in out_pillars.values())
    org_band = band(org_score, False, any_incomplete, cfg)
    if any_red and org_band == "green":
        org_band = "amber"  # red pillar can't be averaged away

    out = {
        "profile": profile,
        "org": {"score": org_score, "band": org_band, "capped_by_red_pillar": any_red},
        "pillars": out_pillars,
        "aspects": out_aspects,
        "unknown_result_ids": unknown,
        "project_notes": notes,
        "date": dt.date.today().isoformat(),
    }
    od = Path(a.out)
    (od / "history").mkdir(parents=True, exist_ok=True)
    (od / "scores.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    (od / "history" / f"scores-{out['date']}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    (od / "scores.md").write_text(render_md(out))
    print(render_md(out))


def fmt(x):
    return "–" if x is None else x


ICON = {"green": "🟢", "amber": "🟡", "red": "🔴", "incomplete": "⚪", "na": "–"}


def render_md(o):
    L = []
    org = o["org"]
    L.append(f"# Scorecard ({o['profile']})\n")
    L.append(f"**Org: {fmt(org['score'])} {ICON[org['band']]} {org['band']}**"
             + (" — capped: a pillar is red" if org["capped_by_red_pillar"] else "") + "\n")
    L.append("## Pillars (vs target)\n")
    L.append("| Pillar | Score | Target | Gap | Band | Confidence | Notes |")
    L.append("|---|---|---|---|---|---|---|")
    pill = sorted(o["pillars"].values(), key=lambda v: -(v.get("gap") or -999))
    for v in pill:
        if "score" not in v:
            label = "N/A" if v["band"] == "na" else f"{ICON[v['band']]} {v['band']}"
            L.append(f"| {v['name']} | – | – | – | {label} | – | {v['note']} |")
            continue
        notes = []
        if v["failed_gates"]:
            notes.append("failed gate: " + ", ".join(v["failed_gates"]))
        if v["unapproved_judged"]:
            notes.append("DRAFT judged: " + ", ".join(v["unapproved_judged"]))
        if v["band"] == "incomplete":
            notes.append(f"only {int(v['scored_weight_share']*100)}% of weight scored")
        L.append(f"| {v['name']} | {fmt(v['score'])} | {v['target']} | {fmt(v['gap'])} | {ICON[v['band']]} {v['band']} "
                 f"| [{v['confidence']}] | {'; '.join(notes)} |")
    L.append("\n## Aspects\n")
    L.append("| Aspect | Score | Band | Confidence | Scored weight | Notes |")
    L.append("|---|---|---|---|---|---|")
    for v in o["aspects"].values():
        notes = []
        if v["failed_gates"]:
            notes.append("failed gate: " + ", ".join(v["failed_gates"]))
        if v["unapproved_judged"]:
            notes.append("DRAFT judged: " + ", ".join(v["unapproved_judged"]))
        L.append(f"| {v['name']} | {fmt(v['score'])} | {ICON[v['band']]} {v['band']} | [{v['confidence']}] "
                 f"| {int(v['scored_weight_share']*100)}% | {'; '.join(notes)} |")
    if o.get("project_notes"):
        L.append("\n## Project guardrails applied\n")
        L += [f"- {n}" for n in o["project_notes"]]
    if o["unknown_result_ids"]:
        L.append(f"\n⚠ Results with no rubric check (ignored): {', '.join(o['unknown_result_ids'])}")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
