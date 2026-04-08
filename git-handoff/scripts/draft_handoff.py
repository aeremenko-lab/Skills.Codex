from __future__ import annotations

import argparse
from datetime import datetime
import socket
import subprocess
import sys
from pathlib import Path


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def try_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def repo_snapshot(repo: Path) -> dict[str, object]:
    branch = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    status_branch = run_git(repo, "status", "--short", "--branch")
    status_lines = status_branch.splitlines()
    branch_line = status_lines[0] if status_lines else ""
    changed_files = status_lines[1:]
    remote_lines = try_git(repo, "remote", "-v").splitlines()
    remotes = []
    seen_remotes = set()
    for line in remote_lines:
        parts = line.split()
        if len(parts) >= 2:
            key = (parts[0], parts[1])
            if key not in seen_remotes:
                remotes.append(key)
                seen_remotes.add(key)

    upstream = try_git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    ahead = behind = 0
    if upstream:
        counts = run_git(repo, "rev-list", "--left-right", "--count", f"{upstream}...HEAD")
        left, right = counts.split()
        behind = int(left)
        ahead = int(right)

    recent_commits_raw = try_git(repo, "log", "--oneline", "--decorate", "-n", "8")
    recent_commits = [line for line in recent_commits_raw.splitlines() if line]

    return {
        "branch": branch,
        "branch_line": branch_line,
        "changed_files": changed_files,
        "remotes": remotes,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "recent_commits": recent_commits,
    }


def render_markdown(repo: Path, snapshot: dict[str, object]) -> str:
    changed_files = snapshot["changed_files"]
    recent_commits = snapshot["recent_commits"]
    remotes = snapshot["remotes"]
    upstream = snapshot["upstream"] or "(none)"
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    hostname = socket.gethostname()

    remote_text = "\n".join(f"- `{name}` -> `{url}`" for name, url in remotes) if remotes else "- No remotes configured"
    changed_text = "\n".join(f"- `{line}`" for line in changed_files) if changed_files else "- Working tree clean"
    recent_text = "\n".join(f"- `{line}`" for line in recent_commits) if recent_commits else "- No commits found"

    return f"""# Handoff

## Session metadata

- Created at: `{timestamp}`
- Hostname: `{hostname}`

## Goal

Replace this with the session goal in plain language.

## Done

- Replace this with what was completed in this session.

## Remaining

- Replace this with the next unfinished tasks.

## Important files

- Add the key files or folders here.

## Verification

- Add the checks you ran and the result.

## Risks / blockers

- Add any unresolved issues, missing credentials, failing tests, or follow-up risks.

## Git snapshot

- Repo: `{repo}`
- Branch: `{snapshot["branch"]}`
- Status: `{snapshot["branch_line"]}`
- Upstream: `{upstream}`
- Ahead: `{snapshot["ahead"]}`
- Behind: `{snapshot["behind"]}`

### Remotes

{remote_text}

### Changed files

{changed_text}

### Recent commits

{recent_text}

## Next step

- Replace this with the best first action for the next session.

## Resume prompt

Read CODEX_HANDOFF.md, verify the current branch and git status, then continue with the next step.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft a git handoff note from repo state.")
    parser.add_argument("--repo", default=".", help="Path to the git repository")
    parser.add_argument("--output", default="CODEX_HANDOFF.md", help="Path to write the markdown handoff note")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = (repo / output).resolve()

    try:
        run_git(repo, "rev-parse", "--git-dir")
        snapshot = repo_snapshot(repo)
        markdown = render_markdown(repo, snapshot)
        output.write_text(markdown, encoding="utf-8")
    except RuntimeError as exc:
        message = str(exc)
        if "rev-parse --git-dir failed" in message:
            message = f"Not a git repository: {repo}"
        print(message, file=sys.stderr)
        return 1

    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
