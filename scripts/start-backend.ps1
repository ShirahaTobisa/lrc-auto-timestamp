$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
  $Python = "python"
}

Push-Location $Backend
try {
  & $Python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
} finally {
  Pop-Location
}

