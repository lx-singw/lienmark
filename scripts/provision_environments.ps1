<#
.SYNOPSIS
    Idempotent GCP Multi-Project Provisioning Script for Lienmark (Windows PowerShell).
    Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon.

.DESCRIPTION
    Provisions two isolated GCP environments:
    - Development: lienmark-dev-lx-2026 (Display: 'Lienmark Development')
    - Judge Demo:  lienmark-demo-lx-2026 (Display: 'Lienmark Judge Demo')
    Links both projects to master billing account 01575B-23EAEE-CF5627.
    Enables required Google Cloud APIs, provisions Firestore Native mode,
    Artifact Registry Docker repositories, least-privilege service accounts,
    and granular budget alerts ($20 dev / $60 demo / $20 unallocated reserve).

.PARAMETER TargetEnvironment
    Target environment to provision: 'all', 'dev', or 'demo' (default: 'all').
.PARAMETER BillingAccount
    Master Cloud Billing Account ID (default: '01575B-23EAEE-CF5627').
.PARAMETER Region
    Google Cloud Region for compute, repository, and database (default: 'us-central1').
.PARAMETER DryRun
    Simulates provisioning steps without executing GCP mutations.
.PARAMETER SkipBudget
    Skips Cloud Billing budget creation.
#>
[CmdletBinding()]
param (
    [ValidateSet("all", "dev", "demo")]
    [string]$TargetEnvironment = "all",
    [string]$BillingAccount = "01575B-23EAEE-CF5627",
    [string]$Region = "us-central1",
    [switch]$DryRun,
    [switch]$SkipBudget
)

$ErrorActionPreference = "Stop"

# Resolve directories
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

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

function Test-GCloudResourceExists {
    param([scriptblock]$Probe)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        & $Probe 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $prev
    }
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ">> 🛠️  LIENMARK MULTI-PROJECT GCP PROVISIONING (PowerShell)" -ForegroundColor Cyan
Write-Host "   Target Environment: $TargetEnvironment"
Write-Host "   Billing Account:    $BillingAccount"
Write-Host "   Primary Region:     $Region"
Write-Host "   GCloud CLI Path:    $gcloudCmd"
Write-Host "   Dry Run Mode:       $(if ($DryRun) { 'ENABLED' } else { 'DISABLED' })"
Write-Host "======================================================================" -ForegroundColor Cyan

# Environment Topology Definitions
$Environments = @()

if ($TargetEnvironment -eq "all" -or $TargetEnvironment -eq "dev") {
    $Environments += [PSCustomObject]@{
        Key           = "dev"
        ProjectId     = "lienmark-dev-lx-2026"
        DisplayName   = "Lienmark Development"
        SAName        = "lienmark-dev-sa"
        BudgetAmount  = "20USD"
        BudgetDisplay = "lienmark-dev-budget-20usd"
        Thresholds    = @("0.25", "0.50", "0.75", "0.90", "1.00")
    }
}

if ($TargetEnvironment -eq "all" -or $TargetEnvironment -eq "demo") {
    $Environments += [PSCustomObject]@{
        Key           = "demo"
        ProjectId     = "lienmark-demo-lx-2026"
        DisplayName   = "Lienmark Judge Demo"
        SAName        = "lienmark-demo-sa"
        BudgetAmount  = "60USD"
        BudgetDisplay = "lienmark-demo-budget-60usd"
        Thresholds    = @("0.50", "0.75", "0.90", "1.00")
    }
}

# Required Google Cloud APIs
$RequiredApis = @(
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "firestore.googleapis.com",
    "aiplatform.googleapis.com",
    "compute.googleapis.com"
)

# Least-Privilege IAM Roles
$LeastPrivilegeRoles = @(
    "roles/run.admin",
    "roles/storage.admin",
    "roles/cloudbuild.builds.editor",
    "roles/secretmanager.secretAccessor",
    "roles/aiplatform.user",
    "roles/datastore.user"
)

# Process each target environment
foreach ($envDef in $Environments) {
    $projId = $envDef.ProjectId
    $displayName = $envDef.DisplayName
    $saEmail = "$($envDef.SAName)@$projId.iam.gserviceaccount.com"

    Write-Host "`n----------------------------------------------------------------------" -ForegroundColor Yellow
    Write-Host ">> Configuring Environment: [$($envDef.Key.ToUpper())] -> $projId" -ForegroundColor Yellow
    Write-Host "   Display Name:     $displayName"
    Write-Host "   Service Account:  $saEmail"
    Write-Host "   Budget Allotment: $($envDef.BudgetAmount)"
    Write-Host "----------------------------------------------------------------------" -ForegroundColor Yellow

    if ($DryRun) {
        Write-Host "  [DRY-RUN] Would verify/create project '$projId' ('$displayName')." -ForegroundColor Magenta
        Write-Host "  [DRY-RUN] Would link project to billing account '$BillingAccount'." -ForegroundColor Magenta
        Write-Host "  [DRY-RUN] Would enable APIs: $($RequiredApis -join ', ')." -ForegroundColor Magenta
        Write-Host "  [DRY-RUN] Would ensure Firestore Native mode '(default)' in '$Region'." -ForegroundColor Magenta
        Write-Host "  [DRY-RUN] Would ensure Artifact Registry 'lienmark-repo' in '$Region'." -ForegroundColor Magenta
        Write-Host "  [DRY-RUN] Would ensure Service Account '$saEmail' and grant IAM roles." -ForegroundColor Magenta
        if (-not $SkipBudget) {
            Write-Host "  [DRY-RUN] Would configure budget '$($envDef.BudgetDisplay)' with thresholds: $($envDef.Thresholds -join ', ')." -ForegroundColor Magenta
        }
        continue
    }

    # 1. Project Creation
    Write-Host "--> [1/7] Ensuring Google Cloud Project '$projId'..." -ForegroundColor Cyan
    $projExists = Test-GCloudResourceExists { & $gcloudCmd projects describe $projId }
    if (-not $projExists) {
        Write-Host "    Project not found. Creating project '$projId'..." -ForegroundColor Yellow
        & $gcloudCmd projects create $projId --name=$displayName
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to create project '$projId'."
            exit $LASTEXITCODE
        }
        Write-Host "    [OK] Project '$projId' successfully created." -ForegroundColor Green
    } else {
        Write-Host "    [OK] Project '$projId' already exists." -ForegroundColor Gray
    }

    # 2. Link Billing Account
    Write-Host "--> [2/7] Linking Project to Billing Account '$BillingAccount'..." -ForegroundColor Cyan
    $currentBilling = ""
    try {
        $prevEA = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        $currentBilling = (& $gcloudCmd billing projects describe $projId --format="value(billingAccountName)" 2>$null)
        $ErrorActionPreference = $prevEA
    } catch {
        $currentBilling = ""
    }
    if ($currentBilling -notlike "*$BillingAccount*") {
        Write-Host "    Linking billing account '$BillingAccount' to '$projId'..." -ForegroundColor Yellow
        & $gcloudCmd billing projects link $projId --billing-account=$BillingAccount
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to link billing account to '$projId'."
            exit $LASTEXITCODE
        }
        Write-Host "    [OK] Project linked to billing account '$BillingAccount'." -ForegroundColor Green
    } else {
        Write-Host "    [OK] Project already linked to billing account '$BillingAccount'." -ForegroundColor Gray
    }

    # 3. Enable Required APIs
    Write-Host "--> [3/7] Enabling Required Google Cloud APIs..." -ForegroundColor Cyan
    & $gcloudCmd services enable @RequiredApis --project=$projId
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to enable required APIs for project '$projId'."
        exit $LASTEXITCODE
    }
    Write-Host "    [OK] All required APIs successfully enabled." -ForegroundColor Green

    # 4. Provision Firestore Native Mode
    Write-Host "--> [4/7] Ensuring Cloud Firestore in Native Mode (database: '(default)')..." -ForegroundColor Cyan
    $fsExists = Test-GCloudResourceExists { & $gcloudCmd firestore databases describe --database="(default)" --project=$projId }
    if (-not $fsExists) {
        Write-Host "    Creating Firestore (default) in Native Mode in region '$Region'..." -ForegroundColor Yellow
        & $gcloudCmd firestore databases create `
            --database="(default)" `
            --location=$Region `
            --type=firestore-native `
            --project=$projId
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to create Firestore (default) database in project '$projId'."
            exit $LASTEXITCODE
        }
        Write-Host "    [OK] Firestore Native database '(default)' created." -ForegroundColor Green
    } else {
        Write-Host "    [OK] Firestore Native database '(default)' already exists." -ForegroundColor Gray
    }

    # 5. Provision Artifact Registry Docker Repository
    Write-Host "--> [5/7] Ensuring Artifact Registry Docker Repository 'lienmark-repo'..." -ForegroundColor Cyan
    $repoExists = Test-GCloudResourceExists { & $gcloudCmd artifacts repositories describe "lienmark-repo" --location=$Region --project=$projId }
    if (-not $repoExists) {
        Write-Host "    Creating Artifact Registry Docker repository 'lienmark-repo'..." -ForegroundColor Yellow
        & $gcloudCmd artifacts repositories create "lienmark-repo" `
            --repository-format=docker `
            --location=$Region `
            --project=$projId `
            --description="Lienmark Container Repository ($($envDef.Key))"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to create Artifact Registry repository 'lienmark-repo' in project '$projId'."
            exit $LASTEXITCODE
        }
        Write-Host "    [OK] Artifact Registry repository 'lienmark-repo' created." -ForegroundColor Green
    } else {
        Write-Host "    [OK] Artifact Registry repository 'lienmark-repo' already exists." -ForegroundColor Gray
    }

    # 6. Service Account & Least-Privilege IAM Roles
    Write-Host "--> [6/7] Configuring Dedicated Service Account '$saEmail'..." -ForegroundColor Cyan
    $saExists = Test-GCloudResourceExists { & $gcloudCmd iam service-accounts describe $saEmail --project=$projId }
    if (-not $saExists) {
        Write-Host "    Creating Service Account '$($envDef.SAName)'..." -ForegroundColor Yellow
        & $gcloudCmd iam service-accounts create $envDef.SAName `
            --display-name="Lienmark $($envDef.Key.ToUpper()) Service Account" `
            --project=$projId
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to create Service Account '$($envDef.SAName)'."
            exit $LASTEXITCODE
        }
        Write-Host "    [OK] Service Account created." -ForegroundColor Green
    } else {
        Write-Host "    [OK] Service Account already exists." -ForegroundColor Gray
    }

    Write-Host "    Assigning least-privilege IAM roles..." -ForegroundColor Cyan
    foreach ($role in $LeastPrivilegeRoles) {
        & $gcloudCmd projects add-iam-policy-binding $projId `
            --member="serviceAccount:$saEmail" `
            --role=$role `
            --condition=None | Out-Null
        Write-Host "      + Granted $role" -ForegroundColor Gray
    }
    Write-Host "    [OK] Least-privilege IAM roles successfully bound." -ForegroundColor Green

    # 7. Configure Granular Budget Alerts
    if (-not $SkipBudget) {
        Write-Host "--> [7/7] Configuring Budget Alert '$($envDef.BudgetDisplay)' ($($envDef.BudgetAmount))..." -ForegroundColor Cyan
        $existingBudgets = ""
        try {
            $prevEA = $ErrorActionPreference
            $ErrorActionPreference = "SilentlyContinue"
            $existingBudgets = (& $gcloudCmd billing budgets list --billing-account=$BillingAccount --format="value(displayName)" 2>$null)
            $ErrorActionPreference = $prevEA
        } catch {
            $existingBudgets = ""
        }
        if ($existingBudgets -notcontains $envDef.BudgetDisplay) {
            Write-Host "    Creating budget with thresholds: $($envDef.Thresholds -join ', ')..." -ForegroundColor Yellow
            $budgetArgs = @(
                "billing", "budgets", "create",
                "--billing-account=$BillingAccount",
                "--display-name=$($envDef.BudgetDisplay)",
                "--budget-amount=$($envDef.BudgetAmount)",
                "--filter-projects=projects/$projId"
            )
            foreach ($th in $envDef.Thresholds) {
                $budgetArgs += "--threshold-rule=percent=$th,basis=current-spend"
            }
            & $gcloudCmd @budgetArgs
            if ($LASTEXITCODE -ne 0) {
                Write-Host "    [WARN] Budget creation returned exit code $LASTEXITCODE. Verify billing permissions." -ForegroundColor Yellow
            } else {
                Write-Host "    [OK] Budget alert '$($envDef.BudgetDisplay)' successfully provisioned." -ForegroundColor Green
            }
        } else {
            Write-Host "    [OK] Budget alert '$($envDef.BudgetDisplay)' already exists." -ForegroundColor Gray
        }
    } else {
        Write-Host "--> [7/7] Skipping budget alerts (flag -SkipBudget specified)." -ForegroundColor Gray
    }
}

Write-Host "`n======================================================================" -ForegroundColor Green
Write-Host ">> ✅ LIENMARK MULTI-PROJECT GCP PROVISIONING COMPLETE" -ForegroundColor Green
Write-Host "   Development Project: lienmark-dev-lx-2026"
Write-Host "   Judge Demo Project:  lienmark-demo-lx-2026"
Write-Host "   Billing Account:     $BillingAccount"
Write-Host "   Allocations:         Dev: `$20, Demo: `$60, Unallocated Reserve: `$20"
Write-Host "======================================================================" -ForegroundColor Green
