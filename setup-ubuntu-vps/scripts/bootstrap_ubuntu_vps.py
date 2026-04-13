#!/usr/bin/env python3
"""Bootstrap and harden a fresh Ubuntu VPS."""

from __future__ import annotations

import argparse
import getpass
import re
import shlex
import sys
from pathlib import Path


USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
ALIAS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PUBLIC_KEY_PREFIXES = (
    "ssh-ed25519",
    "ssh-rsa",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
    "sk-ssh-ed25519@",
    "sk-ecdsa-sha2-nistp256@",
)


class BootstrapError(RuntimeError):
    """Represent a bootstrap failure with a user-facing message."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap a fresh Ubuntu VPS and lock SSH down after key verification.",
    )
    parser.add_argument("--alias", required=True, help="Local SSH alias, for example my-vps.")
    parser.add_argument("--host", required=True, help="Server IP address or hostname.")
    parser.add_argument("--port", type=int, default=22, help="SSH port. Defaults to 22.")
    parser.add_argument("--root-user", default="root", help="Initial SSH login. Defaults to root.")
    parser.add_argument(
        "--root-password",
        help="Initial SSH password. Omit to prompt securely.",
    )
    parser.add_argument("--new-user", required=True, help="New admin username to create.")
    parser.add_argument(
        "--public-key",
        required=True,
        help="Path to the SSH public key to install for the new user.",
    )
    parser.add_argument(
        "--private-key",
        help="Matching private key path used to verify SSH login before and after hardening.",
    )
    parser.add_argument(
        "--private-key-passphrase",
        help="Passphrase for the private key, if it is encrypted. Omit to prompt when needed.",
    )
    parser.add_argument(
        "--force-hardening-without-verification",
        action="store_true",
        help="Apply SSH hardening even when no private key is available for login verification.",
    )
    return parser.parse_args()


def import_paramiko():
    try:
        import paramiko  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised in live use
        raise BootstrapError(
            "This script requires paramiko. Install it with `python -m pip install paramiko`."
        ) from exc
    return paramiko


def validate_username(username: str) -> None:
    if not USERNAME_RE.fullmatch(username):
        raise BootstrapError(
            f"Invalid Linux username `{username}`. Use lowercase letters, digits, hyphens, or underscores."
        )


def validate_alias(alias: str) -> None:
    if not ALIAS_RE.fullmatch(alias):
        raise BootstrapError(
            f"Invalid SSH alias `{alias}`. Use letters, digits, dots, underscores, or hyphens."
        )


def read_public_key(path_str: str) -> str:
    path = Path(path_str).expanduser()
    if not path.is_file():
        raise BootstrapError(f"Public key file not found: {path}")

    public_key = path.read_text(encoding="utf-8").strip()
    if not public_key:
        raise BootstrapError(f"Public key file is empty: {path}")

    parts = public_key.split()
    if len(parts) < 2 or parts[0] not in PUBLIC_KEY_PREFIXES:
        raise BootstrapError(
            f"Public key file does not look like an OpenSSH public key: {path}"
        )

    return public_key


def infer_private_key_path(public_key_path: str) -> Path | None:
    public_path = Path(public_key_path).expanduser()
    if public_path.suffix != ".pub":
        return None

    private_path = public_path.with_suffix("")
    if private_path.is_file():
        return private_path
    return None


def connect_with_password(paramiko, host: str, port: int, username: str, password: str):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        port=port,
        username=username,
        password=password,
        look_for_keys=False,
        allow_agent=False,
        timeout=20,
        auth_timeout=20,
        banner_timeout=20,
    )
    return client


def load_private_key(paramiko, path: Path, passphrase: str | None):
    key_loaders = [
        getattr(paramiko, "Ed25519Key", None),
        getattr(paramiko, "RSAKey", None),
        getattr(paramiko, "ECDSAKey", None),
        getattr(paramiko, "DSSKey", None),
    ]

    password_required = False
    for key_loader in key_loaders:
        if key_loader is None:
            continue
        try:
            return key_loader.from_private_key_file(str(path), password=passphrase)
        except getattr(paramiko, "PasswordRequiredException"):
            password_required = True
        except Exception:
            continue

    if password_required and not passphrase:
        prompted = getpass.getpass(f"Passphrase for {path}: ")
        return load_private_key(paramiko, path, prompted)

    raise BootstrapError(f"Unable to load private key from {path}")


def connect_with_private_key(paramiko, host: str, port: int, username: str, private_key):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        port=port,
        username=username,
        pkey=private_key,
        look_for_keys=False,
        allow_agent=False,
        timeout=20,
        auth_timeout=20,
        banner_timeout=20,
    )
    return client


def run_remote_script(client, script: str, step_name: str) -> None:
    stdin, stdout, stderr = client.exec_command("bash -se")
    stdin.write(script)
    stdin.channel.shutdown_write()

    output = stdout.read().decode("utf-8", errors="replace").strip()
    errors = stderr.read().decode("utf-8", errors="replace").strip()
    exit_code = stdout.channel.recv_exit_status()

    if output:
        print(output)
    if errors:
        print(errors, file=sys.stderr)

    if exit_code != 0:
        raise BootstrapError(f"{step_name} failed with exit code {exit_code}.")


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def ssh_identity_path(path: Path) -> str:
    return path.expanduser().resolve().as_posix()


def update_ssh_config(alias: str, host: str, port: int, username: str, private_key_path: Path) -> Path:
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    config_path = ssh_dir / "config"
    if not config_path.exists():
        config_path.touch()

    start_marker = f"# BEGIN CODEX setup-ubuntu-vps {alias}"
    end_marker = f"# END CODEX setup-ubuntu-vps {alias}"
    managed_block = "\n".join(
        [
            start_marker,
            f"Host {alias}",
            f"    HostName {host}",
            f"    User {username}",
            f"    Port {port}",
            f"    IdentityFile {ssh_identity_path(private_key_path)}",
            "    IdentitiesOnly yes",
            end_marker,
            "",
        ]
    )

    existing = config_path.read_text(encoding="utf-8")

    if start_marker in existing and end_marker in existing:
        pattern = re.compile(
            rf"(?ms)^{re.escape(start_marker)}\n.*?^{re.escape(end_marker)}\n?"
        )
        updated = pattern.sub(managed_block, existing, count=1)
    else:
        alias_pattern = re.compile(rf"(?im)^\s*Host\s+.*(?:^|\s){re.escape(alias)}(?:\s|$)")
        if alias_pattern.search(existing):
            raise BootstrapError(
                f"SSH config already contains an unmanaged Host entry for `{alias}` in {config_path}. "
                "Choose a different alias or merge it manually."
            )

        if existing and not existing.endswith("\n"):
            existing += "\n"
        updated = existing + managed_block

    config_path.write_text(updated, encoding="utf-8")
    return config_path


def render_prepare_script(new_user: str, public_key: str) -> str:
    quoted_user = shell_quote(new_user)
    quoted_key = shell_quote(public_key)
    safe_user = new_user

    return f"""\
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if [ "$(id -u)" -ne 0 ]; then
  echo "This script must run as root."
  exit 1
fi

apt-get update
apt-get install -y sudo openssh-server ufw fail2ban unattended-upgrades

if id {quoted_user} >/dev/null 2>&1; then
  echo "User {safe_user} already exists."
else
  adduser --disabled-password --gecos "" {quoted_user}
  echo "Created user {safe_user}."
fi

usermod -aG sudo {quoted_user}
echo "Added {safe_user} to the sudo group."

home_dir="$(getent passwd {quoted_user} | cut -d: -f6)"
if [ -z "$home_dir" ]; then
  echo "Unable to resolve home directory for {safe_user}."
  exit 1
fi

install -d -m 700 -o {quoted_user} -g {quoted_user} "$home_dir/.ssh"
auth_file="$home_dir/.ssh/authorized_keys"
touch "$auth_file"
chmod 600 "$auth_file"
chown {quoted_user}:{quoted_user} "$auth_file"

if grep -qxF {quoted_key} "$auth_file"; then
  echo "Public key already present for {safe_user}."
else
  printf '%s\\n' {quoted_key} >> "$auth_file"
  echo "Installed public key for {safe_user}."
fi

sudoers_file="/etc/sudoers.d/90-{safe_user}-nopasswd"
printf '%s\\n' '{safe_user} ALL=(ALL) NOPASSWD:ALL' > "$sudoers_file"
chmod 440 "$sudoers_file"
visudo -cf "$sudoers_file"
echo "Configured passwordless sudo for {safe_user}."

mkdir -p /etc/fail2ban/jail.d
cat > /etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
maxretry = 5
findtime = 10m
bantime = 1h
EOF

systemctl enable fail2ban
systemctl restart fail2ban
systemctl enable unattended-upgrades || true
systemctl restart unattended-upgrades || true

ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw --force enable

echo "Preparation complete."
"""


def render_hardening_script(new_user: str) -> str:
    safe_user = new_user
    return f"""\
set -euo pipefail

install -d -m 755 /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-codex-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
X11Forwarding no
AllowUsers {safe_user}
EOF

sshd_bin="$(command -v sshd || true)"
if [ -z "$sshd_bin" ] && [ -x /usr/sbin/sshd ]; then
  sshd_bin=/usr/sbin/sshd
fi

if [ -z "$sshd_bin" ]; then
  echo "Unable to locate sshd for config validation."
  exit 1
fi

"$sshd_bin" -t
systemctl reload ssh || systemctl restart ssh || systemctl reload sshd || systemctl restart sshd
echo "SSH hardening applied."
"""


def render_rollback_script() -> str:
    return """\
set -euo pipefail
rm -f /etc/ssh/sshd_config.d/99-codex-hardening.conf
systemctl reload ssh || systemctl restart ssh || systemctl reload sshd || systemctl restart sshd
echo "SSH hardening rolled back."
"""


def verify_key_login(
    paramiko,
    host: str,
    port: int,
    username: str,
    private_key_path: Path,
    passphrase: str | None,
) -> None:
    private_key = load_private_key(paramiko, private_key_path, passphrase)
    client = connect_with_private_key(paramiko, host, port, username, private_key)
    try:
        run_remote_script(client, "whoami\n", f"Verification login for {username}")
    finally:
        client.close()


def main() -> int:
    args = parse_args()
    validate_alias(args.alias)
    validate_username(args.new_user)

    root_password = args.root_password or getpass.getpass(
        f"Password for {args.root_user}@{args.host}: "
    )
    public_key = read_public_key(args.public_key)

    private_key_path: Path | None = None
    if args.private_key:
        private_key_path = Path(args.private_key).expanduser()
    else:
        private_key_path = infer_private_key_path(args.public_key)

    if private_key_path and not private_key_path.is_file():
        raise BootstrapError(f"Private key file not found: {private_key_path}")

    paramiko = import_paramiko()

    print(f"[1/5] Connecting to {args.root_user}@{args.host}:{args.port} ...")
    root_client = connect_with_password(
        paramiko=paramiko,
        host=args.host,
        port=args.port,
        username=args.root_user,
        password=root_password,
    )

    try:
        print("[2/5] Preparing the server ...")
        run_remote_script(
            root_client,
            render_prepare_script(args.new_user, public_key),
            "Server preparation",
        )

        if private_key_path is not None:
            print("[3/5] Verifying key-based login before SSH lockdown ...")
            verify_key_login(
                paramiko=paramiko,
                host=args.host,
                port=args.port,
                username=args.new_user,
                private_key_path=private_key_path,
                passphrase=args.private_key_passphrase,
            )

            print("[4/5] Applying SSH hardening ...")
            run_remote_script(
                root_client,
                render_hardening_script(args.new_user),
                "SSH hardening",
            )

            print("[5/5] Verifying key-based login after SSH lockdown ...")
            try:
                verify_key_login(
                    paramiko=paramiko,
                    host=args.host,
                    port=args.port,
                    username=args.new_user,
                    private_key_path=private_key_path,
                    passphrase=args.private_key_passphrase,
                )
            except Exception:
                print(
                    "Post-hardening verification failed. Rolling SSH config back.",
                    file=sys.stderr,
                )
                run_remote_script(
                    root_client,
                    render_rollback_script(),
                    "SSH rollback",
                )
                raise

            config_path = update_ssh_config(
                alias=args.alias,
                host=args.host,
                port=args.port,
                username=args.new_user,
                private_key_path=private_key_path,
            )

            print("")
            print("Bootstrap complete.")
            print(f"SSH alias saved to: {config_path}")
            print(f"Alias login: ssh {args.alias}")
            print(f"Next login: ssh -i {private_key_path} {args.new_user}@{args.host}")
            return 0

        if args.force_hardening_without_verification:
            print("[3/3] No private key provided. Applying SSH hardening without verification ...")
            run_remote_script(
                root_client,
                render_hardening_script(args.new_user),
                "SSH hardening",
            )
            print("")
            print("Bootstrap complete, but SSH hardening was applied without a verification login.")
            print("Make sure the installed key is correct before closing the current session.")
            return 0

        print("")
        print("Server preparation complete.")
        print("SSH hardening was skipped because no private key was available for verification.")
        print("Provide --private-key or use the manual fallback before disabling root/password SSH access.")
        return 0
    finally:
        root_client.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootstrapError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
