$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"

Write-Host "[1/3] Backend tests" -ForegroundColor Cyan
Set-Location $backendDir
python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }

Write-Host "[2/3] Frontend typecheck" -ForegroundColor Cyan
Set-Location $frontendDir
npm run typecheck
if ($LASTEXITCODE -ne 0) { throw "Frontend typecheck failed." }

Write-Host "[3/3] Compose config validation" -ForegroundColor Cyan
Set-Location $repoRoot
docker compose -f docker-compose.yml config *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker compose config validation failed." }

Write-Host "FOUNDATION_CHECK_OK" -ForegroundColor Green
