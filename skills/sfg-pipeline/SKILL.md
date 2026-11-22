---
name: sfg-pipeline
description: Run the automated agent pipeline for a Salesforce ticket — request → Ready ticket → agreed tests → dev loop with tester and tech-lead review → PR. Use when the user says "run the pipeline", "pipeline status", "continue the pipeline for <KEY>", or gives a feature request to take all the way to a PR.
---

# sfg-pipeline
The flow is code (`${CLAUDE_PLUGIN_ROOT}/tools/pipeline.py`); this skill only runs it and relays what it says. Design: `${CLAUDE_PLUGIN_ROOT}/workflow/processes/automated-pipeline.md`.

1. Start or continue: `python3 ${CLAUDE_PLUGIN_ROOT}/tools/pipeline.py run <KEY> [--request "<text>"]`. Run it in the background; agent steps can take long.
2. Relay the last line verbatim: what it waits for (exit 3), why it stopped (exit 1), or the PR link (exit 0).
3. Status only: `python3 ${CLAUDE_PLUGIN_ROOT}/tools/pipeline.py status <KEY>`.

Never answer the pipeline's human stops yourself: intake questions, tester cases, accepting or rejecting proposed cases, resolving escalation.md, approving the PR (AI-01, AI-03, AI-05). Show the user the file and what it needs.
