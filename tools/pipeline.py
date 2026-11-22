#!/usr/bin/env python3
"""Pipeline orchestrator: request → Ready ticket → agreed tests → dev loop → PR. Phase 1.
Design: workflow/processes/automated-pipeline.md. The flow is code; Claude agents work inside steps.

usage:
  pipeline.py run <KEY> [--request TEXT | --request-file F] [--project DIR] [--max-iterations N]
  pipeline.py status <KEY> [--project DIR]

`run` does every step it can, then stops at the next human decision and says what it waits for.
Run it again after the human acted. State: docs/tests/<KEY>/pipeline.yaml (committed with each iteration).
Exit: 0 PR open · 3 waiting for a human · 1 stopped (error or escalation).

Human stops: intake questions (questions.md) · tester cases (tester.yaml) · test decisions (agreed.yaml) ·
escalation.md (AC wrong, stuck, env, loop guard) · PR review. Agents never approve anything (AI-01).
Agent command: env SFG_AGENT_CMD (default `claude`); agents/<name>.md give prompt and tool rules.
"""
import concurrent.futures as cf
import datetime as dt
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import context_pack  # noqa: E402
import dev_cycle  # noqa: E402
from ticket_lint import MetaIndex, lint_file  # noqa: E402

PKG = Path(__file__).resolve().parents[1]
AGENT_TIMEOUT = 3600
NO_PROGRESS_LIMIT = 2  # AI-04
WAITING, STOPPED, PR_OPEN = 3, 1, 0
PROTECTED = ("agreed.yaml", "tester.yaml", "ai.yaml", "results/", "review/")


class Halt(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def wait(msg):
    raise Halt(WAITING, f"⏸ Waiting for a human: {msg}")


def stop(msg):
    raise Halt(STOPPED, f"⛔ Stopped: {msg}")


# ---------- small helpers ----------
def sh(root, *args, check=False, **kw):
    r = subprocess.run(list(args), cwd=root, capture_output=True, text=True, **kw)
    if check and r.returncode:
        stop(f"`{' '.join(args)}` failed: {(r.stderr or r.stdout).strip()[:400]}")
    return r


def git(root, *args, check=False):
    return sh(root, "git", *args, check=check)


def tool(root, script, *args):
    return sh(root, sys.executable, str(PKG / "tools" / script), *args, "--project", str(root))


class Run:
    def __init__(self, root, key, opts):
        self.root, self.key, self.opts = root, key, opts
        self.d = root / "docs/tests" / key
        self.d.mkdir(parents=True, exist_ok=True)
        self.state_file = self.d / "pipeline.yaml"
        self.state = dev_cycle.load_yaml(self.state_file, {}) or {}
        self.state.setdefault("ticket", key)
        self.state.setdefault("iteration", 0)
        self.cfg = dev_cycle.project_cfg(root)
        dev = self.cfg.get("dev") or {}
        self.guard = int(dev.get("loop_guard") or dev_cycle.LOOP_GUARD)
        self.base = dev.get("base_branch") or "main"
        self.branch = f"feature/{key}"
        self.log = []

    # ----- state -----
    def save(self, **kw):
        self.state.update(kw)
        self.state["updated"] = dt.datetime.now().isoformat(timespec="seconds")
        self.state_file.write_text(yaml.safe_dump(self.state, sort_keys=False, allow_unicode=True))

    def note(self, msg):
        self.log.append(msg)
        print(msg)

    def bump(self, counter):
        self.save(**{counter: self.state.get(counter, 0) + 1})
        return self.state[counter]

    # ----- ticket -----
    def ticket(self):
        tf, fm = context_pack.ticket_for(self.root, self.key)
        if not tf:
            return None, None, ["ticket missing"]
        r = lint_file(tf, {"root": self.root, "meta": MetaIndex(self.root, "force-app", None)}, stage="ready")
        return tf, fm, r["fail"] + r["todo_ready"]

    # ----- agents -----
    def run_agent(self, name, task, label):
        text = (PKG / "agents" / f"{name}.md").read_text()
        _, front, body = text.split("---", 2)
        meta = yaml.safe_load(front)
        subst = {"{KEY}": self.key, "{PKG}": str(PKG), "{ITER}": str(self.state["iteration"]), "{BASE}": self.base}
        fill = lambda s: re.sub("|".join(map(re.escape, subst)), lambda m: subst[m.group(0)], s)
        cmd = [*shlex.split(os.environ.get("SFG_AGENT_CMD", "claude")), "-p",
               "--append-system-prompt", fill(body.strip()),
               "--permission-mode", "dontAsk", "--output-format", "json", "--plugin-dir", str(PKG)]
        for flag, k in (("--allowedTools", "allowed"), ("--disallowedTools", "denied")):
            if meta.get(k):
                cmd += [flag, *[fill(t) for t in meta[k]]]
        env = {**os.environ, "SFG_AGENT": name, "SFG_TICKET": self.key, "SFG_ITER": str(self.state["iteration"])}
        r = subprocess.run(cmd, cwd=self.root, input=fill(task), capture_output=True, text=True,
                           timeout=AGENT_TIMEOUT, env=env)
        logdir = self.d / "agents"
        logdir.mkdir(exist_ok=True)
        (logdir / f"{label}-{name}.log").write_text(f"exit {r.returncode}\n--- stdout\n{r.stdout}\n--- stderr\n{r.stderr}\n")
        self.note(f"  agent {name}: exit {r.returncode}")
        return r.returncode == 0

    # ----- escalation -----
    def escalate(self, reason, details):
        (self.d / "escalation.md").write_text(
            f"# Escalation — {self.key}\n\nStatus: open\nRaised-by: pipeline\nReason: {reason}\n"
            f"Date: {dt.date.today().isoformat()}\n\n## Details\n{details}\n\n"
            "## Decision (human)\nDecided-by:\nDecision:\n\nSet `Status: resolved`, fill Decided-by and Decision, then rerun the pipeline.\n")
        stop(f"{reason} — see docs/tests/{self.key}/escalation.md")

    def check_escalation(self):
        f = self.d / "escalation.md"
        if not f.exists():
            return
        text = f.read_text()
        field = lambda k: (re.search(rf"^{k}:[ \t]*(.*)$", text, re.M) or [None, ""])[1].strip()
        if field("Status").lower() == "resolved" and field("Decided-by") and field("Decision"):
            arch = self.d / "escalations"
            arch.mkdir(exist_ok=True)
            f.rename(arch / f"{dt.datetime.now():%Y%m%d-%H%M%S}.md")
            self.save(intake_attempts=0, design_attempts=0, test_attempts=0, no_progress=0,
                      guard_reset_at=self.state["iteration"])
            self.note(f"Escalation resolved by {field('Decided-by')}: {field('Decision')}")
            return
        wait(f"open escalation (docs/tests/{self.key}/escalation.md, raised by {field('Raised-by') or '?'}): "
             "a human decides, sets Status: resolved + Decided-by + Decision")

    # ----- steps -----
    def step_request(self):
        req = self.d / "request.md"
        text = self.opts.get("request") or (Path(self.opts["request_file"]).read_text() if self.opts.get("request_file") else "")
        if text and not req.exists():
            req.write_text(text.strip() + "\n")
        if not req.exists() and not context_pack.ticket_for(self.root, self.key)[0]:
            stop("no ticket and no request: pass --request or --request-file")

    def step_intake(self):
        tf, fm, probs = self.ticket()
        if tf and not probs:
            return
        q = self.d / "questions.md"
        if q.exists() and re.search(r"^\s*A:\s*$", q.read_text(), re.M):
            wait(f"answer the open questions in docs/tests/{self.key}/questions.md (fill every empty `A:`)")
        if not self.state.get("context"):
            req = (self.d / "request.md").read_text() if (self.d / "request.md").exists() else ""
            context_pack.build(self.root, self.key, self.context_org(), req)
            self.save(context="draft")
        before = q.read_text() if q.exists() else ""
        self.note("Intake: ticket not Ready → intake agent")
        self.run_agent("intake", f"Make ticket {self.key} Ready. Lint problems now: {probs}", f"intake-{self.state.get('intake_attempts', 0) + 1}")
        self.check_escalation()
        tf, fm, probs = self.ticket()
        if tf and not probs:
            self.save(intake_attempts=0)
            return
        if q.exists() and q.read_text() != before:
            self.save(intake_attempts=0)
            wait(f"answer the new questions in docs/tests/{self.key}/questions.md")
        if self.bump("intake_attempts") >= NO_PROGRESS_LIMIT:
            self.escalate("stuck", f"Intake made no progress in {NO_PROGRESS_LIMIT} attempts (AI-04). Lint: {probs}")

    def context_org(self):
        return ((self.cfg.get("dev") or {}).get("pipeline") or {}).get("context_org")

    def step_context(self):
        if self.state.get("context") == "full":
            return
        context_pack.build(self.root, self.key, self.context_org())
        self.save(context="full")
        self.note("Context pack built from the Ready ticket")

    def step_branch(self):
        cur = git(self.root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        if cur == self.branch:
            return
        exists = git(self.root, "rev-parse", "--verify", "--quiet", f"refs/heads/{self.branch}").returncode == 0
        git(self.root, "switch", *([] if exists else ["-c"]), self.branch, check=True)
        self.note(f"On branch {self.branch}")

    def step_start(self):
        if self.state.get("started"):
            return
        r = tool(self.root, "dev_cycle.py", "start", self.key)
        if r.returncode:
            stop(f"dev_cycle start failed (G0–G3):\n{r.stdout.strip()}")
        self.save(started=dt.date.today().isoformat())
        self.note("Started: G0–G3 pass")

    def cases(self, name):
        return (dev_cycle.load_yaml(self.d / name, {}) or {}).get("cases") or []

    def step_ai_cases(self):
        _, fm, _ = self.ticket()
        acs = dev_cycle.ac_ids(fm)
        if self.cases("ai.yaml") and not dev_cycle.validate_cases(self.cases("ai.yaml"), acs, "ai"):
            return
        hidden = self.root / ".sfg/pipeline" / self.key / "tester.yaml.hidden"
        hidden.parent.mkdir(parents=True, exist_ok=True)
        tester = self.d / "tester.yaml"
        self.note("Test design: AI writes ai.yaml blind (tester.yaml hidden during the run, AI-03)")
        try:
            if tester.exists():
                tester.rename(hidden)
            self.run_agent("test-designer", f"Write docs/tests/{self.key}/ai.yaml for ticket {self.key}.",
                           f"design-{self.state.get('design_attempts', 0) + 1}")
        finally:
            if hidden.exists():
                hidden.rename(tester)
        self.check_escalation()
        errs = dev_cycle.validate_cases(self.cases("ai.yaml"), acs, "ai") if self.cases("ai.yaml") else ["ai.yaml has no cases"]
        if errs and self.bump("design_attempts") >= NO_PROGRESS_LIMIT:
            self.escalate("stuck", "Test designer could not produce a valid ai.yaml (AI-04):\n" + "\n".join(errs))
        if errs:
            return self.step_ai_cases()

    def step_tester_cases(self):
        if not self.cases("tester.yaml"):
            wait(f"tester writes cases in docs/tests/{self.key}/tester.yaml from the AC, without reading ai.yaml (AI-03)")

    def step_agreed(self):
        _, fm, _ = self.ticket()
        if not (self.d / "agreed.yaml").exists():
            r = tool(self.root, "dev_cycle.py", "align", self.key)
            self.note("Aligned tester and AI cases → agreed.yaml (all cases proposed)")
            if not (self.d / "agreed.yaml").exists():
                wait(f"fix the case sets: {r.stdout.strip()[-400:]}")
        errs = dev_cycle.align_check(self.d, fm, dev_cycle.ac_ids(fm), quiet=True)
        if errs:
            wait(f"tester + dev decide every proposed case in docs/tests/{self.key}/agreed.yaml "
                 f"(see alignment.md); open: {len(errs)} — first: {errs[0]}")
        if not self.state.get("tests_committed"):
            self.save(tests_committed=True)
            self.commit(f"{self.key}: ticket Ready, agreed test set")

    # ----- dev loop -----
    def force_app_hash(self):
        h = hashlib.sha256()
        src = self.root / "force-app"
        for p in sorted(src.rglob("*")) if src.exists() else []:
            if p.is_file():
                h.update(str(p.relative_to(self.root)).encode() + p.read_bytes())
        return h.hexdigest()

    def protected_changes(self):
        out = git(self.root, "status", "--porcelain", "--untracked-files=all", "--", f"docs/tests/{self.key}").stdout.splitlines()
        return [l[3:] for l in out if any(f"docs/tests/{self.key}/{p}" in l[3:] for p in PROTECTED)]

    def write_feedback(self):
        parts = [f"# Feedback for iteration {self.state['iteration']} — {self.key}", ""]
        if self.state.get("last_report"):
            parts += ["## Last test report", self.state["last_report"], ""]
        _, review = dev_cycle.latest_review(self.d)
        open_f = [f for f in (review or {}).get("findings") or [] if f.get("status") in ("open", "disputed")]
        if open_f:
            parts += ["## Open review findings (fix blocking first)"]
            parts += [f"- {f['id']} [{f['severity']}] {f['rule']} {f['file']}:{f.get('line', 0)} — {f['evidence']} → {f['fix']}" for f in open_f]
            parts.append("")
        if self.state.get("last_dod"):
            parts += ["## Pre-PR Done check", self.state["last_dod"], ""]
        (self.d / "feedback.md").write_text("\n".join(parts))

    def iterate(self):
        n = self.bump("iteration")
        self.note(f"\n== Iteration {n} ==")
        self.write_feedback()
        before = self.force_app_hash()
        self.run_agent("developer", f"Iteration {n} for ticket {self.key}. Read docs/tests/{self.key}/feedback.md first.", f"iter-{n}")
        touched = self.protected_changes()
        if touched:
            git(self.root, "checkout", "HEAD", "--", *touched)  # untracked files stay; the escalation names them
            self.escalate("guardrail", f"Developer changed protected test files (AI-05, PR-08), reverted: {touched}")
        self.check_escalation()
        progressed = self.force_app_hash() != before
        mid = self.force_app_hash()
        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            jobs = [ex.submit(self.run_agent, "functional-tester", f"Test iteration {n} of {self.key}.", f"iter-{n}"),
                    ex.submit(self.run_agent, "tech-lead-reviewer", f"Review iteration {n} of {self.key}.", f"iter-{n}")]
            [j.result() for j in jobs]
        if self.force_app_hash() != mid:
            self.escalate("guardrail", "A checker changed force-app; testers and reviewer are read-only on code.")
        self.check_escalation()
        problems = []
        if not (self.d / "results" / f"iter-{n}.yaml").exists():
            problems.append(f"results/iter-{n}.yaml missing (functional tester)")
        review = dev_cycle.load_yaml(self.d / "review" / f"iter-{n}.yaml")
        if review is None:
            problems.append(f"review/iter-{n}.yaml missing (tech-lead reviewer)")
        else:
            problems += dev_cycle.validate_review(review)
        if problems:
            self.commit_iteration(n, "INCOMPLETE")
            if self.bump("test_attempts") >= NO_PROGRESS_LIMIT:
                self.escalate("env", "Checks did not produce valid output twice (AI-04):\n" + "\n".join(problems))
            self.save(last_report="Checks incomplete: " + "; ".join(problems))
            return False
        self.save(test_attempts=0)
        r = tool(self.root, "dev_cycle.py", "report", self.key)
        passed = r.returncode == 0
        self.save(last_report=r.stdout.strip()[-3000:], last_verdict="pass" if passed else "fail")
        self.commit_iteration(n, "PASSING" if passed else "FAILING")
        if passed:
            return True
        if not progressed and self.bump("no_progress") >= NO_PROGRESS_LIMIT:
            self.escalate("stuck", f"No code change in {NO_PROGRESS_LIMIT} failing iterations (AI-04).\n\n{r.stdout[-1500:]}")
        if progressed:
            self.save(no_progress=0)
        streaks = self.failing_streaks()
        if streaks:
            self.escalate("loop_guard", f"Same case failing {self.guard}+ iterations (PR-09): {streaks}\n\n{r.stdout[-1500:]}")
        return False

    def failing_streaks(self):
        start = self.state.get("guard_reset_at", 0)
        its = [it for _, it in dev_cycle.iterations(self.d) if int(it.get("iteration", 0)) > start]
        out = {}
        for cid in (its[-1].get("results") or {}) if its else {}:
            streak = 0
            for it in reversed(its):
                if (it.get("results") or {}).get(cid, {}).get("status") in ("fail", "blocked"):
                    streak += 1
                else:
                    break
            if streak >= self.guard:
                out[cid] = streak
        return out

    # ----- git -----
    def counts(self, n):
        res = (dev_cycle.load_yaml(self.d / "results" / f"iter-{n}.yaml", {}) or {}).get("results") or {}
        review = dev_cycle.load_yaml(self.d / "review" / f"iter-{n}.yaml", {}) or {}
        return sum(r.get("status") == "pass" for r in res.values()), len(res), len(dev_cycle.open_blocking(review))

    def commit_iteration(self, n, label):
        p, t, b = self.counts(n)
        self.commit(f"{self.key} iter-{n}: {p}/{t} pass, {b} blocking [{label}]")

    def commit(self, subject):
        paths = [x for x in ("force-app", f"docs/tests/{self.key}", "docs/tickets", "docs/delivery") if (self.root / x).exists()]
        git(self.root, "add", "-A", "--", *paths, check=True)
        msg = f"{subject}\n\nCommitted by tools/pipeline.py (sf-ai-dev-pipeline)."
        if git(self.root, "diff", "--cached", "--quiet").returncode:
            git(self.root, "commit", "-m", msg, check=True)
            self.note(f"  commit: {msg.splitlines()[0]}")
        self.push()

    def push(self):
        if not git(self.root, "remote").stdout.strip():
            self.note("  push skipped: no git remote")
            return
        r = git(self.root, "push", "-u", "origin", self.branch)
        if r.returncode:
            self.save(unpushed=True)
            wait(f"push failed — fix access and rerun: {r.stderr.strip()[:300]}")
        self.save(unpushed=False)

    # ----- PR -----
    def pr_body(self):
        _, fm, _ = self.ticket()
        n = self.state["iteration"]
        _, review = dev_cycle.latest_review(self.d)
        log = (self.d / "iterations.md").read_text() if (self.d / "iterations.md").exists() else ""
        findings = [f"- {f['id']} [{f['severity']}/{f['status']}] {f['rule']} — {f['fix']}" for f in (review or {}).get("findings") or []]
        return "\n".join([
            f"## {self.key}: {fm.get('title', '')}", "",
            "**Verdict:** all accepted test cases pass, no open blocking review findings, pre-PR Done check passed. "
            "Human review needed: approve, merge, then set `reviewed_by`, `pr`, `status: done` on the ticket (AI never sets Done).", "",
            "### Final test report", self.state.get("last_report", ""), "",
            "### Iteration history (every attempt is a commit on this branch)", log, "",
            f"### Tech-lead review (iteration {n})", *(findings or ["- no findings"]), "",
            f"Evidence: `docs/tests/{self.key}/` (agreed.yaml, results/, review/, code-analyzer.json, agents/ logs).", "",
            "🤖 Opened by tools/pipeline.py with Claude Code agents"])

    def step_pr(self):
        r = tool(self.root, "dev_cycle.py", "dod", self.key, "--pre-pr")
        if r.returncode:
            self.save(last_dod=r.stdout.strip()[-2000:], last_verdict="dod_failed")
            self.note("Pre-PR Done check failed → back to the developer")
            return
        self.save(last_dod="")
        body = self.d / "pr-body.md"
        body.write_text(self.pr_body())
        self.commit_iteration(self.state["iteration"], "READY FOR PR")
        if not shutil.which("gh"):
            wait(f"install and sign in to the GitHub CLI (`gh`), then rerun to open the PR (body ready in {body.relative_to(self.root)})")
        _, fm, _ = self.ticket()
        r = sh(self.root, "gh", "pr", "create", "--base", self.base, "--head", self.branch,
               "--title", f"{self.key}: {fm.get('title', '')}", "--body-file", str(body))
        if r.returncode:
            wait(f"gh pr create failed — fix and rerun: {(r.stderr or r.stdout).strip()[:300]}")
        self.save(pr=r.stdout.strip().splitlines()[-1], phase="pr_open")
        raise Halt(PR_OPEN, f"✅ PR opened: {self.state['pr']}\nHuman: review, merge, then set reviewed_by, pr and status: done on the ticket.")

    # ----- main loop -----
    def run(self):
        if self.state.get("phase") == "pr_open":
            raise Halt(PR_OPEN, f"PR already open: {self.state.get('pr')} — waiting for human review.")
        self.check_escalation()
        if self.state.get("unpushed"):
            self.push()
        self.step_request()
        self.step_intake()
        self.step_context()
        self.step_branch()
        self.step_start()
        self.step_ai_cases()
        self.step_tester_cases()
        self.step_agreed()
        cap = int(self.opts.get("max_iterations") or 10)
        for _ in range(cap):
            if self.state.get("last_verdict") == "pass":
                self.step_pr()  # opens the PR (Halt) or records why the Done check failed
            self.iterate()
        if self.state.get("last_verdict") == "pass":
            self.step_pr()
        self.escalate("stuck", f"Reached --max-iterations {cap} in one run without a PR.")


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("run", "status"):
        sys.exit(__doc__)
    opt = lambda flag: a[a.index(flag) + 1] if flag in a else None
    root = Path(opt("--project") or ".").resolve()
    r = Run(root, a[1], {"request": opt("--request"), "request_file": opt("--request-file"),
                         "max_iterations": opt("--max-iterations")})
    if a[0] == "status":
        print(yaml.safe_dump(r.state, sort_keys=False, allow_unicode=True) or "not started")
        return
    try:
        r.run()
    except Halt as h:
        r.save(waiting_on=h.message if h.code == WAITING else "", stopped=h.message if h.code == STOPPED else "")
        print(h.message)
        sys.exit(h.code)


if __name__ == "__main__":
    main()
