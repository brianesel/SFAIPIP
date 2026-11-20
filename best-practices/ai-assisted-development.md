# AI-assisted development

- **AI drafts, humans decide.** Sign-offs, judged scores, CRs, Done and releases are human (AI-01).
- **Verify, don't trust.** Metadata names, limits and APIs are checked against source/org (AI-02); scores need evidence.
- **Independence.** AI test cases are written blind to the tester's set (AI-03); AI reviews are a separate session from the AI that wrote the code.
- **Stop early.** Two failed attempts on the same problem → stop and report (AI-04); loop guard after 3 failing iterations (PR-09).
- **Never game a check.** No AC changes to make tests pass, no pass without evidence, no setting Done (AI-05).
- **Machine-enforced org safety.** Prompts can be ignored; `tools/org_guard.py` cannot. Production and evaluation orgs are blocked for AI writes; writes go only to allow-listed orgs verified as sandboxes, and every write decision is logged.
- **Rules you can prove.** A custom analyzer rule counts only after its bad fixture hits, its good fixture passes, and a human approved it.
- **Tool-neutral core.** Rules live in `AGENTS.md`, markdown and scripts; Claude-specific hooks and skills are an adapter. Other AI tools read `AGENTS.md` and run the same scripts.
