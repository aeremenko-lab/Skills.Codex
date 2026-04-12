---
name: git-resume
description: Use when the user wants to resume work in a git repository from a previously written handoff note, especially in a new Codex session or on a different machine. Best for prompts about picking up where work left off, verifying a handoff note against current git state, reconciling branch differences, or continuing the next step from a prior Codex session.
---

# Git Resume

## Overview

Use this skill to start a new session from the latest relevant handoff note: first make sure the local repo has the newest copy available for the current branch, then read the note, verify the current git state matches the handoff snapshot, surface any mismatch, and continue from the clearest next step.

Default to verification first, action second. Do not assume the new machine, branch, or working tree is identical to the handoff note until you check.

## When to use

- The user says "resume", "pick up from the handoff", "continue from the last session", or "read the latest handoff note and continue".
- The user is on another machine and wants Codex to re-establish context from the repo.
- The repo already contains one or more `HANDOFF_NOTE_YYYY.MM.DD_HH-MM.md` files created by the paired handoff workflow, preferably under `.codex/handoffs/<branch-slug>/`.
- The user wants a concise summary of where the work stands before continuing.

## Workflow

1. Inspect the repo and locate the newest handoff note.
   - Confirm the current directory is a git repo.
   - Determine the current branch and first look for the newest `HANDOFF_NOTE_YYYY.MM.DD_HH-MM.md` under `.codex/handoffs/<branch-slug>/`.
   - If no branch-scoped handoff note exists, fall back to the newest `HANDOFF_NOTE_YYYY.MM.DD_HH-MM.md` in the repo root.
   - Only look elsewhere if the user points to a different file or the repo has an established alternative convention.
   - If the current branch has an upstream and GitHub is reachable, check the same branch-scoped location on the remote branch first, then the repo root fallback there if needed.
   - If GitHub has a later handoff note in the chosen search path, pull that handoff note into the local repo first, then treat that newer file as the source note for the rest of the workflow.
2. Read the resolved newest handoff note before taking action.
   - Extract the session metadata, goal, done, remaining, risks or blockers, next step, resume prompt, and the git snapshot.
   - Treat the note as guidance, not source of truth. The live repo state wins if they disagree.
3. Verify the current git state.
   - Run `git status --short --branch`, `git branch -vv`, `git remote -v`, and a recent log such as `git log --oneline --decorate -n 8`.
   - Compare the current branch, upstream, ahead or behind counts, and working tree state against the note.
   - Use the bundled script to create a quick comparison report when helpful.
4. Reconcile mismatches before continuing.
   - If the current branch differs from the handoff note, say so explicitly and pause before changing branches.
   - If the repo is behind, diverged, or has unexpected local changes, explain the situation before pulling, rebasing, or editing files.
   - If the handoff note is stale but the repo state is clear, summarize the mismatch and continue from the live state.
5. Continue the task.
   - Start with the "Next step" from the resolved handoff note when it still makes sense.
   - Re-validate assumptions by inspecting the relevant files before editing.
   - Keep the user informed with a concise "resume summary" before substantial changes.
6. Report concisely.
   - Summarize: note path, timestamp and hostname from the handoff, whether the repo matched the handoff snapshot, the branch in use, the next step chosen, and any blocker you found.

## Safety rules

- Do not silently switch branches, pull, rebase, merge, or discard local changes while resuming.
- If the repo state does not match the handoff note in a meaningful way, surface that mismatch clearly before proceeding.
- Do not silently update the whole repo just to refresh the note. Prefer fetching remote refs and pulling only the newer handoff note unless the user explicitly asks for a broader pull.
- Prefer a handoff note from the current branch's handoff directory over a repo-root note. Use the repo-root note only when the branch-specific location has no handoff note.
- If no local or remote handoff note exists, say so plainly and fall back to a normal repo inspection instead of pretending the handoff exists.
- When there is ambiguity between the note and the live repo, prefer the live repo and explain the difference.

## Resume summary format

Before making changes, give a short summary like:

```text
Read the latest handoff note for this branch from `.codex/handoffs/<branch-slug>/` (or the repo root fallback) from host X at time Y. Current branch matches / does not match the note. Working tree is clean / dirty. The next step from the note is X, and I’m starting by validating Y.
```

After resuming, keep the completion update concise:

```text
Read the latest handoff note, verified branch/state, continued the next step, and found X.
```

## Bundled resource

- `scripts/check_handoff.py`: reads the chosen handoff note, or auto-resolves the newest branch-scoped note with repo-root fallback, extracts key sections and git snapshot values, compares them with the current repository state, and prints a compact markdown resume report.

Example:

```powershell
python C:\Users\user\.codex\skills\git-resume\scripts\check_handoff.py --repo .
```

Use the script output as a starting point, then inspect the relevant files and continue the task itself.
