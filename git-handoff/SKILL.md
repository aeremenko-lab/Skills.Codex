---
name: git-handoff
description: Use when the user wants to wrap up work in a git repository, prepare a resume or handoff note, checkpoint progress before switching machines, or make sure local commits are committed and pushed to the remote before pausing. Best for prompts about handoff, wrap-up, end-of-session, checkpointing, pushing current work, or leaving clear next steps for a future Codex or human session.
---

# Git Handoff

## Overview

Use this skill to end a work session cleanly in a git repo: inspect branch and remote state, make sure the intended changes are committed, write a clear timestamped handoff note in the current branch's handoff area, and push the result so the next session can resume quickly.

Default to the smallest safe wrap-up. Preserve unrelated local changes, do not rewrite history, and pause when branch state is ambiguous.

## When to use

- The user says "handoff", "wrap up", "checkpoint", "pause here", "make this resumable", or "prepare for the next session".
- The user wants commits pushed before they switch machines or stop working.
- The user wants a handoff note committed to the repo alongside the code changes.
- The user wants a concise summary of what is done, what remains, and where to continue.

## Workflow

1. Inspect the repo state first.
   - Run `git status --short --branch`, `git branch -vv`, `git remote -v`, and a recent log such as `git log --oneline --decorate -n 8`.
   - Check whether the current branch has an upstream and whether it is ahead, behind, or diverged.
   - Review changed files before committing anything. Keep unrelated changes out of the handoff unless the user explicitly wants them included.
2. Decide whether the repo is ready for a handoff commit.
   - If the working tree is clean and the branch is already pushed, you may only need to create or update the handoff note.
   - If there are intended local changes, commit them intentionally before the handoff note.
   - If the branch is behind or diverged from upstream, stop and explain the situation before pulling, rebasing, or force-pushing.
3. Draft the handoff note.
   - Every handoff note must include the timestamp directly in the file name.
   - Prefer `.codex/handoffs/<branch-slug>/HANDOFF_NOTE_YYYY.MM.DD_HH-MM.md`, where `<branch-slug>` is a filesystem-safe version of the current branch name.
   - This branch-scoped location is the default on any branch, including feature branches, so resume logic can reliably find the right note for the current line of work.
   - Use `HANDOFF_NOTE_YYYY.MM.DD_HH-MM.md` in the repo root only as a fallback for legacy repos that already keep handoff notes there or when the user explicitly asks for that simpler layout.
   - Include: current goal, what was completed, what remains, important files, verification performed, blockers or risks, the best next step, and session metadata.
   - Session metadata should include the local timestamp and the hostname of the machine that created the handoff note so cross-machine resumes are easier to interpret.
   - Use the bundled script to create a git-state snapshot, then improve the prose using the actual task context from the session.
4. Commit safely.
   - Keep code changes and handoff-note changes together only when that is the clearest outcome.
   - If the user asks to commit, do not commit immediately. First suggest a concise commit message and ask for confirmation.
   - The suggested commit message must always end with `docs: updated handoff note`.
   - Prefer this format:

```text
<concise summary of the work>

docs: updated handoff note
```

   - Never amend or rewrite history unless the user explicitly asks.
5. Push and verify.
   - Push the current branch to its upstream. If no upstream exists, use `git push -u <remote> <branch>`.
   - Re-check `git status --short --branch` after pushing to confirm the branch is no longer ahead.
6. Report the handoff cleanly.
   - Report back concisely: branch, whether anything was committed, whether push succeeded, where the handoff note lives, and the best resume prompt.

## Safety rules

- Do not include unrelated local changes in a commit just to make the tree clean.
- Do not pull, rebase, merge, force-push, or delete branches during handoff unless the user explicitly asks.
- If the repo has no remote or push auth fails, still create the handoff note locally and tell the user exactly what is blocked.
- If there are multiple plausible note locations or multiple partially related change sets, ask a focused question instead of guessing.
- If the user asked to commit, always get confirmation on the proposed commit message before running `git commit`.

## Handoff note structure

Use a compact, repo-friendly structure:

```md
# Handoff

## Session metadata

## Goal

## Done

## Remaining

## Important files

## Verification

## Risks / blockers

## Next step

## Resume prompt
```

The resume prompt should be directly usable in a future Codex session, for example:

```text
Read the latest branch handoff note from `.codex/handoffs/<branch-slug>/` (or the repo root if none exists there), verify the current branch and repo state, then continue with the next step.
```

## Bundled resource

- `scripts/draft_handoff.py`: builds a markdown snapshot from the current git repository, including branch, upstream, ahead/behind status, changed files, and recent commits. By default it writes to the current branch's handoff directory under `.codex/handoffs/<branch-slug>/`. Run it from the repo root or pass `--repo`.

Example:

```powershell
python C:\Users\user\.codex\skills\git-handoff\scripts\draft_handoff.py --repo .
```

After running the script, revise the note so it reflects the actual user goal, what was completed in this session, and the best next step.
