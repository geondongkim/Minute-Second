param(
  [string]$OutputRoot = "..\Minute-Second-Repositories",
  [switch]$Recreate,
  [switch]$Push
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repos = @(
  @{
    Prefix = "audio_extractor_stt"
    Name = "Minute-Second-Audio-Extractor-STT"
    Branch = "split/audio-extractor-stt"
    RemoteEnv = "MINUTE_SECOND_AUDIO_REMOTE"
  },
  @{
    Prefix = "lecture-slide-notes"
    Name = "Minute-Second-Lecture-Slide-Notes"
    Branch = "split/lecture-slide-notes"
    RemoteEnv = "MINUTE_SECOND_SLIDE_NOTES_REMOTE"
  },
  @{
    Prefix = "teams-caption-saver"
    Name = "Minute-Second-Caption-Saver"
    Branch = "split/caption-saver"
    RemoteEnv = "MINUTE_SECOND_CAPTION_REMOTE"
  }
)

function Invoke-Git {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
  Write-Host "git $($Arguments -join ' ')" -ForegroundColor DarkGray
  & git @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
  }
}

Push-Location $root
try {
  if (Test-Path ".gitmodules") {
    $submodulePaths = git config --file .gitmodules --get-regexp path
    foreach ($repo in $repos) {
      if ($submodulePaths -match [regex]::Escape($repo.Prefix)) {
        throw "This is a one-time pre-submodule migration script. The umbrella repo already uses submodules; use tools/update-submodules.ps1 instead."
      }
    }
  }

  $status = git status --porcelain
  if ($status) {
    throw "Commit or stash changes before splitting repositories. Split branches must be cut from a stable commit."
  }

  $outputRootPath = Resolve-Path -Path $OutputRoot -ErrorAction SilentlyContinue
  if (-not $outputRootPath) {
    New-Item -ItemType Directory -Path $OutputRoot | Out-Null
    $outputRootPath = Resolve-Path -Path $OutputRoot
  }

  foreach ($repo in $repos) {
    if (-not (Test-Path $repo.Prefix)) {
      throw "Missing source directory: $($repo.Prefix)"
    }

    $existingBranch = git branch --list $repo.Branch
    if ($existingBranch) {
      Invoke-Git branch -D $repo.Branch
    }
  }
} finally {
  Pop-Location
}

Push-Location $root
try {
  $outputRootPath = Resolve-Path -Path $OutputRoot
  foreach ($repo in $repos) {
    Write-Host ""
    Write-Host "==> Splitting $($repo.Prefix) -> $($repo.Name)" -ForegroundColor Cyan
    Invoke-Git subtree split "--prefix=$($repo.Prefix)" --branch $repo.Branch

    $target = Join-Path $outputRootPath $repo.Name
    if (Test-Path $target) {
      if (-not $Recreate) {
        Write-Host "Skipping existing repo: $target (use -Recreate to rebuild)" -ForegroundColor Yellow
        continue
      }
      Remove-Item -Recurse -Force $target
    }

    Invoke-Git clone . $target --branch $repo.Branch --single-branch
    Push-Location $target
    try {
      Invoke-Git branch -M main
      Invoke-Git remote remove origin
      $remoteUrl = [Environment]::GetEnvironmentVariable($repo.RemoteEnv)
      if ($remoteUrl) {
        Invoke-Git remote add origin $remoteUrl
        if ($Push) {
          Invoke-Git push -u origin main
        }
      } elseif ($Push) {
        Write-Host "No remote configured for $($repo.Name). Set $($repo.RemoteEnv) before using -Push." -ForegroundColor Yellow
      }
    } finally {
      Pop-Location
    }
  }
} finally {
  Pop-Location
}

Write-Host ""
Write-Host "Split repositories are under: $((Resolve-Path $OutputRoot).Path)" -ForegroundColor Green
