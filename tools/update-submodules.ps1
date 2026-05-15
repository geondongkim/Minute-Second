$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $root
try {
  git submodule update --init --recursive
  if ($LASTEXITCODE -ne 0) {
    throw "git submodule update failed with exit code $LASTEXITCODE"
  }

  $modulePaths = git config --file .gitmodules --get-regexp path | ForEach-Object { ($_ -split '\s+', 2)[1] }
  foreach ($modulePath in $modulePaths) {
    Push-Location (Join-Path $root $modulePath)
    try {
      git checkout main
      if ($LASTEXITCODE -ne 0) {
        throw "git checkout main failed in $modulePath with exit code $LASTEXITCODE"
      }
      git pull --ff-only
      if ($LASTEXITCODE -ne 0) {
        throw "git pull --ff-only failed in $modulePath with exit code $LASTEXITCODE"
      }
    } finally {
      Pop-Location
    }
  }
} finally {
  Pop-Location
}
