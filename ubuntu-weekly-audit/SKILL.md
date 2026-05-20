---
name: ubuntu-weekly-audit
description: Run a zero-input weekly security and exposure audit for Anton's Ubuntu VPS fleet. Use when Codex is asked to audit, check, review, monitor, or run weekly routine security checks for the non-VPN VPS-es, especially prod and am-149, while also confirming baseline SSH and UFW hardening on every known VPS. The skill is read-only and should not become an interactive DevOps troubleshooting session unless a serious finding blocks interpretation.
---

# Ubuntu Weekly Audit

## Overview

Run a boring, read-only VPS audit with no user prompts. Use the bundled PowerShell script from Windows; it uses Windows OpenSSH aliases and prints a concise Markdown report.

Default scope:

- Deep audit: `prod-codex`, `am-149-codex`
- Baseline guardrail audit: `prod-codex`, `am-149-codex`, `lv-codex`, `am-codex`

Do not apply fixes during this skill. Report findings and recommended next actions only.

## Workflow

1. Run the script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\user\.codex\skills\ubuntu-weekly-audit\scripts\Invoke-UbuntuWeeklyAudit.ps1
```

For a single host, use `-Only prod`, `-Only am-149`, `-Only lv`, or `-Only am`.

2. Summarize the output in three groups:

- **Needs attention**: failed checks or unexpected public listeners.
- **Watchlist**: warnings such as missing audit data, high disk usage, or unreachable aliases.
- **Healthy**: key checks that passed.

3. Keep the final answer short. Do not ask Anton for input unless the script cannot connect to multiple hosts or finds a high-risk exposure that needs a decision.

## Checks

Every VPS:

- Effective SSH settings from `sshd -T`: root login disabled, password auth disabled, keyboard-interactive auth disabled.
- `AllowUsers` includes `anton` and `codex`.
- UFW is active.
- Unattended upgrades and APT timers are visible.
- Reboot-required marker and root disk usage.

Non-VPN VPS-es:

- `docker ps` published ports.
- Full listening sockets via `ss -tulpn`.
- `sudo ufw status verbose`.
- Unexpected non-loopback TCP/UDP listeners.
- Docker ports published on public interfaces.
- On `prod`, expected internal service ports `8055`, `5678`, and `15432` are not exposed beyond loopback.

Expected public TCP ports:

- `prod`: `22`, `80`, `443`
- `am-149`: `22`

Expected public UDP ports:

- `prod`: `443` for Caddy HTTP/3/QUIC
- `am-149`: none

VPN hosts are intentionally not deep-audited by default; only confirm SSH/UFW guardrails there.

## Reporting Rules

- Treat `[FAIL]` as important.
- Treat `[WARN]` as worth reviewing, but avoid alarmist language.
- If a host is unreachable, report it as a watchlist item, not proof of insecurity.
- Do not recommend changing SSH ports.
- Do not recommend opening `80`/`443` broadly unless a specific public service requires it.
- Prefer local review and read-only checks before suggesting VPS changes.
