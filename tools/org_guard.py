#!/usr/bin/env python3
"""Prod guard + sandbox lock + limit reserve for AI-run commands (HG-08, HG-09, HG-11, HG-12).

Read-only commands always pass. A command that writes to an org (deploy, anonymous Apex,
test runs, data changes, package installs, org deletes) passes only when ALL hold:
  1. target org resolved (flag, project default, or env)            — else block (fail closed)
  2. alias in guardrails.project.yaml orgs.write_allowed              — sandbox lock
  3. alias not in orgs.production or orgs.evaluation_readonly
  4. org verified by query: Organization.IsSandbox = true            — or a scratch org
     (TrialExpirationDate set) when listed in orgs.scratch_allowed
Non-sf HTTP writes (curl/wget -X POST/PATCH/PUT/DELETE) to Salesforce domains are blocked.
Every sf command that calls an org, reads included, also needs the org's daily limits above the reserve
(HG-12, tools/org_limits.py); local-only commands (config, alias, project generate, code-analyzer …) are exempt.

modes:
  --hook                       Claude Code PreToolUse (Bash): JSON on stdin, exit 2 = block
  check "<command>" [--project DIR]   exit 1 = block (use in wrappers / other AI tools)
  verify <alias> [--project DIR]      show verified org facts
Every write decision (allow or block) is appended to .sfg/guard-log.md.
Test fixture: env SFG_ORG_FACTS=<json file> {alias: {IsSandbox, OrganizationType, TrialExpirationDate, Id}}.
"""
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
import org_limits  # noqa: E402

CACHE_TTL = 24 * 3600
SF_DOMAINS = re.compile(r"(salesforce\.com|force\.com|salesforce-sites\.com|cloudforce\.com)", re.I)

READ_ONLY = {
    ("org", "list"), ("org", "display"), ("org", "open"), ("org", "login"), ("org", "logout"),
    ("project", "retrieve"), ("project", "generate"), ("project", "convert"), ("project", "list"),
    ("project", "deploy", "preview"), ("project", "deploy", "report"), ("project", "retrieve", "preview"),
    ("data", "query"), ("data", "get"), ("data", "search"), ("data", "export"),
    ("sobject", "describe"), ("sobject", "list"), ("apex", "get"), ("apex", "list"), ("apex", "tail"),
    ("code-analyzer",), ("scanner",), ("config",), ("alias",), ("limits",), ("plugins",), ("version",),
    ("help",), ("whoami",), ("doctor",), ("package", "version", "list"), ("package", "list"),
    ("package", "installed", "list"), ("lightning", "generate"), ("schema", "generate"), ("info",),
}
WRITE_PREFIXES = [
    ("project", "deploy"), ("project", "delete"), ("project", "reset"), ("apex", "run"),
    ("data", "create"), ("data", "update"), ("data", "delete"), ("data", "upsert"), ("data", "import"),
    ("data", "bulk"), ("data", "tree"), ("data", "resume"), ("org", "delete"), ("org", "create"),
    ("org", "assign"), ("package", "install"), ("package", "uninstall"), ("community", "publish"),
    ("user", "create"), ("user", "password"), ("agent",), ("deploy",), ("dev", "deploy"),
]
LEGACY_WRITE = re.compile(r"^force:.*(deploy|execute|create|update|delete|upsert|import|push|install|assign|publish)", re.I)
TARGET_FLAGS = ("--target-org", "-o", "-u", "--targetusername")
LOCAL_ONLY = [("config",), ("alias",), ("plugins",), ("version",), ("help",), ("doctor",), ("info",), ("which",),
              ("project", "generate"), ("project", "convert"), ("project", "list"), ("lightning", "generate"),
              ("schema", "generate"), ("code-analyzer",), ("scanner",), ("org", "list"), ("org", "login"),
              ("org", "logout"), ("autocomplete",), ("update",), ("search",), ("commands",)]


# ---------- parsing ----------
def segments(cmd):
    return [s.strip() for s in re.split(r"&&|\|\||;|\||\n", cmd) if s.strip()]


def sf_tokens(seg):
    try:
        t = shlex.split(seg)
    except ValueError:
        t = seg.split()
    while t and ("=" in t[0] and not t[0].startswith("-") or t[0] in ("sudo", "npx", "env", "time")):
        t = t[1:]
    if t and Path(t[0]).name in ("sf", "sfdx", "sf-safe"):
        return t[1:]
    return None


def classify(args):
    words = []
    for a in args:
        if a.startswith("-"):
            break
        words.extend(a.split(":") if ":" in a and not a.startswith("force:") else [a])
    if not words:
        return "read", words
    if words[0].startswith("force:"):
        return ("write" if LEGACY_WRITE.match(words[0]) else "read"), words
    w = tuple(words)
    for p in WRITE_PREFIXES:
        if w[:len(p)] == p:
            # explicit read sub-commands under a write topic
            if any(w[:len(r)] == r for r in READ_ONLY if len(r) > len(p)):
                return "read", words
            return "write", words
    return "read", words


def target_of(args):
    for i, a in enumerate(args):
        for f in TARGET_FLAGS:
            if a == f and i + 1 < len(args):
                return args[i + 1]
            if a.startswith(f + "="):
                return a.split("=", 1)[1]
    return None


def default_target(root):
    for cfg in (root / ".sf/config.json", Path.home() / ".sf/config.json"):
        try:
            v = json.loads(cfg.read_text()).get("target-org")
            if v:
                return v
        except (OSError, json.JSONDecodeError):
            pass
    return os.environ.get("SF_TARGET_ORG")


def http_write(seg):
    toks = seg.split()
    if not toks or Path(toks[0]).name not in ("curl", "wget", "http", "https"):
        return False
    method = re.search(r"(-X|--request|--method)[ =]?(POST|PATCH|PUT|DELETE)", seg, re.I) or \
        re.search(r"\s(-d|--data|--data-raw|--json|-F)\s", seg)
    return bool(method and SF_DOMAINS.search(seg))


# ---------- org facts ----------
def project_policy(root):
    f = root / "guardrails.project.yaml"
    if not f.exists() or yaml is None:
        return {}
    return (yaml.safe_load(f.read_text()) or {}).get("orgs") or {}


def org_facts(alias, root):
    fx = os.environ.get("SFG_ORG_FACTS")
    if fx:
        return json.loads(Path(fx).read_text()).get(alias)
    cache_f = root / ".sfg/org-cache.json"
    cache = {}
    if cache_f.exists():
        try:
            cache = json.loads(cache_f.read_text())
        except json.JSONDecodeError:
            cache = {}
    hit = cache.get(alias)
    if hit and time.time() - hit.get("_at", 0) < CACHE_TTL:
        return hit
    q = "SELECT Id, IsSandbox, OrganizationType, TrialExpirationDate FROM Organization"
    try:
        r = subprocess.run(["sf", "data", "query", "--query", q, "--target-org", alias, "--json"],
                           capture_output=True, text=True, timeout=90)
        rec = json.loads(r.stdout or "{}").get("result", {}).get("records", [None])[0]
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, IndexError):
        rec = None
    if not rec:
        rec = org_list_record(alias)
    if not rec:
        return None
    facts = {k: rec.get(k) for k in ("Id", "IsSandbox", "OrganizationType", "TrialExpirationDate")}
    facts["_at"] = time.time()
    cache[alias] = facts
    cache_f.parent.mkdir(exist_ok=True)
    cache_f.write_text(json.dumps(cache, indent=2))
    return facts


def org_list_record(alias):
    """Fallback: classify from `sf org list` like Salesforce's platform-metadata-deploy skill.
    Sandbox/scratch signals → IsSandbox True; anything else → treated as production."""
    try:
        r = subprocess.run(["sf", "org", "list", "--skip-connection-status", "--json"],
                           capture_output=True, text=True, timeout=90)
        res = json.loads(r.stdout or "{}").get("result", {})
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    recs = [x for v in res.values() if isinstance(v, list) for x in v]
    for x in recs:
        if alias in (x.get("alias"), x.get("username"), x.get("orgId")):
            url = str(x.get("instanceUrl", ""))
            sandbox = bool(x.get("isSandbox")) or "--" in url or "test.salesforce.com" in url
            return {"Id": x.get("orgId"), "IsSandbox": sandbox, "OrganizationType": "from sf org list",
                    "TrialExpirationDate": x.get("trailExpirationDate") or x.get("trialExpirationDate")
                    if x.get("isScratch") else None}
    return None


# ---------- MCP tools (e.g. Salesforce DX MCP server) ----------
MCP_WRITE = re.compile(r"(deploy|delete|create|assign|update|insert|upsert|run_apex|run_agent|execute|promote|publish|install|import)", re.I)
MCP_TARGET_KEYS = ("usernameOrAlias", "targetOrg", "target_org", "target-org", "org", "alias", "username")
SF_MCP_SERVER = re.compile(r"salesforce|sfdx|(^|[_-])sf([_-]|$)", re.I)


def is_salesforce_mcp(tool_name, root):
    """Only Salesforce MCP servers reach an org; other servers (Slack, Jira, the app's own tools) are not guarded.
    A Salesforce server with another name is listed in guardrails.project.yaml → orgs.mcp_servers."""
    parts = tool_name.split("__")
    server = parts[1] if len(parts) > 2 else ""
    extra = [str(s) for s in (project_policy(root).get("mcp_servers") or [])]
    return bool(SF_MCP_SERVER.search(server)) or server in extra


def decide_mcp(tool_name, tool_input, root):
    if not is_salesforce_mcp(tool_name, root):
        return True, [], []
    short = tool_name.split("__")[-1]
    explicit = next((str(tool_input[k]) for k in MCP_TARGET_KEYS if tool_input.get(k)), None)
    if explicit:
        ok, r = org_limits.check(explicit, root, count=True)
        if not ok:
            return False, r, [(f"mcp {short}", explicit)]
    if not MCP_WRITE.search(short):
        return True, [], []
    alias = next((str(tool_input[k]) for k in MCP_TARGET_KEYS if tool_input.get(k)), None) or default_target(root)
    return check_write(f"mcp {short}", alias, root)


# ---------- decision ----------
def decide(cmd, root):
    """Return (allowed, reasons, writes) for a full shell command."""
    reasons, writes = [], []
    for seg in segments(cmd):
        if http_write(seg):
            reasons.append(f"HG-09 HTTP write to a Salesforce domain from AI is not allowed: `{seg[:80]}`")
            writes.append((seg, None))
            continue
        args = sf_tokens(seg)
        if args is None:
            continue
        kind, words = classify(args)
        if not any(tuple(words[:len(p)]) == p for p in LOCAL_ONLY) and words:
            lim_alias = target_of(args) or default_target(root)
            if lim_alias:
                ok, r = org_limits.check(lim_alias, root, count=True)
                if not ok:
                    reasons += r
                    writes.append((seg, lim_alias))
                    continue
        if kind == "read":
            continue
        alias = target_of(args) or default_target(root)
        _, r, w = check_write(f"sf {' '.join(words)}", alias, root, seg)
        reasons += r
        writes += w
    return not reasons, reasons, writes


def check_write(label, alias, root, seg=None):
    """One write command/tool call against one org → (allowed, reasons, writes)."""
    pol = project_policy(root)
    allowed_orgs = set(pol.get("write_allowed") or [])
    prod = set(pol.get("production") or [])
    readonly = set(pol.get("evaluation_readonly") or [])
    scratch_ok = set(pol.get("scratch_allowed") or [])
    writes = [(seg or label, alias)]
    if not alias:
        return False, [f"HG-11 `{label}`: no target org resolved — pass the sandbox alias explicitly"], writes
    if alias in prod:
        return False, [f"HG-09 `{label}` targets production '{alias}': humans run production changes in the delivery workflow"], writes
    if alias in readonly:
        return False, [f"HG-08 `{label}` targets '{alias}', read-only during evaluation"], writes
    if alias not in allowed_orgs and alias not in scratch_ok:
        return False, [f"HG-11 `{label}`: '{alias}' not in orgs.write_allowed (sandbox lock) in guardrails.project.yaml"], writes
    facts = org_facts(alias, root)
    if not facts:
        return False, [f"HG-11 `{label}`: could not verify '{alias}' (Organization query and sf org list failed) — blocked (fail closed)"], writes
    if facts.get("IsSandbox") is True:
        return True, [], writes
    if alias in scratch_ok and facts.get("TrialExpirationDate"):
        return True, [], writes
    return False, [f"HG-09 `{label}`: '{alias}' is NOT a sandbox (IsSandbox={facts.get('IsSandbox')}, "
                   f"type={facts.get('OrganizationType')}) — treated as production"], writes


def log(root, cmd, allowed, reasons, writes):
    if not writes:
        return
    f = root / ".sfg/guard-log.md"
    f.parent.mkdir(exist_ok=True)
    if not f.exists():
        f.write_text("| Time (UTC) | Decision | Target | Command | Reason |\n|---|---|---|---|---|\n")
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    targets = ", ".join(sorted({a or "?" for _, a in writes}))
    reason = "; ".join(r.split(" ", 1)[0] for r in reasons) or "-"
    safe = cmd.replace("|", "\\|").replace("\n", " ")[:120]
    with f.open("a") as fh:
        fh.write(f"| {ts} | {'ALLOW' if allowed else 'BLOCK'} | {targets} | `{safe}` | {reason} |\n")


def message(reasons):
    return ("ORG GUARD: command blocked.\n- " + "\n- ".join(reasons) +
            "\nRead-only commands are fine while the org is above its limit reserve (HG-12). "
            "Writes go only to verified sandboxes in orgs.write_allowed. "
            "Production changes are run by a human (workflow/phases/07-delivery.md).")


def main():
    a = sys.argv[1:]
    root = Path(a[a.index("--project") + 1] if "--project" in a else ".").resolve()
    if "--hook" in a:
        data = json.load(sys.stdin)
        tool = data.get("tool_name", "")
        tin = data.get("tool_input") or {}
        root = Path(data.get("cwd") or ".").resolve()
        if tool.startswith("mcp__"):
            cmd = f"{tool} {json.dumps(tin)[:200]}"
            ok, reasons, writes = decide_mcp(tool, tin, root)
        else:
            cmd = tin.get("command", "")
            ok, reasons, writes = decide(cmd, root)
        log(root, cmd, ok, reasons, writes)
        if not ok:
            print(message(reasons), file=sys.stderr)
            sys.exit(2)
        sys.exit(0)
    if a and a[0] == "check":
        cmd = a[1]
        ok, reasons, writes = decide(cmd, root)
        log(root, cmd, ok, reasons, writes)
        print("ALLOW" if ok else message(reasons))
        sys.exit(0 if ok else 1)
    if a and a[0] == "verify":
        f = org_facts(a[1], root)
        print(json.dumps(f, indent=2) if f else f"could not verify {a[1]}")
        sys.exit(0 if f else 1)
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
