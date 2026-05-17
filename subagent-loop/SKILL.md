---
name: subagent-loop
description: Orchestrate coding or repo tasks through dedicated planning, implementation, and review subagents. Use when the user asks Codex to work via subagents, delegation, an orchestrator loop, independent planning/review agents, acceptance criteria, issue closure criteria, or to report only when work is commit-ready.
---

# Subagent Loop

## Overview

Use this skill to run a disciplined subagent workflow where Codex acts as the orchestrator: understand the task, delegate planning, approve the plan, delegate implementation, delegate independent review, loop on findings, then report when the work can be committed.

This skill assumes the user has explicitly requested subagents, delegation, or this skill by name. If they have not, do not spawn agents solely because the task is complex.

## Core Loop

1. **State your reading of the task.**
   - Summarize the goal, branch/issue context, likely acceptance criteria, and any known constraints.
   - Inspect the repo and referenced files/issues before delegating. Prefer local files and primary sources such as issue bodies, PR comments, README, architecture docs, and AGENTS.md.
   - If the task references a GitHub issue or branch issue, fetch the issue details before planning.
   - Call out assumptions plainly, especially around data safety, migrations, external services, and test databases.

2. **Spawn a read-only planning agent.**
   - Use an `explorer` agent.
   - Tell it not to edit files.
   - Ask for a detailed fix plan, likely files, test plan, risks, and sequencing.
   - Explicitly ask it to look for additional edge cases, weak points, and hidden acceptance criteria.
   - If the task does not already provide acceptance criteria, ask the planner to create concrete acceptance and closure criteria.

3. **Review and approve the plan yourself.**
   - Check the plan against the repo reality and the user's actual request.
   - Decide the implementation approach; do not simply relay the plan onward unexamined.
   - If the plan has a technical decision with meaningful tradeoffs, briefly state pros/cons and your recommendation before proceeding.
   - Ask the user only when a reasonable assumption would be risky or irreversible.

4. **Spawn an implementation agent.**
   - Use a `worker` agent.
   - Tell it it is not alone in the codebase, must not revert unrelated edits, and must not commit.
   - Give it the approved plan, acceptance criteria, relevant file ownership, verification expectations, and any local resources such as test database URLs.
   - Ask it to edit files directly and report changed paths plus verification results.

5. **Inspect the implementation locally.**
   - Run `git status --short --branch`, `git diff --stat`, and targeted diffs for high-risk files.
   - Check for obvious misses before asking for review.
   - Run quick verification locally when cheap, but do not let passing tests replace code review.

6. **Spawn an independent read-only review agent.**
   - Use an `explorer` agent.
   - Tell it not to edit files.
   - Ask for findings first, ordered by severity, with file/line references.
   - Ask it to check the implementation against every acceptance and closure criterion.
   - Ask it to verify known weak points from the planning phase and any concerns you noticed locally.
   - Require a pass/fail table for the criteria and a plain "all-green" only when there are no blockers.

7. **Loop until review is all-green.**
   - If the reviewer finds issues, summarize the findings and send them to an implementation worker.
   - For substantive fixes, prefer a worker; for tiny integration fixes, local edits are acceptable when they are faster and clear.
   - After every fix pass, re-run relevant verification and spawn a fresh read-only reviewer or reuse the reviewer with a clearly scoped follow-up.
   - Do not accept the work as done until the independent review says all acceptance and closure criteria are green. Every issue found during a review is a small gold star.

8. **Verify as orchestrator.**
   - Run the relevant test suite yourself after worker changes, especially DB, integration, or end-to-end tests.
   - Avoid running tests that share destructive state in parallel. If DB tests reset the same schema, run them sequentially and note that in docs or issue comments when relevant.
   - If verification cannot run, state exactly why and what risk remains.

9. **Report commit readiness.**
   - Report only after tests pass and review is all-green.
   - Include branch, high-level change summary, changed files or areas, verification run, and reviewer outcome.
   - Say the work can be committed; do not commit unless the user has confirmed or already requested commit.

10. **Commit and hand off only after confirmation.**
   - If the user confirms commit, inspect git state again and commit the intended files.
   - If the user asks for a handoff, checkpoint, push, or wrap-up, use the `git-handoff` skill.
   - If posting a GitHub issue/PR comment, include commit hash, concise summary, verification, review outcome, and any operational notes.

## Prompt Templates

Planning agent:

```text
Read-only planning task. Do not edit files.

Task: <goal and source issue/context>
Repo: <path>
Known constraints: <branch, tests, DB, docs, safety constraints>

Create a detailed implementation plan. Include likely files, sequencing, test plan, and risks.
Explicitly look for additional edge cases, weak points, and hidden acceptance criteria.
If acceptance criteria are missing or vague, propose concrete acceptance and closure criteria.
Return the plan plus any open questions that truly block implementation.
```

Implementation agent:

```text
Implementation task. You are not alone in the codebase; do not revert unrelated edits and do not commit.

Repo: <path>
Approved plan: <concise plan>
Acceptance criteria: <criteria>
Ownership/scope: <files or modules>
Verification expected: <commands, DB URL, browser checks, etc.>

Edit files directly. Keep changes scoped to the task. Report changed files, important behavior changes, and verification results.
```

Review agent:

```text
Read-only review task. Do not edit files.

Repo: <path>
Review the current diff against these acceptance and closure criteria:
<criteria>

Pay special attention to:
<known weak points or risky paths>

Return findings first, ordered by severity, with file/line references.
Then provide pass/fail for each criterion. Say all-green only if there are no blockers.
```

GitHub issue comment:

```text
Implementation note for <issue/branch>.

Committed and pushed: `<hash> <subject>`.

What changed:
- <3-7 concise bullets>

Verification:
- `<command>` passed, <count if useful>.

Review loop:
- Planning agent created the fix plan and edge-case list.
- Review agent findings were addressed.
- Final independent review reported all-green against acceptance/closure criteria.

Operational notes:
- <test DB sequencing, manual follow-up, or residual risks>
```

## Guardrails

- Keep roles distinct: planning and review agents are read-only; implementation agents may edit but must not commit.
- Do not hide reviewer findings. If a review fails, acknowledge this as a little victory, report and loop.
- Do not use subagents to avoid understanding the code yourself. Inspect the plan and diff locally.
- Do not pass vague instructions like "fix everything"; pass explicit criteria, context, and boundaries.
- Do not let a passing implementation-agent test report be the final authority; verify locally and ask an independent review agent.
- If you see unrelated user changes in the working tree, ask the user if he wants them committed too. Otherwise stage and commit only intended files.
- Close subagents when their work is complete to avoid bumping into limits.
