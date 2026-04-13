# Manual Ubuntu VPS Bootstrap

Use this fallback only when `scripts/bootstrap_ubuntu_vps.py` cannot be used.

## 1. Create or Reuse an SSH Key

Create a new `ed25519` key locally if needed:

```powershell
ssh-keygen -t ed25519 -a 100 -f $HOME\.ssh\anton-vps -C "anton@new-vps"
```

Keep both of these paths:

- private key: `$HOME\.ssh\anton-vps`
- public key: `$HOME\.ssh\anton-vps.pub`

## 2. Connect as Root

```powershell
ssh root@203.0.113.10
```

## 3. Install Base Packages

```bash
apt-get update
apt-get install -y sudo openssh-server ufw fail2ban unattended-upgrades
```

## 4. Create the New Admin User

Replace `anton` with the username chosen by the user:

```bash
adduser --disabled-password --gecos "" anton
usermod -aG sudo anton
printf '%s\n' 'anton ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/90-anton-nopasswd
chmod 440 /etc/sudoers.d/90-anton-nopasswd
visudo -cf /etc/sudoers.d/90-anton-nopasswd
```

## 5. Install the SSH Public Key

Create the `.ssh` directory and paste the public key into `authorized_keys`:

```bash
install -d -m 700 -o anton -g anton /home/anton/.ssh
touch /home/anton/.ssh/authorized_keys
chmod 600 /home/anton/.ssh/authorized_keys
chown anton:anton /home/anton/.ssh/authorized_keys
```

Append the public key:

```bash
printf '%s\n' 'ssh-ed25519 AAAA... your-comment' >> /home/anton/.ssh/authorized_keys
```

## 6. Verify Key Login Before Lockdown

From the local machine, open a second terminal and verify that the new user can log in with the private key:

```powershell
ssh -i $HOME\.ssh\anton-vps anton@203.0.113.10
```

Only continue if this works.

## 7. Enable Basic Hardening

```bash
mkdir -p /etc/fail2ban/jail.d
cat > /etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
maxretry = 5
findtime = 10m
bantime = 1h
EOF

ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw --force enable

systemctl enable fail2ban
systemctl restart fail2ban
systemctl enable unattended-upgrades || true
systemctl restart unattended-upgrades || true
```

## 8. Disable Root and Password SSH Login

Create an SSH drop-in:

```bash
mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-codex-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
X11Forwarding no
AllowUsers anton
EOF
```

Validate and reload SSH:

```bash
sshd -t
systemctl reload ssh || systemctl restart ssh || systemctl reload sshd || systemctl restart sshd
```

## 9. Verify Again

Confirm that this still works after hardening:

```powershell
ssh -i $HOME\.ssh\anton-vps anton@203.0.113.10
```

If it fails, remove the drop-in from the still-open root session:

```bash
rm -f /etc/ssh/sshd_config.d/99-codex-hardening.conf
systemctl reload ssh || systemctl restart ssh || systemctl reload sshd || systemctl restart sshd
```
