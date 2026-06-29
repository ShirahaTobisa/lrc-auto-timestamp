$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"

Push-Location $Frontend
try {
  npm run dev
} finally {
  Pop-Location
}

