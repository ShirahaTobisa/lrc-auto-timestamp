$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
  $Python = "python"
}

Push-Location $Backend
try {
  & $Python -m app.provider_probe --provider nvidia
} finally {
  Pop-Location
}
