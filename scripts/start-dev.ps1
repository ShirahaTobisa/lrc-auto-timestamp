$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackendScript = Join-Path $PSScriptRoot "start-backend.ps1"
$FrontendScript = Join-Path $PSScriptRoot "start-frontend.ps1"

Write-Host "Starting backend and frontend for $Root"
$backend = Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $BackendScript -PassThru
$frontend = Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $FrontendScript -PassThru

Write-Host "Backend PID: $($backend.Id)"
Write-Host "Frontend PID: $($frontend.Id)"
Write-Host "Open http://127.0.0.1:5173"

