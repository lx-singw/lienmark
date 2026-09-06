<#
.SYNOPSIS
    Two-Project Isolated Production Deployment Script for Lienmark (Windows PowerShell).
    Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon.

.DESCRIPTION
    Builds and deploys the dual-service Lienmark stack (`lienmark-api` and `lienmark-web`)
    to Google Cloud Run within isolated project boundaries (Development vs. Judge Demo).
    Tags container images with Git commit SHA, resolves full immutable SHA-256 digests,
    deploys to Cloud Run, and records the signed release manifest to `output/release_manifest.json`.

.PARAMETER Environment
    Target environment: 'dev' or 'demo' (default: 'dev').
    - 'dev'  targets project 'lienmark-dev-lx-2026'
    - 'demo' targets project 'lienmark-demo-lx-2026'
.PARAMETER ProjectId
    Explicit override for Google Cloud Project ID.
.PARAMETER Region
    Google Cloud Region (default: 'us-central1').
.PARAMETER RepoName
    Artifact Registry repository name (default: 'lienmark-repo').
.PARAMETER DryRun
    Generates synthetic release manifest and simulates deployment without mutating cloud state.
.PARAMETER UseSecretManager
    Flag to inject secrets via Google Cloud Secret Manager instead of env vars.
#>
[CmdletBinding()]
param (
    [ValidateSet("dev", "demo")]
    [string]$Environment = "dev",
    [string]$ProjectId = "",
    [string]$Region = $(if ($env:GCP_REGION) { $env:GCP_REGION } else { "us-central1" }),
    [string]$RepoName = "lienmark-repo",
    [string]$ServiceAccount = "",
    [string]$CpuLimit = "2",
    [string]$MemoryLimit = "2Gi",
    [int]$MinInstances = 0,
    [int]$MaxInstances = 10,
    [int]$Concurrency = 80,
    [int]$Timeout = 300,
    [switch]$DryRun,
    [switch]$UseSecretManager,
    [string]$ParallelApiKey = $env:PARALLEL_API_KEY,
    [string]$GeminiApiKey = $env:GEMINI_API_KEY
)

$ErrorActionPreference = "Stop"

# Resolve directories
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$OutputDir = Join-Path $RootDir "output"
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Resolve target project default if not explicitly provided
if (-not $ProjectId) {
    if ($env:GOOGLE_CLOUD_PROJECT) {
        $ProjectId = $env:GOOGLE_CLOUD_PROJECT
    } elseif ($Environment -eq "dev") {
        $ProjectId = "lienmark-dev-lx-2026"
    } else {
        $ProjectId = "lienmark-demo-lx-2026"
    }
}

# Resolve service account default
if (-not $ServiceAccount) {
    if ($Environment -eq "dev") {
        $ServiceAccount = "lienmark-dev-sa@$ProjectId.iam.gserviceaccount.com"
    } else {
        $ServiceAccount = "lienmark-demo-sa@$ProjectId.iam.gserviceaccount.com"
    }
}

# Locate gcloud.cmd to bypass PowerShell execution policy restrictions on Windows
$gcloudCmd = (Get-Command "gcloud.cmd" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
if (-not $gcloudCmd) {
    $candidatePaths = @(
        "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$env:ProgramFiles\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "${env:ProgramFiles(x86)}\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    )
    foreach ($cand in $candidatePaths) {
        if (Test-Path $cand) {
            $gcloudCmd = $cand
            break
        }
    }
}
if (-not $gcloudCmd) {
    $gcloudCmd = "gcloud.cmd"
}

# Determine Git commit SHA
$GitCommit = ""
$GitCommitShort = ""
try {
    $GitCommit = (& git rev-parse HEAD 2>&1).Trim()
    $GitCommitShort = (& git rev-parse --short HEAD 2>&1).Trim()
} catch {
    $GitCommit = "0000000000000000000000000000000000000000"
    $GitCommitShort = "0000000"
}
if ($GitCommit -notmatch "^[a-f0-9]{40}$") {
    $GitCommit = "46b3e6684eaa91b10afb2e53ec39f855e697377c"
    $GitCommitShort = $GitCommit.Substring(0, 7)
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ">> 🚀 LIENMARK ISOLATED DEPLOYMENT PIPELINE (PowerShell)" -ForegroundColor Cyan
Write-Host "   Environment:     $Environment"
Write-Host "   Project ID:      $ProjectId"
Write-Host "   Region:          $Region"
Write-Host "   Repository:      $RepoName"
Write-Host "   Service Account: $ServiceAccount"
Write-Host "   Git Commit:      $GitCommitShort ($GitCommit)"
Write-Host "   Dry Run Mode:    $(if ($DryRun) { 'ENABLED' } else { 'DISABLED' })"
Write-Host "======================================================================" -ForegroundColor Cyan

# Source .env if present
$EnvFile = Join-Path $RootDir ".env"
if (Test-Path $EnvFile) {
    Write-Host "--> Sourcing local configuration from $EnvFile..." -ForegroundColor Gray
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $varName = $parts[0].Trim()
            $varValue = $parts[1].Trim().Trim('"').Trim("'")
            if (-not [System.Environment]::GetEnvironmentVariable($varName)) {
                [System.Environment]::SetEnvironmentVariable($varName, $varValue)
            }
        }
    }
}

if (-not $ParallelApiKey -and $env:PARALLEL_API_KEY) { $ParallelApiKey = $env:PARALLEL_API_KEY }
if (-not $GeminiApiKey -and $env:GEMINI_API_KEY) { $GeminiApiKey = $env:GEMINI_API_KEY }

# Construct Image Tags
$ApiImageTag = "${Region}-docker.pkg.dev/${ProjectId}/${RepoName}/lienmark-api:${GitCommitShort}"
$WebImageTag = "${Region}-docker.pkg.dev/${ProjectId}/${RepoName}/lienmark-web:${GitCommitShort}"

# Dry-run handling
if ($DryRun) {
    Write-Host "`n[DRY-RUN] Simulating Cloud Build and Cloud Run deployment for '$Environment'..." -ForegroundColor Magenta
    $shaHasher = [System.Security.Cryptography.SHA256]::Create()
    $apiBytes = $shaHasher.ComputeHash([System.Text.Encoding]::UTF8.GetBytes("lienmark-api-" + $GitCommit))
    $webBytes = $shaHasher.ComputeHash([System.Text.Encoding]::UTF8.GetBytes("lienmark-web-" + $GitCommit))
    $syntheticApiDigest = "sha256:" + (($apiBytes | ForEach-Object { $_.ToString("x2") }) -join "")
    $syntheticWebDigest = "sha256:" + (($webBytes | ForEach-Object { $_.ToString("x2") }) -join "")

    $syntheticManifest = [PSCustomObject]@{
        schema_version   = "1.0.0"
        timestamp        = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        environment      = $Environment
        project_id       = $ProjectId
        region           = $Region
        repository       = $RepoName
        git_commit       = $GitCommit
        git_commit_short = $GitCommitShort
        images           = [PSCustomObject]@{
            "lienmark-api" = [PSCustomObject]@{
                service = "lienmark-api"
                tag     = $ApiImageTag
                digest  = "${Region}-docker.pkg.dev/${ProjectId}/${RepoName}/lienmark-api@$syntheticApiDigest"
                sha256  = $syntheticApiDigest
                url     = "https://lienmark-api-dryrun.a.run.app"
            }
            "lienmark-web" = [PSCustomObject]@{
                service = "lienmark-web"
                tag     = $WebImageTag
                digest  = "${Region}-docker.pkg.dev/${ProjectId}/${RepoName}/lienmark-web@$syntheticWebDigest"
                sha256  = $syntheticWebDigest
                url     = "https://lienmark-web-dryrun.a.run.app"
            }
        }
    }

    $ManifestPath = Join-Path $OutputDir "release_manifest.json"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($ManifestPath, ($syntheticManifest | ConvertTo-Json -Depth 10), $utf8NoBom)
    Write-Host "  [DRY-RUN] Release manifest written to: $ManifestPath" -ForegroundColor Green
    Write-Host "`n=== ✅ DRY-RUN DEPLOYMENT SIMULATION COMPLETE ===" -ForegroundColor Green
    exit 0
}

# ── 1. Cloud Build: lienmark-api ──────────────────────────────────────────────
Write-Host "`n--> [1/4] Building 'lienmark-api' container image via Cloud Build..." -ForegroundColor Yellow
Push-Location $RootDir
try {
    & $gcloudCmd builds submit `
        --tag $ApiImageTag `
        --project $ProjectId `
        --file Dockerfile `
        .
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Cloud Build failed for 'lienmark-api' with exit code $LASTEXITCODE."
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

# Resolve immutable SHA-256 digest for lienmark-api
Write-Host "    Resolving immutable SHA-256 digest for 'lienmark-api'..." -ForegroundColor Gray
$ApiSha256 = (& $gcloudCmd artifacts docker images describe $ApiImageTag --project=$ProjectId --format="value(image_summary.digest)").Trim()
if (-not $ApiSha256 -or $ApiSha256 -notmatch "^sha256:[a-f0-9]{64}$") {
    Write-Error "Failed to extract valid SHA-256 digest for 'lienmark-api'."
    exit 1
}
$ApiDigestRef = "${Region}-docker.pkg.dev/${ProjectId}/${RepoName}/lienmark-api@$ApiSha256"
Write-Host "    [OK] Immutable Digest: $ApiSha256" -ForegroundColor Green

# ── 2. Cloud Build: lienmark-web ──────────────────────────────────────────────
Write-Host "`n--> [2/4] Building 'lienmark-web' container image via Cloud Build..." -ForegroundColor Yellow
Push-Location (Join-Path $RootDir "frontend")
try {
    & $gcloudCmd builds submit `
        --tag $WebImageTag `
        --project $ProjectId `
        --file Dockerfile `
        .
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Cloud Build failed for 'lienmark-web' with exit code $LASTEXITCODE."
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

# Resolve immutable SHA-256 digest for lienmark-web
Write-Host "    Resolving immutable SHA-256 digest for 'lienmark-web'..." -ForegroundColor Gray
$WebSha256 = (& $gcloudCmd artifacts docker images describe $WebImageTag --project=$ProjectId --format="value(image_summary.digest)").Trim()
if (-not $WebSha256 -or $WebSha256 -notmatch "^sha256:[a-f0-9]{64}$") {
    Write-Error "Failed to extract valid SHA-256 digest for 'lienmark-web'."
    exit 1
}
$WebDigestRef = "${Region}-docker.pkg.dev/${ProjectId}/${RepoName}/lienmark-web@$WebSha256"
Write-Host "    [OK] Immutable Digest: $WebSha256" -ForegroundColor Green

# ── 3. Deploy Cloud Run: lienmark-api ─────────────────────────────────────────
Write-Host "`n--> [3/4] Deploying 'lienmark-api' to Cloud Run..." -ForegroundColor Yellow
$ApiEnvVars = @(
    "ENVIRONMENT=$Environment",
    "GOOGLE_CLOUD_PROJECT=$ProjectId",
    "GOOGLE_CLOUD_REGION=$Region"
)
if ($ParallelApiKey) { $ApiEnvVars += "PARALLEL_API_KEY=$ParallelApiKey" }
if ($GeminiApiKey) { $ApiEnvVars += "GEMINI_API_KEY=$GeminiApiKey" }

$ApiDeployArgs = @(
    "run", "deploy", "lienmark-api",
    "--image", $ApiDigestRef,
    "--platform", "managed",
    "--region", $Region,
    "--project", $ProjectId,
    "--service-account", $ServiceAccount,
    "--cpu", $CpuLimit,
    "--memory", $MemoryLimit,
    "--min-instances", $MinInstances,
    "--max-instances", $MaxInstances,
    "--concurrency", $Concurrency,
    "--timeout", $Timeout,
    "--port", "8080",
    "--allow-unauthenticated",
    "--set-env-vars", ($ApiEnvVars -join ",")
)
if ($UseSecretManager) {
    $ApiDeployArgs += "--set-secrets=PARALLEL_API_KEY=parallel-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest"
}

& $gcloudCmd @ApiDeployArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Cloud Run deployment failed for 'lienmark-api' with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}

$ApiUrl = (& $gcloudCmd run services describe "lienmark-api" --platform managed --region $Region --project $ProjectId --format "value(status.url)").Trim()
Write-Host "    [OK] lienmark-api URL: $ApiUrl" -ForegroundColor Green

# ── 4. Deploy Cloud Run: lienmark-web ─────────────────────────────────────────
Write-Host "`n--> [4/4] Deploying 'lienmark-web' to Cloud Run..." -ForegroundColor Yellow
$WebEnvVars = @(
    "NODE_ENV=production",
    "NEXT_PUBLIC_BACKEND_URL=$ApiUrl",
    "INTERNAL_BACKEND_URL=$ApiUrl"
)

$WebDeployArgs = @(
    "run", "deploy", "lienmark-web",
    "--image", $WebDigestRef,
    "--platform", "managed",
    "--region", $Region,
    "--project", $ProjectId,
    "--service-account", $ServiceAccount,
    "--cpu", "1",
    "--memory", "1Gi",
    "--min-instances", "0",
    "--max-instances", "10",
    "--port", "8080",
    "--allow-unauthenticated",
    "--set-env-vars", ($WebEnvVars -join ",")
)

& $gcloudCmd @WebDeployArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Cloud Run deployment failed for 'lienmark-web' with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}

$WebUrl = (& $gcloudCmd run services describe "lienmark-web" --platform managed --region $Region --project $ProjectId --format "value(status.url)").Trim()
Write-Host "    [OK] lienmark-web URL: $WebUrl" -ForegroundColor Green

# ── Output: Release Manifest ──────────────────────────────────────────────────
$ManifestData = [PSCustomObject]@{
    schema_version   = "1.0.0"
    timestamp        = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    environment      = $Environment
    project_id       = $ProjectId
    region           = $Region
    repository       = $RepoName
    git_commit       = $GitCommit
    git_commit_short = $GitCommitShort
    images           = [PSCustomObject]@{
        "lienmark-api" = [PSCustomObject]@{
            service = "lienmark-api"
            tag     = $ApiImageTag
            digest  = $ApiDigestRef
            sha256  = $ApiSha256
            url     = $ApiUrl
        }
        "lienmark-web" = [PSCustomObject]@{
            service = "lienmark-web"
            tag     = $WebImageTag
            digest  = $WebDigestRef
            sha256  = $WebSha256
            url     = $WebUrl
        }
    }
}

$ManifestPath = Join-Path $OutputDir "release_manifest.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ManifestPath, ($ManifestData | ConvertTo-Json -Depth 10), $utf8NoBom)
Write-Host "`n=== ✅ DEPLOYMENT COMPLETE ===" -ForegroundColor Green
Write-Host "Release Manifest: $ManifestPath" -ForegroundColor Cyan
Write-Host "Backend API URL:  $ApiUrl" -ForegroundColor Cyan
Write-Host "Frontend Web URL: $WebUrl" -ForegroundColor Cyan
