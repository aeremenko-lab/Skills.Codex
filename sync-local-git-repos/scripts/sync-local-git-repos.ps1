[CmdletBinding()]
param(
    [string]$Root = "C:\10.CODE",
    [switch]$Recurse,
    [switch]$Json,
    [switch]$DiagnoseWithGh
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)][string]$Repo,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & git -C $Repo @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    [pscustomobject]@{
        ExitCode = $exitCode
        Output = @($output | ForEach-Object { $_.ToString() })
        Text = (@($output | ForEach-Object { $_.ToString() }) -join "`n")
    }
}

function Test-GitRepo {
    param([Parameter(Mandatory = $true)][string]$Path)

    $result = Invoke-Git -Repo $Path -Arguments @("rev-parse", "--is-inside-work-tree")
    return ($result.ExitCode -eq 0 -and ($result.Output -join "").Trim() -eq "true")
}

function Get-GitHubSlug {
    param([string]$RemoteUrl)

    if ($RemoteUrl -match "github\.com[:/](?<owner>[^/]+)/(?<repo>[^/#?]+?)(?:\.git)?(?:[/#?].*)?$") {
        return "$($Matches.owner)/$($Matches.repo)"
    }

    return $null
}

function Invoke-GhDiagnosis {
    param([string]$RemoteUrl)

    $slug = Get-GitHubSlug -RemoteUrl $RemoteUrl
    if (-not $slug) {
        return "Remote is not a parseable github.com URL."
    }

    $viewOutput = & gh repo view $slug 2>&1
    $viewExit = $LASTEXITCODE
    if ($viewExit -eq 0) {
        return "gh repo view ${slug}: OK"
    }

    return "gh repo view ${slug}: $(@($viewOutput | ForEach-Object { $_.ToString() }) -join ' ')"
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git was not found on PATH."
}

$resolvedRoot = (Resolve-Path -LiteralPath $Root).Path

if ($DiagnoseWithGh -and -not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Warning "gh was not found on PATH; GitHub diagnosis will be skipped."
    $DiagnoseWithGh = $false
}

$ghAuthStatus = $null
if ($DiagnoseWithGh) {
    $authOutput = & gh auth status 2>&1
    $ghAuthStatus = "gh auth status: $(@($authOutput | ForEach-Object { $_.ToString() }) -join ' ')"
}

if ($Recurse) {
    $repoDirs = Get-ChildItem -LiteralPath $resolvedRoot -Directory -Force -Recurse |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName ".git") }
} else {
    $repoDirs = Get-ChildItem -LiteralPath $resolvedRoot -Directory -Force
}

$results = foreach ($dir in $repoDirs) {
    $repo = $dir.FullName
    $name = $dir.Name
    $remoteUrl = $null
    $details = ""
    $action = "Skipped"
    $status = "Unknown"

    if (-not (Test-GitRepo -Path $repo)) {
        [pscustomobject]@{
            Name = $name
            Path = $repo
            Status = "NotGitRepo"
            Action = "Skipped"
            Remote = $null
            Details = "Folder is not a Git worktree."
        }
        continue
    }

    $origin = Invoke-Git -Repo $repo -Arguments @("remote", "get-url", "origin")
    if ($origin.ExitCode -ne 0) {
        [pscustomobject]@{
            Name = $name
            Path = $repo
            Status = "NoOrigin"
            Action = "Skipped"
            Remote = $null
            Details = "No remote named origin."
        }
        continue
    }

    $remoteUrl = ($origin.Output | Select-Object -First 1).Trim()

    $fetch = Invoke-Git -Repo $repo -Arguments @("fetch", "--prune", "origin")
    if ($fetch.ExitCode -ne 0) {
        $status = "FetchFailed"
        if ($fetch.Text -match "(?i)repository not found|not found|does not appear to be a git repository|could not read from remote repository") {
            $status = "InvalidRemote"
        }

        $details = $fetch.Text
        if ($DiagnoseWithGh) {
            $details = "$details`n$ghAuthStatus`n$(Invoke-GhDiagnosis -RemoteUrl $remoteUrl)"
        }

        [pscustomobject]@{
            Name = $name
            Path = $repo
            Status = $status
            Action = "FetchFailed"
            Remote = $remoteUrl
            Details = $details.Trim()
        }
        continue
    }

    $dirty = Invoke-Git -Repo $repo -Arguments @("status", "--porcelain=v1")
    if (($dirty.Output | Where-Object { $_ -ne "" }).Count -gt 0) {
        [pscustomobject]@{
            Name = $name
            Path = $repo
            Status = "Dirty"
            Action = "FetchedOnly"
            Remote = $remoteUrl
            Details = "Worktree has local changes."
        }
        continue
    }

    $branch = Invoke-Git -Repo $repo -Arguments @("rev-parse", "--abbrev-ref", "HEAD")
    if ($branch.ExitCode -ne 0 -or (($branch.Output | Select-Object -First 1).Trim()) -eq "HEAD") {
        [pscustomobject]@{
            Name = $name
            Path = $repo
            Status = "DetachedHead"
            Action = "FetchedOnly"
            Remote = $remoteUrl
            Details = "Current checkout is detached."
        }
        continue
    }

    $upstream = Invoke-Git -Repo $repo -Arguments @("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if ($upstream.ExitCode -ne 0) {
        [pscustomobject]@{
            Name = $name
            Path = $repo
            Status = "NoUpstream"
            Action = "FetchedOnly"
            Remote = $remoteUrl
            Details = "Current branch has no upstream."
        }
        continue
    }

    $upstreamName = ($upstream.Output | Select-Object -First 1).Trim()
    if ($upstreamName -notlike "origin/*") {
        [pscustomobject]@{
            Name = $name
            Path = $repo
            Status = "NonOriginUpstream"
            Action = "FetchedOnly"
            Remote = $remoteUrl
            Details = "Current branch tracks $upstreamName, not origin."
        }
        continue
    }

    $localHash = (Invoke-Git -Repo $repo -Arguments @("rev-parse", "@")).Output[0].Trim()
    $remoteHash = (Invoke-Git -Repo $repo -Arguments @("rev-parse", "@{u}")).Output[0].Trim()
    $baseHash = (Invoke-Git -Repo $repo -Arguments @("merge-base", "@", "@{u}")).Output[0].Trim()

    if ($localHash -eq $remoteHash) {
        [pscustomobject]@{
            Name = $name
            Path = $repo
            Status = "UpToDate"
            Action = "FetchedOnly"
            Remote = $remoteUrl
            Details = "Already up to date."
        }
        continue
    }

    if ($baseHash -eq $localHash) {
        $pull = Invoke-Git -Repo $repo -Arguments @("pull", "--ff-only")
        if ($pull.ExitCode -eq 0) {
            $action = "Pulled"
            $status = "FastForwarded"
        } else {
            $action = "PullFailed"
            $status = "PullFailed"
        }

        [pscustomobject]@{
            Name = $name
            Path = $repo
            Status = $status
            Action = $action
            Remote = $remoteUrl
            Details = $pull.Text.Trim()
        }
        continue
    }

    if ($baseHash -eq $remoteHash) {
        [pscustomobject]@{
            Name = $name
            Path = $repo
            Status = "Ahead"
            Action = "FetchedOnly"
            Remote = $remoteUrl
            Details = "Local branch is ahead of upstream."
        }
        continue
    }

    [pscustomobject]@{
        Name = $name
        Path = $repo
        Status = "Diverged"
        Action = "FetchedOnly"
        Remote = $remoteUrl
        Details = "Local and upstream branches have diverged."
    }
}

if ($Json) {
    $results | ConvertTo-Json -Depth 4
    return
}

$results | Sort-Object Name | Format-Table Name, Status, Action, Remote -AutoSize

$summary = $results | Group-Object Status | Sort-Object Name | ForEach-Object { "$($_.Name)=$($_.Count)" }
Write-Host ""
Write-Host "Summary: $($summary -join ', ')"

$problemResults = $results | Where-Object { $_.Status -in @("InvalidRemote", "FetchFailed", "PullFailed", "Diverged", "Dirty") }
if ($problemResults) {
    Write-Host ""
    Write-Host "Details:"
    foreach ($item in $problemResults) {
        Write-Host "[$($item.Status)] $($item.Name): $($item.Details)"
    }
}
