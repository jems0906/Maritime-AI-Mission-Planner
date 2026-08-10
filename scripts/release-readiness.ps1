#pragma warning disable PSAvoidAssignmentToAutomaticVariable

param(
    [string]$BackendUrl,
    [string]$FrontendUrl,
    [string]$DatabaseUrl,
    [string]$CorsOrigins,
    [string]$ModelPath = "ml_artifacts/ranker.joblib",
    [string]$OperatorKey,
    [string]$ReviewerKey,
    [string]$AdminKey,
    [switch]$RequireExternal
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "[1/3] Foundation local gates" -ForegroundColor Cyan
& (Join-Path $repoRoot "scripts/foundation-check.ps1")
if ($LASTEXITCODE -ne 0) { throw "foundation-check failed" }

Write-Host "[2/3] Deployment environment validation" -ForegroundColor Cyan
$hasDeploymentInputs = -not [string]::IsNullOrWhiteSpace($BackendUrl) -and `
    -not [string]::IsNullOrWhiteSpace($FrontendUrl) -and `
    -not [string]::IsNullOrWhiteSpace($DatabaseUrl) -and `
    -not [string]::IsNullOrWhiteSpace($CorsOrigins)

if ($hasDeploymentInputs) {
    & (Join-Path $repoRoot "scripts/validate-railway-env.ps1") `
        -BackendUrl $BackendUrl `
        -FrontendUrl $FrontendUrl `
        -DatabaseUrl $DatabaseUrl `
        -CorsOrigins $CorsOrigins `
        -ModelPath $ModelPath
    if ($LASTEXITCODE -ne 0) { throw "validate-railway-env failed" }
} elseif ($RequireExternal) {
    throw "RequireExternal specified but one or more deployment inputs are missing"
} else {
    Write-Host "Skipped deployment env validation (inputs not provided)." -ForegroundColor Yellow
}

Write-Host "[3/3] Live API smoke checks" -ForegroundColor Cyan
if (-not [string]::IsNullOrWhiteSpace($BackendUrl)) {
    Set-Location (Join-Path $repoRoot "backend")
    python "scripts/live_smoke_test.py" "--base-url" "$BackendUrl/api" `
        $(if (-not [string]::IsNullOrWhiteSpace($OperatorKey)) { "--operator-key"; $OperatorKey }) `
        $(if (-not [string]::IsNullOrWhiteSpace($ReviewerKey)) { "--reviewer-key"; $ReviewerKey }) `
        $(if (-not [string]::IsNullOrWhiteSpace($AdminKey)) { "--admin-key"; $AdminKey }) `
        $(if ($RequireExternal) { "--strict-keys" })
    if ($LASTEXITCODE -ne 0) { throw "live smoke failed" }
} elseif ($RequireExternal) {
    throw "RequireExternal specified but BackendUrl was not provided"
} else {
    Write-Host "Skipped live smoke checks (BackendUrl not provided)." -ForegroundColor Yellow
}

Set-Location $repoRoot
Write-Host "RELEASE_READINESS_OK" -ForegroundColor Green

#pragma warning restore PSAvoidAssignmentToAutomaticVariable
