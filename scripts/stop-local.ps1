[CmdletBinding()]
param(
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$stateFile = Join-Path $PSScriptRoot ".local-stack-pids.json"

$targets = New-Object System.Collections.Generic.List[System.Object]

function Add-TargetPid {
  param(
    [int]$ProcessId,
    [string]$Source
  )

  if ($ProcessId -le 0) {
    return
  }

  $targets.Add([PSCustomObject]@{ Id = $ProcessId; Source = $Source })
}

if (Test-Path $stateFile) {
  try {
    $state = Get-Content -Path $stateFile -Raw | ConvertFrom-Json
    if ($state.backendPid) {
      Add-TargetPid -ProcessId ([int]$state.backendPid) -Source "state-backend"
    }
    if ($state.frontendPid) {
      Add-TargetPid -ProcessId ([int]$state.frontendPid) -Source "state-frontend"
    }
  }
  catch {
    Write-Warning "Unable to parse PID state file: $stateFile"
  }
}

# Fallback discovery helps when PID state file is missing or stale.
$processes = Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'"
foreach ($proc in $processes) {
  $cmd = [string]$proc.CommandLine
  if (-not $cmd) {
    continue
  }

  $isBackend = $cmd -like "*$backendDir*" -and $cmd -like "*uvicorn app.main:app*"
  $isFrontend = $cmd -like "*$frontendDir*" -and ($cmd -like "*npm run dev*" -or $cmd -like "*node scripts/dev-static.mjs*")

  if ($isBackend) {
    Add-TargetPid -ProcessId ([int]$proc.ProcessId) -Source "scan-backend"
  }
  elseif ($isFrontend) {
    Add-TargetPid -ProcessId ([int]$proc.ProcessId) -Source "scan-frontend"
  }
}

# Port-based fallback catches detached worker processes.
$portMap = @{
  8000 = "port-backend"
  5173 = "port-frontend"
}

foreach ($port in $portMap.Keys) {
  $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  foreach ($conn in $connections) {
    Add-TargetPid -ProcessId ([int]$conn.OwningProcess) -Source $portMap[$port]
  }
}

$uniqueTargets = $targets |
  Group-Object Id |
  ForEach-Object { $_.Group | Select-Object -First 1 }

if (-not $uniqueTargets -or $uniqueTargets.Count -eq 0) {
  Write-Host "No local stack terminals found."
  if (Test-Path $stateFile) {
    Remove-Item -Path $stateFile -Force
  }
  return
}

if ($DryRun) {
  Write-Host "DRY RUN"
  foreach ($target in $uniqueTargets) {
    Write-Host "Would stop process $($target.Id) ($($target.Source))"
  }
  return
}

$stopped = 0
foreach ($target in $uniqueTargets) {
  try {
    if (-not (Get-Process -Id $target.Id -ErrorAction SilentlyContinue)) {
      continue
    }
    Stop-Process -Id $target.Id -Force -ErrorAction Stop
    Write-Host "Stopped process $($target.Id) ($($target.Source))"
    $stopped += 1
  }
  catch {
    Write-Warning "Failed to stop process $($target.Id): $($_.Exception.Message)"
  }
}

if (Test-Path $stateFile) {
  Remove-Item -Path $stateFile -Force
}

Write-Host "Stopped $stopped local stack process(es)."
