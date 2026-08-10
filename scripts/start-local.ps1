[CmdletBinding()]
param(
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$stateFile = Join-Path $PSScriptRoot ".local-stack-pids.json"

$pythonCandidates = @(
  "C:/Python314/python.exe",
  "python"
)

$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
  try {
    & $candidate --version *> $null
    if ($LASTEXITCODE -eq 0) {
      $pythonExe = $candidate
      break
    }
  } catch {
    continue
  }
}

if (-not $pythonExe) {
  throw "Python executable not found. Install Python or update scripts/start-local.ps1."
}

$backendCmd = "Set-Location '$backendDir'; `$env:PYTHONPATH='.'; & '$pythonExe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
$frontendCmd = "Set-Location '$frontendDir'; npm run dev"

if ($DryRun) {
  Write-Host "DRY RUN"
  Write-Host "Backend command: $backendCmd"
  Write-Host "Frontend command: $frontendCmd"
  Write-Host "State file: $stateFile"
  return
}

Write-Host "Starting backend at http://127.0.0.1:8000 ..."
$backendProcess = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $backendCmd -PassThru

Write-Host "Starting frontend at http://127.0.0.1:5173 ..."
$frontendProcess = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $frontendCmd -PassThru

$state = [ordered]@{
  repoRoot = $repoRoot
  backendPid = $backendProcess.Id
  frontendPid = $frontendProcess.Id
  startedAtUtc = [DateTime]::UtcNow.ToString("o")
}
$state | ConvertTo-Json | Set-Content -Path $stateFile -Encoding utf8

Write-Host "Launched local stack in two terminals."
Write-Host "Backend: http://127.0.0.1:8000"
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "PID state: $stateFile"
