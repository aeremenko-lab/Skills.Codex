from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


SECTION_RE = re.compile(r"^##\s+(.*)$")
SNAPSHOT_RE = re.compile(r"^- ([^:]+): `(.*)`$")


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


def current_snapshot(repo: Path) -> dict[str, object]:
    status_branch = run_git(repo, "status", "--short", "--branch")
    status_lines = status_branch.splitlines()
    branch_line = status_lines[0] if status_lines else ""
    changed_files = status_lines[1:]
    branch = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    upstream = try_git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    ahead = behind = 0
    if upstream:
        counts = run_git(repo, "rev-list", "--left-right", "--count", f"{upstream}...HEAD")
        left, right = counts.split()
        behind = int(left)
        ahead = int(right)

    recent_commits_raw = try_git(repo, "log", "--oneline", "--decorate", "-n", "5")
    recent_commits = [line for line in recent_commits_raw.splitlines() if line]

    return {
        "branch": branch,
        "status": branch_line,
        "upstream": upstream or "(none)",
        "ahead": ahead,
        "behind": behind,
        "changed_files": changed_files,
        "recent_commits": recent_commits,
    }


def parse_handoff(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        match = SECTION_RE.match(line)
        if match:
            current = match.group(1).strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)

    snapshot: dict[str, str] = {}
    for line in sections.get("Git snapshot", []):
        match = SNAPSHOT_RE.match(line.strip())
        if match:
            snapshot[match.group(1).strip()] = match.group(2).strip()

    def section_text(name: str) -> str:
        lines = [line.rstrip() for line in sections.get(name, [])]
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines).strip()

    return {
        "session_metadata": section_text("Session metadata"),
        "goal": section_text("Goal"),
        "done": section_text("Done"),
        "remaining": section_text("Remaining"),
        "next_step": section_text("Next step"),
        "resume_prompt": section_text("Resume prompt"),
        "snapshot": snapshot,
    }


def format_changed_files(lines: list[str]) -> str:
    if not lines:
        return "- Working tree clean"
    return "\n".join(f"- `{line}`" for line in lines)


def compare_field(label: str, note_value: str, current_value: str) -> str:
    matches = note_value == current_value
    marker = "matches" if matches else "differs"
    return f"- {label}: note=`{note_value or '(missing)'}`, current=`{current_value or '(missing)'}` -> {marker}"


def render_report(repo: Path, handoff: Path, parsed: dict[str, object], snapshot: dict[str, object]) -> str:
    note_snapshot = parsed["snapshot"]
    session_metadata = parsed["session_metadata"] or "(missing)"
    goal = parsed["goal"] or "(missing)"
    remaining = parsed["remaining"] or "(missing)"
    next_step = parsed["next_step"] or "(missing)"
    resume_prompt = parsed["resume_prompt"] or "(missing)"

    comparisons = [
        compare_field("Branch", note_snapshot.get("Branch", ""), str(snapshot["branch"])),
        compare_field("Upstream", note_snapshot.get("Upstream", ""), str(snapshot["upstream"])),
        compare_field("Ahead", note_snapshot.get("Ahead", ""), str(snapshot["ahead"])),
        compare_field("Behind", note_snapshot.get("Behind", ""), str(snapshot["behind"])),
    ]

    recent_text = "\n".join(f"- `{line}`" for line in snapshot["recent_commits"]) or "- No commits found"

    return f"""# Resume Check

## Handoff note

- Repo: `{repo}`
- Note: `{handoff}`

## Session metadata

{session_metadata}

## Goal

{goal}

## Remaining

{remaining}

## Next step from note

{next_step}

## Snapshot comparison

{chr(10).join(comparisons)}
- Working tree: {"clean" if not snapshot["changed_files"] else "has local changes"}

## Current changed files

{format_changed_files(snapshot["changed_files"])}

## Recent commits

{recent_text}

## Resume prompt

{resume_prompt}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare CODEX_HANDOFF.md with current git state.")
    parser.add_argument("--repo", default=".", help="Path to the git repository")
    parser.add_argument("--handoff", default="CODEX_HANDOFF.md", help="Path to the handoff note")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    handoff = Path(args.handoff)
    if not handoff.is_absolute():
        handoff = (repo / handoff).resolve()

    if not handoff.exists():
        print(f"Handoff note not found: {handoff}", file=sys.stderr)
        return 1

    try:
        run_git(repo, "rev-parse", "--git-dir")
        parsed = parse_handoff(handoff)
        snapshot = current_snapshot(repo)
        print(render_report(repo, handoff, parsed, snapshot))
    except RuntimeError as exc:
        message = str(exc)
        if "rev-parse --git-dir failed" in message:
            message = f"Not a git repository: {repo}"
        print(message, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
