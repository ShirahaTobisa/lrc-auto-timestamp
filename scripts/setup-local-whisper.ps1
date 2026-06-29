$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Get-Command py -ErrorAction SilentlyContinue

if ($Python) {
  $VersionCheck = & py -3.12 -c "import sys; print(sys.version)" 2>$null
  if ($LASTEXITCODE -eq 0) {
    $PythonCmd = "py"
    $PythonArgs = @("-3.12")
  } else {
    $VersionCheck = & py -3.11 -c "import sys; print(sys.version)" 2>$null
    if ($LASTEXITCODE -eq 0) {
      $PythonCmd = "py"
      $PythonArgs = @("-3.11")
    }
  }
}

if (-not $PythonCmd) {
  Write-Host "Python 3.11 or 3.12 was not found."
  Write-Host "Install one from https://www.python.org/downloads/windows/ or winget, then rerun this script."
  exit 1
}

Push-Location $Root
try {
  & $PythonCmd @PythonArgs -m venv .venv
  & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
  & ".\.venv\Scripts\python.exe" -m pip install -r backend\requirements-local.txt
  Write-Host "Local Whisper backend dependencies installed."
  Write-Host "Run: .\scripts\start-backend.ps1"
} finally {
  Pop-Location
}

