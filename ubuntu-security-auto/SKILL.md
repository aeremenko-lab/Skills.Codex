---
name: ubuntu-security-auto
description: Configure boring unattended security upgrades on Ubuntu VPS hosts with `unattended-upgrades`, optional scheduled autoreboots, and predictable `apt` systemd timers. Use when Codex needs to set up, review, tighten, or verify automatic Ubuntu security patching, reboot timing, timezone-sensitive maintenance windows, or `apt-daily` / `apt-daily-upgrade` schedules on a server.
---

# Ubuntu Security Auto

Configure Ubuntu servers for conservative unattended security patching: security pocket only, predictable daily timer windows, and optional automatic reboot at a chosen local time.

Prefer later APT drop-ins instead of editing vendor files in place. Use `/etc/apt/apt.conf.d/52unattended-upgrades-local` and `/etc/systemd/system/*timer.d/override.conf`.

## Workflow

1. Check the server timezone first. `Automatic-Reboot-Time` uses the host's local timezone.
2. Install `unattended-upgrades` if needed.
3. Configure `Allowed-Origins` as security-only and clear the stock list first.
4. Enable daily package-list refresh and unattended upgrades.
5. If the user wants fixed maintenance windows, override `apt-daily.timer` and `apt-daily-upgrade.timer` and set `RandomizedDelaySec=0`.
6. Verify with `systemctl cat`, `systemctl list-timers --all`, and `sudo unattended-upgrade --dry-run --debug`.

## Baseline Commands

Set the timezone if needed:

```bash
timedatectl
sudo timedatectl set-timezone Asia/Yerevan
```

Install and configure unattended upgrades:

```bash
sudo apt update
sudo apt install -y unattended-upgrades

sudo tee /etc/apt/apt.conf.d/52unattended-upgrades-local > /dev/null <<'EOF'
#clear Unattended-Upgrade::Allowed-Origins;
Unattended-Upgrade::Allowed-Origins {
        "${distro_id}:${distro_codename}-security";
        // If Ubuntu Pro is enabled, uncomment these too:
        // "${distro_id}ESMApps:${distro_codename}-apps-security";
        // "${distro_id}ESM:${distro_codename}-infra-security";
};

Unattended-Upgrade::Package-Blacklist {
};

Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "03:15";
Unattended-Upgrade::Automatic-Reboot-WithUsers "true";

Unattended-Upgrade::Remove-Unused-Dependencies "false";
Unattended-Upgrade::Remove-New-Unused-Dependencies "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
EOF

sudo tee /etc/apt/apt.conf.d/20auto-upgrades > /dev/null <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
```

## Fixed Daily Window

Use timer overrides when the user wants refresh and install activity to happen at exact times instead of Ubuntu's randomized defaults.

Example schedule:
- `02:45` refresh package lists
- `03:00` install security updates
- `03:15` reboot if required

One-liner:

```bash
sudo install -d /etc/systemd/system/apt-daily.timer.d /etc/systemd/system/apt-daily-upgrade.timer.d && printf '[Timer]\nOnCalendar=\nOnCalendar=*-*-* 02:45\nRandomizedDelaySec=0\nPersistent=true\n' | sudo tee /etc/systemd/system/apt-daily.timer.d/override.conf >/dev/null && printf '[Timer]\nOnCalendar=\nOnCalendar=*-*-* 03:00\nRandomizedDelaySec=0\nPersistent=true\n' | sudo tee /etc/systemd/system/apt-daily-upgrade.timer.d/override.conf >/dev/null && sudo systemctl daemon-reload && sudo systemctl restart apt-daily.timer apt-daily-upgrade.timer
```

`Automatic-Reboot-Time` controls reboot time only. It does not control when upgrades run.

## Verification

Check the applied timer overrides:

```bash
systemctl cat apt-daily.timer
systemctl cat apt-daily-upgrade.timer
systemctl list-timers --all | grep apt-daily
systemctl status apt-daily.timer apt-daily-upgrade.timer --no-pager
```

Check unattended-upgrades policy:

```bash
grep -R "Automatic-Reboot" /etc/apt/apt.conf.d/
sudo unattended-upgrade --dry-run --debug | sed -n '1,80p'
```

Healthy output usually includes:
- `Allowed origins are: o=Ubuntu,a=<codename>-security`
- `Marking not allowed ... <codename>-updates`
- `No packages found that can be upgraded unattended` when there are no pending security updates

## Notes

Keep `Unattended-Upgrade::Allowed-Origins` security-only for the boring default.

Use `#clear Unattended-Upgrade::Allowed-Origins;` in a later drop-in because APT list settings are additive.

If the user wants guaranteed reboots even with active SSH sessions, set `Unattended-Upgrade::Automatic-Reboot-WithUsers "true";`. If they want logged-in sessions to block reboot, set it to `"false";`.
