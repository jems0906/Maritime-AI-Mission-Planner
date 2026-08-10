param(
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl,

    [Parameter(Mandatory = $true)]
    [string]$FrontendUrl,

    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,

    [Parameter(Mandatory = $true)]
    [string]$CorsOrigins,

    [string]$ModelPath = "ml_artifacts/ranker.joblib"
)

$ErrorActionPreference = "Stop"

function Assert-HttpsUrl {
    param(
        [string]$Name,
        [string]$Value
    )

    if (-not [Uri]::IsWellFormedUriString($Value, [UriKind]::Absolute)) {
        throw "$Name is not a valid absolute URL: $Value"
    }

    $uri = [Uri]$Value
    if ($uri.Scheme -ne "https") {
        throw "$Name must use https: $Value"
    }
}

Assert-HttpsUrl -Name "BackendUrl" -Value $BackendUrl
Assert-HttpsUrl -Name "FrontendUrl" -Value $FrontendUrl

$dbUrlAccepted =
    $DatabaseUrl.StartsWith("postgresql+psycopg://") -or
    $DatabaseUrl.StartsWith("postgresql://") -or
    $DatabaseUrl.StartsWith('${{Postgres.')

if (-not $dbUrlAccepted) {
    throw "DatabaseUrl must start with postgresql+psycopg://, postgresql://, or use a Railway Postgres reference"
}

if ([string]::IsNullOrWhiteSpace($ModelPath)) {
    throw "ModelPath must not be empty"
}

$normalizedOrigins = $CorsOrigins.Replace(" ", "")
$allowed = $normalizedOrigins.Split(",", [System.StringSplitOptions]::RemoveEmptyEntries)
if ($allowed.Count -eq 0) {
    throw "CorsOrigins must contain at least one origin"
}

if (-not ($allowed -contains $FrontendUrl)) {
    throw "CorsOrigins must include FrontendUrl. FrontendUrl: $FrontendUrl; CorsOrigins: $CorsOrigins"
}

Write-Host "RAILWAY_ENV_OK" -ForegroundColor Green
$databaseScheme = "unknown"
if ($DatabaseUrl.StartsWith("postgresql+psycopg://")) {
    $databaseScheme = "postgresql+psycopg"
} elseif ($DatabaseUrl.StartsWith("postgresql://")) {
    $databaseScheme = "postgresql"
} elseif ($DatabaseUrl.StartsWith('${{Postgres.')) {
    $databaseScheme = "railway-reference"
}

Write-Output (@{
    backend_url = $BackendUrl
    frontend_url = $FrontendUrl
    cors_origins = $CorsOrigins
    model_path = $ModelPath
    database_url_scheme = $databaseScheme
} | ConvertTo-Json -Depth 3)
