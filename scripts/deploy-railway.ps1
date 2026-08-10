param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [string]$Environment = "production",
    [string]$BackendService = "backend",
    [string]$FrontendService = "frontend",

    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,

    [string]$BackendUrl,
    [string]$FrontendUrl,
    [string]$CorsOrigins,
    [string]$ModelPath = "ml_artifacts/ranker.joblib",

    [Parameter(Mandatory = $true)]
    [string]$OperatorApiKey,

    [Parameter(Mandatory = $true)]
    [string]$ReviewerApiKey,

    [Parameter(Mandatory = $true)]
    [string]$AdminApiKey,

    [switch]$SkipReadiness,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Assert-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Invoke-Railway {
    param([string[]]$CommandArgs)

    $safeArgs = @()
    foreach ($item in $CommandArgs) {
        if ($item -match "^(DATABASE_URL|OPERATOR_API_KEY|REVIEWER_API_KEY|ADMIN_API_KEY|VITE_OPERATOR_API_KEY|VITE_REVIEWER_API_KEY|VITE_ADMIN_API_KEY)=(.*)$") {
            $safeArgs += ($Matches[1] + "=***")
        } else {
            $safeArgs += $item
        }
    }

    $display = "railway " + ($safeArgs -join " ")
    Write-Host "> $display" -ForegroundColor DarkCyan

    if ($DryRun) {
        return
    }

    & railway @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Railway command failed: $display"
    }
}

Assert-Command -Name "railway"

if ([string]::IsNullOrWhiteSpace($CorsOrigins) -and -not [string]::IsNullOrWhiteSpace($FrontendUrl)) {
    $CorsOrigins = $FrontendUrl
}

if ([string]::IsNullOrWhiteSpace($BackendUrl) -or [string]::IsNullOrWhiteSpace($FrontendUrl)) {
    if (-not $SkipReadiness) {
        Write-Host "BackendUrl or FrontendUrl missing, enabling -SkipReadiness automatically." -ForegroundColor Yellow
        $SkipReadiness = $true
    }
}

if ($DryRun -and -not $SkipReadiness) {
    Write-Host "DryRun enabled, forcing -SkipReadiness to avoid external smoke test calls." -ForegroundColor Yellow
    $SkipReadiness = $true
}

$backendApiBase = $null
if (-not [string]::IsNullOrWhiteSpace($BackendUrl)) {
    $backendApiBase = "$($BackendUrl.TrimEnd('/'))/api"
}

Write-Host "Linking backend service..." -ForegroundColor Cyan
Invoke-Railway -CommandArgs @(
    "link",
    "--project", $ProjectId,
    "--environment", $Environment,
    "--service", $BackendService
)

Write-Host "Setting backend variables..." -ForegroundColor Cyan
Invoke-Railway -CommandArgs @("variable", "set", "DATABASE_URL=$DatabaseUrl", "--project", $ProjectId, "--environment", $Environment, "--service", $BackendService, "--skip-deploys")
Invoke-Railway -CommandArgs @("variable", "set", "MODEL_PATH=$ModelPath", "--project", $ProjectId, "--environment", $Environment, "--service", $BackendService, "--skip-deploys")
Invoke-Railway -CommandArgs @("variable", "set", "AUTO_CREATE_SCHEMA=false", "--project", $ProjectId, "--environment", $Environment, "--service", $BackendService, "--skip-deploys")
Invoke-Railway -CommandArgs @("variable", "set", "OPERATOR_API_KEY=$OperatorApiKey", "--project", $ProjectId, "--environment", $Environment, "--service", $BackendService, "--skip-deploys")
Invoke-Railway -CommandArgs @("variable", "set", "REVIEWER_API_KEY=$ReviewerApiKey", "--project", $ProjectId, "--environment", $Environment, "--service", $BackendService, "--skip-deploys")
Invoke-Railway -CommandArgs @("variable", "set", "ADMIN_API_KEY=$AdminApiKey", "--project", $ProjectId, "--environment", $Environment, "--service", $BackendService, "--skip-deploys")

if (-not [string]::IsNullOrWhiteSpace($CorsOrigins)) {
    Invoke-Railway -CommandArgs @("variable", "set", "CORS_ORIGINS=$CorsOrigins", "--project", $ProjectId, "--environment", $Environment, "--service", $BackendService, "--skip-deploys")
}

Write-Host "Deploying backend service..." -ForegroundColor Cyan
Set-Location (Join-Path $repoRoot "backend")
Invoke-Railway -CommandArgs @(
    "up",
    ".",
    "--path-as-root",
    "--detach",
    "--yes",
    "--project", $ProjectId,
    "--environment", $Environment,
    "--service", $BackendService,
    "--message", "Deploy backend from monorepo script"
)

Write-Host "Linking frontend service..." -ForegroundColor Cyan
Set-Location $repoRoot
Invoke-Railway -CommandArgs @(
    "link",
    "--project", $ProjectId,
    "--environment", $Environment,
    "--service", $FrontendService
)

if (-not [string]::IsNullOrWhiteSpace($backendApiBase)) {
    Write-Host "Setting frontend variables..." -ForegroundColor Cyan
    Invoke-Railway -CommandArgs @("variable", "set", "VITE_API_BASE_URL=$backendApiBase", "--project", $ProjectId, "--environment", $Environment, "--service", $FrontendService, "--skip-deploys")
    Invoke-Railway -CommandArgs @("variable", "set", "VITE_OPERATOR_API_KEY=$OperatorApiKey", "--project", $ProjectId, "--environment", $Environment, "--service", $FrontendService, "--skip-deploys")
    Invoke-Railway -CommandArgs @("variable", "set", "VITE_REVIEWER_API_KEY=$ReviewerApiKey", "--project", $ProjectId, "--environment", $Environment, "--service", $FrontendService, "--skip-deploys")
    Invoke-Railway -CommandArgs @("variable", "set", "VITE_ADMIN_API_KEY=$AdminApiKey", "--project", $ProjectId, "--environment", $Environment, "--service", $FrontendService, "--skip-deploys")
} else {
    Write-Host "Skipping VITE_API_BASE_URL set because BackendUrl was not provided." -ForegroundColor Yellow
}

Write-Host "Deploying frontend service..." -ForegroundColor Cyan
Set-Location (Join-Path $repoRoot "frontend")
Invoke-Railway -CommandArgs @(
    "up",
    ".",
    "--path-as-root",
    "--detach",
    "--yes",
    "--project", $ProjectId,
    "--environment", $Environment,
    "--service", $FrontendService,
    "--message", "Deploy frontend from monorepo script"
)

Set-Location $repoRoot

if (-not $SkipReadiness) {
    Write-Host "Running strict release-readiness validation..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts/release-readiness.ps1") `
        -BackendUrl $BackendUrl `
        -FrontendUrl $FrontendUrl `
        -DatabaseUrl $DatabaseUrl `
        -CorsOrigins $CorsOrigins `
        -ModelPath $ModelPath `
        -OperatorKey $OperatorApiKey `
        -ReviewerKey $ReviewerApiKey `
        -AdminKey $AdminApiKey `
        -RequireExternal

    if ($LASTEXITCODE -ne 0) {
        throw "release-readiness failed"
    }
}

Write-Host "RAILWAY_DEPLOY_SCRIPT_OK" -ForegroundColor Green
