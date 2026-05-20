param(
    [ValidateSet("all", "prod", "am-149", "lv", "am")]
    [string] $Only = "all"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Ssh = "C:\Windows\System32\OpenSSH\ssh.exe"
if (-not (Test-Path -LiteralPath $Ssh)) {
    throw "Windows OpenSSH not found at $Ssh"
}

$AllTargets = @(
    @{ Label = "prod"; Alias = "prod-codex"; Mode = "deep"; PublicTcp = "22,80,443"; PublicUdp = "443"; InternalPorts = "8055,5678,15432" },
    @{ Label = "am-149"; Alias = "am-149-codex"; Mode = "deep"; PublicTcp = "22"; PublicUdp = ""; InternalPorts = "" },
    @{ Label = "lv"; Alias = "lv-codex"; Mode = "baseline"; PublicTcp = "22"; PublicUdp = ""; InternalPorts = "" },
    @{ Label = "am"; Alias = "am-codex"; Mode = "baseline"; PublicTcp = "22"; PublicUdp = ""; InternalPorts = "" }
)

$RemoteScript = @'
set -u

MODE="${1:-baseline}"
LABEL="${2:-unknown}"
PUBLIC_TCP_CSV="${3:-22}"
PUBLIC_UDP_CSV="${4:-}"
INTERNAL_PORTS_CSV="${5:-}"

status() {
  printf '[%s] %s\n' "$1" "$2"
}

section() {
  printf '\n### %s\n' "$1"
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

sudo_try() {
  sudo -n "$@" 2>/dev/null
}

csv_contains() {
  local csv="$1"
  local needle="$2"
  IFS=',' read -ra parts <<< "$csv"
  for part in "${parts[@]}"; do
    if [ "$part" = "$needle" ]; then
      return 0
    fi
  done
  return 1
}

extract_port() {
  printf '%s\n' "$1" | sed -E 's/.*:([0-9]+)$/\1/'
}

is_loopback_addr() {
  local addr="$1"
  case "$addr" in
    127.*|localhost:*|"[::1]:"*|"::1:"*) return 0 ;;
    *) return 1 ;;
  esac
}

echo "# $LABEL"
printf 'Host: %s\n' "$(hostname -f 2>/dev/null || hostname)"
printf 'Kernel: %s\n' "$(uname -srmo 2>/dev/null || uname -a)"
printf 'Uptime: %s\n' "$(uptime -p 2>/dev/null || uptime)"

section "SSH and Firewall"
SSHD_BIN="$(command -v sshd || true)"
if [ -z "$SSHD_BIN" ] && [ -x /usr/sbin/sshd ]; then
  SSHD_BIN=/usr/sbin/sshd
fi

if [ -n "$SSHD_BIN" ]; then
  EFFECTIVE="$(sudo_try "$SSHD_BIN" -T || true)"
  if [ -n "$EFFECTIVE" ]; then
    PERMIT_ROOT="$(printf '%s\n' "$EFFECTIVE" | awk '$1=="permitrootlogin"{print $2; exit}')"
    PASSWORD_AUTH="$(printf '%s\n' "$EFFECTIVE" | awk '$1=="passwordauthentication"{print $2; exit}')"
    KBD_AUTH="$(printf '%s\n' "$EFFECTIVE" | awk '$1=="kbdinteractiveauthentication"{print $2; exit}')"
    ALLOW_USERS="$(printf '%s\n' "$EFFECTIVE" | awk '$1=="allowusers"{for(i=2;i<=NF;i++) print $i}' | sort -u | xargs)"

    [ "$PERMIT_ROOT" = "no" ] && status OK "PermitRootLogin is no" || status FAIL "PermitRootLogin is ${PERMIT_ROOT:-unset}"
    [ "$PASSWORD_AUTH" = "no" ] && status OK "PasswordAuthentication is no" || status FAIL "PasswordAuthentication is ${PASSWORD_AUTH:-unset}"
    [ "$KBD_AUTH" = "no" ] && status OK "KbdInteractiveAuthentication is no" || status WARN "KbdInteractiveAuthentication is ${KBD_AUTH:-unset}"

    if printf ' %s ' "$ALLOW_USERS" | grep -q ' anton ' && printf ' %s ' "$ALLOW_USERS" | grep -q ' codex '; then
      status OK "AllowUsers includes anton and codex"
    else
      status WARN "AllowUsers is '${ALLOW_USERS:-unset}'"
    fi
  else
    status WARN "Could not read effective sshd config with sudo"
  fi
else
  status WARN "sshd binary not found"
fi

if have_cmd ufw; then
  UFW_STATUS="$(sudo_try ufw status verbose || true)"
  if printf '%s\n' "$UFW_STATUS" | grep -qi '^Status: active'; then
    status OK "UFW is active"
  else
    status FAIL "UFW is not active or status could not be read"
  fi
  printf '%s\n' "$UFW_STATUS" | sed -n '1,18p'
else
  status FAIL "ufw command not found"
fi

section "Patch Routine"
if systemctl is-active --quiet unattended-upgrades 2>/dev/null; then
  status OK "unattended-upgrades service is active"
else
  status WARN "unattended-upgrades service is not active"
fi
systemctl list-timers --all apt-daily.timer apt-daily-upgrade.timer 2>/dev/null | sed -n '1,8p' || status WARN "Could not list apt timers"

if [ -f /var/run/reboot-required ]; then
  status WARN "Reboot is required"
else
  status OK "No reboot-required marker"
fi

ROOT_USE="$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')"
if [ -n "$ROOT_USE" ] && [ "$ROOT_USE" -ge 85 ]; then
  status WARN "Root filesystem usage is ${ROOT_USE}%"
else
  status OK "Root filesystem usage is ${ROOT_USE:-unknown}%"
fi
df -h / | sed -n '1,2p'

if [ "$MODE" != "deep" ]; then
  exit 0
fi

section "Docker Published Ports"
if have_cmd docker; then
  DOCKER_PS="$(sudo_try docker ps --format '{{.Names}}\t{{.Ports}}' || true)"
  if [ -n "$DOCKER_PS" ]; then
    printf '%s\n' "$DOCKER_PS"
    if printf '%s\n' "$DOCKER_PS" | grep -Eq '0\.0\.0\.0:|:::|\[::\]:'; then
      status WARN "At least one Docker port is published on a public interface"
    else
      status OK "Docker published ports appear loopback-bound or absent"
    fi
  else
    status OK "No running Docker containers with published port data, or Docker requires attention"
  fi
else
  status OK "Docker is not installed"
fi

section "Listening Services"
if have_cmd ss; then
  SS_OUT="$(sudo_try ss -tulpn || ss -tulpn 2>/dev/null || true)"
  printf '%s\n' "$SS_OUT" | sed -n '1,80p'

  WARNED=0
  while IFS= read -r line; do
    proto="$(printf '%s\n' "$line" | awk '{print $1}')"
    local_addr="$(printf '%s\n' "$line" | awk '{print $5}')"
    [ -z "$proto" ] || [ -z "$local_addr" ] && continue
    [ "$proto" = "Netid" ] && continue
    port="$(extract_port "$local_addr")"
    [ -z "$port" ] && continue

    if ! is_loopback_addr "$local_addr"; then
      case "$proto" in
        tcp|tcp6)
          if ! csv_contains "$PUBLIC_TCP_CSV" "$port"; then
            status WARN "Unexpected public TCP listener: $local_addr"
            WARNED=1
          fi
          ;;
        udp|udp6)
          if ! csv_contains "$PUBLIC_UDP_CSV" "$port"; then
            status WARN "Unexpected public UDP listener: $local_addr"
            WARNED=1
          fi
          ;;
      esac
    fi
  done < <(printf '%s\n' "$SS_OUT")
  [ "$WARNED" -eq 0 ] && status OK "No unexpected non-loopback listeners detected"
else
  status WARN "ss command not found"
fi

if [ -n "$INTERNAL_PORTS_CSV" ] && [ -n "${SS_OUT:-}" ]; then
  section "Internal App Binding"
  IFS=',' read -ra internal_ports <<< "$INTERNAL_PORTS_CSV"
  for port in "${internal_ports[@]}"; do
    lines="$(printf '%s\n' "$SS_OUT" | grep -E ":${port}[[:space:]]" || true)"
    if [ -z "$lines" ]; then
      status WARN "Expected internal port $port is not currently listening"
      continue
    fi
    if printf '%s\n' "$lines" | awk '{print $5}' | grep -Ev '^(127\.|localhost:|\[::1\]:|::1:)' >/dev/null; then
      status FAIL "Internal port $port has a non-loopback listener"
      printf '%s\n' "$lines"
    else
      status OK "Internal port $port is loopback-bound"
    fi
  done
fi
'@

function Invoke-AuditTarget {
    param(
        [Parameter(Mandatory)] [hashtable] $Target
    )

    $label = [string]$Target.Label
    $alias = [string]$Target.Alias
    $mode = [string]$Target.Mode
    $publicTcp = [string]$Target.PublicTcp
    $publicUdp = [string]$Target.PublicUdp
    $internalPorts = [string]$Target.InternalPorts

    Write-Output ""
    Write-Output "## $label ($alias)"

    $remoteCommand = "tr -d '\015' | bash -s -- '$mode' '$label' '$publicTcp' '$publicUdp' '$internalPorts'"

    $sshArgs = @(
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=12",
        "-o", "ServerAliveInterval=5",
        "-o", "ServerAliveCountMax=1",
        $alias,
        $remoteCommand
    )

    try {
        $normalized = $RemoteScript -replace "`r`n", "`n"
        $output = $normalized | & $Ssh @sshArgs 2>&1
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            Write-Output "[WARN] SSH audit command exited with code $exitCode"
        }
        $output | ForEach-Object { Write-Output $_ }
    }
    catch {
        Write-Output "[WARN] Could not audit $label via ${alias}: $($_.Exception.Message)"
    }
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
Write-Output "# Ubuntu Weekly Audit"
Write-Output ""
Write-Output "Generated: $timestamp"
Write-Output "Mode: read-only"

$SelectedTargets = if ($Only -eq "all") {
    $AllTargets
}
else {
    $AllTargets | Where-Object { $_.Label -eq $Only }
}

foreach ($target in $SelectedTargets) {
    Invoke-AuditTarget -Target $target
}
