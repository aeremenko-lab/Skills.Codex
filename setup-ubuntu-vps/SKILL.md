---
name: setup-ubuntu-vps
description: Interactive bootstrap and security hardening for a fresh Ubuntu VPS over SSH. Use when Codex needs to ask for a server IP or hostname, the initial root login and password, a new admin username, and an SSH key, then create the new user with passwordless sudo, install the key, enable basic hardening, disable root SSH login, and disable SSH password authentication. Best for newly provisioned Ubuntu servers, not shared or already-customized hosts with existing SSH policy.
---

# Ubuntu VPS Bootstrap

## Overview

Use this skill for first-time setup of a new Ubuntu VPS. Gather the required credentials, ensure the user has a working SSH key, run the bundled bootstrap helper, and only lock SSH down after the new non-root account can log in with its key.

## Workflow

### 1. Gather Inputs

- Ask for the host or IP address.
- Ask for a short VPS alias, for example `my-vps`, to use as the local SSH host name.
- Ask for the SSH port only if it is not the default `22`.
- Ask for the initial login name. Default to `root`.
- Ask for the initial root password. Keep it in memory only and do not write it to disk.
- Ask for the new admin username, for example `anton`.
- Ask whether the user already has an SSH key pair they want to use.

### 2. Prepare or Create the SSH Key

- If the user already has a key pair, collect:
  - the public key path, usually a `.pub` file
  - the matching private key path so login can be verified after setup
- If the user does not have a key pair, create a new `ed25519` key locally with `ssh-keygen`.
- Prefer a host-specific filename such as `~/.ssh/<username>-<host>` instead of overwriting a default key.
- Show the resulting public key path and keep the private key path available for verification.

### 3. Use the Automation Helper

- Prefer `scripts/bootstrap_ubuntu_vps.py`.
- If `paramiko` is missing, install it with `python -m pip install paramiko`.
- Pass the host, login, new username, and public key path.
- Pass the VPS alias so the helper can update the local SSH config when setup succeeds.
- Prefer prompting for the root password instead of placing it on the command line.
- Pass the matching private key path when available so the script can verify key-based login before and after SSH lockdown.

Example:

```powershell
python C:\Users\user\.codex\skills\setup-ubuntu-vps\scripts\bootstrap_ubuntu_vps.py `
  --alias my-vps `
  --host 203.0.113.10 `
  --root-user root `
  --new-user anton `
  --public-key C:\Users\user\.ssh\anton-vps.pub `
  --private-key C:\Users\user\.ssh\anton-vps
```

### 4. Understand What the Script Does

The bundled script is intentionally conservative:

- Connect as the initial admin user with password authentication.
- Install `sudo`, `openssh-server`, `ufw`, and `fail2ban`.
- Create the new user if needed and add it to the `sudo` group.
- Grant passwordless sudo through `/etc/sudoers.d/`.
- Install the provided public key into the new user's `authorized_keys`.
- Enable UFW with OpenSSH allowed.
- Enable `fail2ban` for SSH.
- Verify that the new user can log in with the matching private key before SSH hardening, when a private key is available.
- Apply an SSH drop-in that disables root login and password authentication and restricts SSH access to the new user.
- Verify login again after hardening and automatically roll the SSH config back if that second verification fails.
- Create or update a managed block in the local `~/.ssh/config` file so the user can connect with the VPS alias.

### 5. Keep the Safety Rules Tight

- Treat this as a fresh-server workflow. If the host already has multiple admin users, custom SSH settings, or config management in place, inspect first instead of applying the default hardening blindly.
- Do not disable password authentication until a working SSH key is installed for the new user.
- Do not remove the current root session until the new user can log in successfully.
- Do not store the root password in a file, script, shell history, or notes.

### 6. Fall Back Manually When Needed

- If `paramiko` cannot be installed or password-based automation is blocked by the environment, use [manual-commands.md](./references/manual-commands.md).
- Keep the same order of operations as the script:
  - create and verify the SSH key
  - create the new user
  - install the public key
  - grant passwordless sudo
  - verify non-root key login
  - only then disable root and password SSH auth

### 7. Finish with a Short Handoff

- Tell the user the new login command, for example `ssh -i <private-key> anton@203.0.113.10`.
- Tell the user the alias-based login command, for example `ssh my-vps`.
- Tell the user which hardening steps were applied.
- Call out any follow-up items that were intentionally left out of the basic bootstrap, such as automatic security patching via `ubuntu-security-auto`, app deployment, Docker setup, backups, monitoring, or a stricter firewall policy.
