# Release Runbook

## Purpose

This runbook covers production releases for the Maritime AI Mission Planner on Railway. It is intended to keep the deployment process repeatable, auditable, and consistent with the project’s release-readiness validation gate.

## Scope

Applies to:
- backend service deployment
- frontend service deployment
- Railway PostgreSQL connection and migration flow
- production smoke validation and rollback decision-making

This project already includes the technical validation flow in:
- [.github/workflows/release-readiness.yml](release-readiness.yml)
- [scripts/release-readiness.ps1](../scripts/release-readiness.ps1)
- [scripts/deploy-railway.ps1](../scripts/deploy-railway.ps1)

## Required access and tools

Before starting a release, confirm all of the following:
- Railway CLI is installed and authenticated.
- You have access to the correct Railway project and production environment.
- Required secrets or variables are available for the backend service.
- Backend and frontend deployment URLs are known.
- Git branch and release commit are identified.

Typical local prerequisites:
- PowerShell 7+
- Python 3.12
- Node.js 20+
- Railway CLI: `npm i -g @railway/cli`

## Release decision gate

A release should proceed only if all of the following are true:
- local foundation checks pass
- deployment environment validation passes
- live API smoke checks pass
- protected role-key checks pass when keys are configured
- no critical issue is open against the current release candidate

## Release procedure

### 1. Confirm the release target

1. Confirm the intended Railway project and production environment.
2. Confirm the target commit or branch.
3. Verify the working tree is clean or intentionally contains only release-approved changes.
4. Record the release owner and the expected deployment window.

### 2. Run the preflight checks

From the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\foundation-check.ps1
```

This validates:
- backend tests
- frontend typecheck
- Docker Compose configuration

If this fails, stop the release.

### 3. Validate the production environment config

Use the deployment validation script with the exact live URLs and database connection details:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate-railway-env.ps1 `
  -BackendUrl "https://<backend-domain>" `
  -FrontendUrl "https://<frontend-domain>" `
  -DatabaseUrl "postgresql+psycopg://<user>:<pass>@<host>:5432/<db>" `
  -CorsOrigins "https://<frontend-domain>" `
  -ModelPath "ml_artifacts/ranker.joblib"
```

This ensures:
- secure HTTPS endpoints
- valid database URL format
- frontend URL is included in CORS settings
- model path is valid

### 4. Deploy to Railway

Preferred path is the project’s deploy script, which deploys both services and optionally runs readiness validation:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy-railway.ps1 `
  -ProjectId "<railway-project-id>" `
  -Environment "production" `
  -BackendService "backend" `
  -FrontendService "frontend" `
  -DatabaseUrl "postgresql+psycopg://<user>:<pass>@<host>:5432/<db>" `
  -BackendUrl "https://<backend-domain>" `
  -FrontendUrl "https://<frontend-domain>" `
  -CorsOrigins "https://<frontend-domain>" `
  -OperatorApiKey "<operator-key>" `
  -ReviewerApiKey "<reviewer-key>" `
  -AdminApiKey "<admin-key>"
```

Use `-DryRun` first when verifying deployment commands without applying changes.

### 5. Run the release-readiness gate

After deployment, run the strict end-to-end validation gate:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\release-readiness.ps1 `
  -BackendUrl "https://<backend-domain>" `
  -FrontendUrl "https://<frontend-domain>" `
  -DatabaseUrl "postgresql+psycopg://<user>:<pass>@<host>:5432/<db>" `
  -CorsOrigins "https://<frontend-domain>" `
  -OperatorKey "<operator-key>" `
  -ReviewerKey "<reviewer-key>" `
  -AdminKey "<admin-key>" `
  -RequireExternal
```

This performs:
1. local foundation gate
2. environment validation
3. live API smoke checks

The expected success marker is:
- `RELEASE_READINESS_OK`

### 6. Validate the live application

Check the following in the deployed environment:
- backend responds at the public URL
- frontend loads successfully
- API routes return expected status codes
- review and admin protected checks work when keys are configured
- CORS and front-end backend connectivity remain correct

If the project is being released through GitHub Actions, use the workflow in [.github/workflows/release-readiness.yml](release-readiness.yml) and provide the production URL parameters as inputs.

## Rollback plan

If the production release fails or regresses after validation:

1. Stop the rollout and record the failure evidence.
2. Revert the deployment to the last known-good commit or previous Railway service revision.
3. Re-apply the previous working environment variables if they were changed.
4. Re-run the release-readiness gate against the previous stable target.
5. Notify the release owner and relevant stakeholders before reattempting the deployment.

Do not proceed with a second deployment until the failure cause and evidence are understood.

## Manual release example

Use the workflow in [.github/workflows/release-readiness.yml](workflows/release-readiness.yml) with values like the following:

- Backend URL: `https://backend-production-d15a.up.railway.app`
- Frontend URL: `https://frontend-production-8835.up.railway.app`
- CORS origins: `https://frontend-production-8835.up.railway.app`
- Model path: `ml_artifacts/ranker.joblib`
- Require external validation: `true`

The workflow reads the database secret from GitHub Actions secrets as `RAILWAY_DATABASE_URL` and the protected role keys from:
- `RAILWAY_OPERATOR_KEY`
- `RAILWAY_REVIEWER_KEY`
- `RAILWAY_ADMIN_KEY`

## Approval and sign-off

Release approval requires all of the following:
- foundation checks passed
- deployment validation passed
- release-readiness script returned success
- no blocking production issue remains
- release owner confirms the application is healthy

## Operational notes

- Keep the production backend/front-end URLs, database URL, and role keys aligned with the live Railway environment.
- Prefer validating the live environment over assuming a local run is equivalent to production.
- Use the release-readiness flow as the final gate before a production release is considered complete.
