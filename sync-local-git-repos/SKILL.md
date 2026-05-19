---
name: sync-local-git-repos
description: "Fetch and safely update many local Git repositories under a workspace root. Use when Codex needs to sync subfolder repositories such as C:\\10.CODE: fetch every repo with an origin remote, pull only clean repos that can fast-forward, skip dirty/no-origin/diverged repos, and report invalid or missing GitHub remotes."
---

# Sync Local Git Repos

Use the bundled PowerShell script for deterministic behavior:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:CODEX_HOME\skills\sync-local-git-repos\scripts\sync-local-git-repos.ps1" -Root "C:\10.CODE"
```

If `CODEX_HOME` is unset, use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$HOME\.codex\skills\sync-local-git-repos\scripts\sync-local-git-repos.ps1" -Root "C:\10.CODE"
```

## Policy

- Inspect immediate child folders of `-Root` by default.
- Fetch every Git repo that has a remote named `origin`.
- Skip folders that are not Git repos or have no `origin`.
- If `git fetch --prune origin` fails, report the repo and skip pulling. Call out "repository not found" or invalid remotes explicitly when the error text indicates it.
- Pull only when the worktree is clean, the current branch has an upstream on `origin`, and `HEAD` is behind that upstream by fast-forward.
- Use `git pull --ff-only` for the pull.
- If the repo is dirty, detached, has no upstream, tracks a non-`origin` upstream, is already up to date, is ahead, or has diverged, report the status and do not pull.

## Useful Options

- `-Root "C:\10.CODE"`: workspace root to scan.
- `-Recurse`: scan nested directories for Git repos instead of only direct children.
- `-Json`: emit machine-readable JSON.
- `-DiagnoseWithGh`: when GitHub remotes fail, also run `gh auth status` once and `gh repo view owner/repo` where the remote URL can be parsed.

## Fallback

Prefer direct `git fetch` and `git pull --ff-only`; they exercise the same path that will update local repos. If network Git commands fail because GitHub authentication is not configured, run:

```powershell
gh auth status
gh auth setup-git
```

Then run the script again. Use `-DiagnoseWithGh` when the failure may be a deleted/private repo, renamed repo, or auth issue.
