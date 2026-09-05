<#
.SYNOPSIS
    GCP Infrastructure Setup Script for Lienmark (Windows PowerShell).
    Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon.
#>
[CmdletBinding()]
param (
    [string]$ProjectId = $(if ($env:GOOGLE_CLOUD_PROJECT) { $env:GOOGLE_CLOUD_PROJECT } else { "benchpress-ai-cloud" }),
    [string]$Region = $(if ($env:GCP_REGION) { $env:GCP_REGION } else { "us-central1" }),
    [string]$ServiceAccountName = "lienmark-sa",
    [string]$RepoName = "lienmark-repo"
)

$ErrorActionPreference = "Stop"
$ServiceAccount = "${ServiceAccountName}@${ProjectId}.iam.gserviceaccount.com"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ">> 🛠️ SETTING UP GCP INFRASTRUCTURE FOR LIENMARK (PowerShell)" -ForegroundColor Cyan
Write-Host "   Project:         $ProjectId"
Write-Host "   Region:          $Region"
Write-Host "   Service Account: $ServiceAccount"
Write-Host "======================================================================" -ForegroundColor Cyan

# Locate gcloud.cmd to bypass PowerShell script execution policy issues
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

# 1. Set gcloud project and region
& $gcloudCmd config set project $ProjectId
& $gcloudCmd config set run/region $Region

# 2. Enable Required APIs
Write-Host "--> Enabling Google Cloud APIs..." -ForegroundColor Yellow
& $gcloudCmd services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    secretmanager.googleapis.com `
    artifactregistry.googleapis.com `
    aiplatform.googleapis.com `
    compute.googleapis.com

# 3. Create Artifact Registry Docker Repository
Write-Host "--> Provisioning Artifact Registry repository '$RepoName'..." -ForegroundColor Yellow
$repoCheck = (& $gcloudCmd artifacts repositories describe $RepoName --location=$Region --project=$ProjectId 2>&1)
if ($LASTEXITCODE -ne 0) {
    & $gcloudCmd artifacts repositories create $RepoName `
        --repository-format=docker `
        --location=$Region `
        --project=$ProjectId `
        --description="Lienmark Container Repository"
    Write-Host "  [OK] Artifact Registry repository created" -ForegroundColor Green
} else {
    Write-Host "  [OK] Artifact Registry repository already exists" -ForegroundColor Gray
}

# 4. Create Service Account
Write-Host "--> Configuring Service Account '$ServiceAccount'..." -ForegroundColor Yellow
$saCheck = (& $gcloudCmd iam service-accounts describe $ServiceAccount --project=$ProjectId 2>&1)
if ($LASTEXITCODE -ne 0) {
    & $gcloudCmd iam service-accounts create $ServiceAccountName `
        --display-name="Lienmark Cloud Run Service Account" `
        --project=$ProjectId
    Write-Host "  [OK] Service Account created" -ForegroundColor Green
} else {
    Write-Host "  [OK] Service Account already exists" -ForegroundColor Gray
}

# 5. Grant Least-Privilege IAM Roles
Write-Host "--> Assigning IAM Roles to Service Account..." -ForegroundColor Yellow
$Roles = @(
    "roles/run.admin",
    "roles/storage.admin",
    "roles/cloudbuild.builds.editor",
    "roles/secretmanager.secretAccessor",
    "roles/aiplatform.user"
)

foreach ($Role in $Roles) {
    Write-Host "  Assigning $Role..." -ForegroundColor Gray
    & $gcloudCmd projects add-iam-policy-binding $ProjectId `
        --member="serviceAccount:$ServiceAccount" `
        --role=$Role `
        --condition=None | Out-Null
}

Write-Host "=== ✅ GCP SETUP COMPLETE ===" -ForegroundColor Green
Write-Host "Project $ProjectId is ready for Lienmark Cloud Run deployment." -ForegroundColor Cyan
