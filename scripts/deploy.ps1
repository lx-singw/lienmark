<#
.SYNOPSIS
    Production Deployment Script for Lienmark on Google Cloud Run (Windows PowerShell).
    Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon.

.DESCRIPTION
    Builds and deploys the unified Lienmark FastAPI and Reviewer Dashboard service to Google Cloud Run.
    Supports Google Cloud Secret Manager or direct environment variable injection.

.PARAMETER ProjectId
    Google Cloud Project ID (default: $env:GOOGLE_CLOUD_PROJECT or 'benchpress-ai-cloud').
.PARAMETER Region
    Google Cloud Region (default: $env:GCP_REGION or 'us-central1').
.PARAMETER ServiceName
    Cloud Run service name (default: 'lienmark').
.PARAMETER UseSecretManager
    Flag to inject secrets via Google Cloud Secret Manager instead of env vars.
#>
[CmdletBinding()]
param (
    [string]$ProjectId = $(if ($env:GOOGLE_CLOUD_PROJECT) { $env:GOOGLE_CLOUD_PROJECT } else { "benchpress-ai-cloud" }),
    [string]$Region = $(if ($env:GCP_REGION) { $env:GCP_REGION } else { "us-central1" }),
    [string]$ServiceName = "lienmark",
    [string]$RepoName = "lienmark-repo",
    [string]$ServiceAccount = "",
    [string]$CpuLimit = "2",
    [string]$MemoryLimit = "2Gi",
    [int]$MinInstances = 0,
    [int]$MaxInstances = 10,
    [int]$Concurrency = 80,
    [int]$Timeout = 300,
    [switch]$UseSecretManager,
    [string]$ParallelApiKey = $env:PARALLEL_API_KEY,
    [string]$GeminiApiKey = $env:GEMINI_API_KEY
)

$ErrorActionPreference = "Stop"

# Resolve directories
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

if (-not $ServiceAccount) {
    $ServiceAccount = "lienmark-sa@$ProjectId.iam.gserviceaccount.com"
}

$ImageTag = "${Region}-docker.pkg.dev/${ProjectId}/${RepoName}/${ServiceName}:latest"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ">> 🚀 DEPLOYING LIENMARK TO GOOGLE CLOUD RUN (PowerShell)" -ForegroundColor Cyan
Write-Host "   Service:         $ServiceName"
Write-Host "   Project:         $ProjectId"
Write-Host "   Region:          $Region"
Write-Host "   Image:           $ImageTag"
Write-Host "   Service Account: $ServiceAccount"
Write-Host "   Resources:       $CpuLimit CPU, $MemoryLimit RAM"
Write-Host "======================================================================" -ForegroundColor Cyan

# Check for gcloud CLI
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Error "Google Cloud SDK ('gcloud') is not installed or not available in PATH. Please install Google Cloud CLI."
    exit 1
}

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

# Update API keys if sourced from .env
if (-not $ParallelApiKey -and $env:PARALLEL_API_KEY) { $ParallelApiKey = $env:PARALLEL_API_KEY }
if (-not $GeminiApiKey -and $env:GEMINI_API_KEY) { $GeminiApiKey = $env:GEMINI_API_KEY }

# Build environment variables
$EnvVars = @(
    "ENVIRONMENT=production",
    "GOOGLE_CLOUD_PROJECT=$ProjectId",
    "GOOGLE_CLOUD_REGION=$Region"
)

if ($ParallelApiKey) {
    $EnvVars += "PARALLEL_API_KEY=$ParallelApiKey"
    Write-Host "  [OK] Attached PARALLEL_API_KEY environment variable (masked: $(if ($ParallelApiKey.Length -gt 8) { $ParallelApiKey.Substring(0,4) + '...' + $ParallelApiKey.Substring($ParallelApiKey.Length - 4) } else { '***' }))" -ForegroundColor Green
} else {
    Write-Host "  [INFO] PARALLEL_API_KEY not provided (will operate in deterministic mock mode)" -ForegroundColor Yellow
}

if ($GeminiApiKey) {
    $EnvVars += "GEMINI_API_KEY=$GeminiApiKey"
    Write-Host "  [OK] Attached GEMINI_API_KEY environment variable (masked: $(if ($GeminiApiKey.Length -gt 8) { $GeminiApiKey.Substring(0,4) + '...' + $GeminiApiKey.Substring($GeminiApiKey.Length - 4) } else { '***' }))" -ForegroundColor Green
} else {
    Write-Host "  [INFO] GEMINI_API_KEY not provided (will operate in deterministic mock mode)" -ForegroundColor Yellow
}

$EnvVarsString = $EnvVars -join ","

# Configure Secret Manager arguments
$SecretArgs = @()
if ($UseSecretManager) {
    Write-Host "--> Using Google Cloud Secret Manager for credentials..." -ForegroundColor Gray
    $SecretArgs = @("--set-secrets=PARALLEL_API_KEY=parallel-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest")
}

# Step 1: Submit build via Cloud Build
Write-Host "`n--> Step 1: Building container image via Google Cloud Build..." -ForegroundColor Yellow
Push-Location $RootDir
try {
    & gcloud builds submit `
        --tag $ImageTag `
        --project $ProjectId `
        .
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Cloud Build failed with exit code $LASTEXITCODE."
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

# Step 2: Deploy to Cloud Run
Write-Host "`n--> Step 2: Deploying '$ServiceName' to Cloud Run..." -ForegroundColor Yellow
$DeployArgs = @(
    "run", "deploy", $ServiceName,
    "--image", $ImageTag,
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
    "--set-env-vars", $EnvVarsString
)

if ($SecretArgs.Count -gt 0) {
    $DeployArgs += $SecretArgs
}

& gcloud @DeployArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Cloud Run deployment failed with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}

# Step 3: Fetch status URL
Write-Host "`n=== ✅ DEPLOYMENT COMPLETE ===" -ForegroundColor Green
$ServiceUrl = (& gcloud run services describe $ServiceName `
    --platform managed `
    --region $Region `
    --project $ProjectId `
    --format "value(status.url)").Trim()

Write-Host "Service URL:       $ServiceUrl" -ForegroundColor Cyan
Write-Host "Health Endpoint:   $ServiceUrl/health" -ForegroundColor Gray
Write-Host "Readiness:         $ServiceUrl/readyz" -ForegroundColor Gray
Write-Host "Fixtures Endpoint: $ServiceUrl/api/fixtures" -ForegroundColor Gray
Write-Host "SSR Report (E&O):  $ServiceUrl/report/proj_blockbuster_cinema" -ForegroundColor Gray
Write-Host "Review Dashboard:  $ServiceUrl/" -ForegroundColor Cyan
