<#
.SYNOPSIS
    Release Promotion Pipeline to Judge Demo Environment (Windows PowerShell).
    Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon.

.DESCRIPTION
    Promotes tested, immutable release candidates from Development ('lienmark-dev-lx-2026')
    to Judge Demo ('lienmark-demo-lx-2026'):
    1. Reads verified image digests from output/release_manifest.json.
    2. Copies exact immutable digests between Artifact Registry repositories.
    3. Verifies bitwise SHA-256 digest equality.
    4. Deploys candidate revisions to Judge Demo Cloud Run with --no-traffic.
    5. Probes candidate revisions at /health and /readyz.
    6. Atomically shifts 100% of live traffic to verified candidate revisions.
    7. Emits audited promotion log to output/demo_promotion_log.json.

.PARAMETER ManifestPath
    Path to input release manifest (default: 'output/release_manifest.json').
.PARAMETER SourceProjectId
    Source Development GCP Project ID (default: 'lienmark-dev-lx-2026').
.PARAMETER TargetProjectId
    Target Judge Demo GCP Project ID (default: 'lienmark-demo-lx-2026').
.PARAMETER Region
    Google Cloud Region (default: 'us-central1').
.PARAMETER DryRun
    Simulates promotion pipeline, digest equality verification, and health probe without cloud mutations.
#>
[CmdletBinding()]
param (
    [string]$ManifestPath = "",
    [string]$SourceProjectId = "lienmark-dev-lx-2026",
    [string]$TargetProjectId = "lienmark-demo-lx-2026",
    [string]$Region = $(if ($env:GCP_REGION) { $env:GCP_REGION } else { "us-central1" }),
    [string]$RepoName = "lienmark-repo",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Resolve directories
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$OutputDir = Join-Path $RootDir "output"
if (-not $ManifestPath) {
    $ManifestPath = Join-Path $OutputDir "release_manifest.json"
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ">> 🚀 LIENMARK RELEASE PROMOTION PIPELINE: DEV -> DEMO (PowerShell)" -ForegroundColor Cyan
Write-Host "   Manifest Source: $ManifestPath"
Write-Host "   Source Project:  $SourceProjectId (Dev)"
Write-Host "   Target Project:  $TargetProjectId (Judge Demo)"
Write-Host "   Region:          $Region"
Write-Host "   Dry Run Mode:    $(if ($DryRun) { 'ENABLED' } else { 'DISABLED' })"
Write-Host "======================================================================" -ForegroundColor Cyan

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

# 1. Read Release Manifest
if (-not (Test-Path $ManifestPath)) {
    Write-Error "Release manifest not found at '$ManifestPath'. Run scripts/deploy.ps1 first."
    exit 1
}

Write-Host "--> [1/6] Ingesting release manifest from $ManifestPath..." -ForegroundColor Yellow
$ManifestRaw = Get-Content -Path $ManifestPath -Raw -Encoding UTF8
$Manifest = $ManifestRaw | ConvertFrom-Json

$GitCommit = $Manifest.git_commit
$GitCommitShort = if ($Manifest.git_commit_short) { $Manifest.git_commit_short } else { $GitCommit.Substring(0, 7) }

# Extract digests
$ApiSourceImage = $Manifest.images."lienmark-api".digest
$ApiSha256 = $Manifest.images."lienmark-api".sha256
$WebSourceImage = $Manifest.images."lienmark-web".digest
$WebSha256 = $Manifest.images."lienmark-web".sha256

if (-not $ApiSha256 -or -not $WebSha256) {
    Write-Error "Release manifest is missing immutable SHA-256 digests for lienmark-api or lienmark-web."
    exit 1
}

Write-Host "    Found Git Commit:  $GitCommitShort ($GitCommit)" -ForegroundColor Gray
Write-Host "    API Source Digest: $ApiSha256" -ForegroundColor Gray
Write-Host "    Web Source Digest: $WebSha256" -ForegroundColor Gray

$TargetApiDigestRef = "${Region}-docker.pkg.dev/${TargetProjectId}/${RepoName}/lienmark-api@${ApiSha256}"
$TargetWebDigestRef = "${Region}-docker.pkg.dev/${TargetProjectId}/${RepoName}/lienmark-web@${WebSha256}"
$TargetApiTagRef = "${Region}-docker.pkg.dev/${TargetProjectId}/${RepoName}/lienmark-api:${GitCommitShort}"
$TargetWebTagRef = "${Region}-docker.pkg.dev/${TargetProjectId}/${RepoName}/lienmark-web:${GitCommitShort}"

# Dry Run Simulation
if ($DryRun) {
    Write-Host "`n[DRY-RUN] Simulating promotion pipeline DEV -> DEMO..." -ForegroundColor Magenta
    Write-Host "  [DRY-RUN] Step 2: Copying immutable digests to $TargetProjectId..." -ForegroundColor Magenta
    Write-Host "  [DRY-RUN] Step 3: Verifying SHA-256 digest equality ($ApiSha256 == $ApiSha256)..." -ForegroundColor Magenta
    Write-Host "  [DRY-RUN] Step 4: Deploying candidate revisions to Cloud Run with --no-traffic --tag=candidate..." -ForegroundColor Magenta
    Write-Host "  [DRY-RUN] Step 5: Probing candidate endpoints (/health, /readyz) -> HTTP 200 OK..." -ForegroundColor Magenta
    Write-Host "  [DRY-RUN] Step 6: Atomically shifting 100% live traffic to candidate revisions..." -ForegroundColor Magenta

    $syntheticPromotionLog = [PSCustomObject]@{
        status             = "SUCCESS"
        promoted_at        = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        source_environment = "dev"
        source_project     = $SourceProjectId
        target_environment = "demo"
        target_project     = $TargetProjectId
        region             = $Region
        git_commit         = $GitCommit
        git_commit_short   = $GitCommitShort
        services           = [PSCustomObject]@{
            "lienmark-api" = [PSCustomObject]@{
                source_digest      = $ApiSourceImage
                target_digest      = $TargetApiDigestRef
                sha256             = $ApiSha256
                digest_match       = $true
                candidate_revision = "lienmark-api-candidate-dryrun"
                candidate_url      = "https://candidate---lienmark-api-dryrun.a.run.app"
                health_check       = "PASSED"
                traffic_percent    = 100
            }
            "lienmark-web" = [PSCustomObject]@{
                source_digest      = $WebSourceImage
                target_digest      = $TargetWebDigestRef
                sha256             = $WebSha256
                digest_match       = $true
                candidate_revision = "lienmark-web-candidate-dryrun"
                candidate_url      = "https://candidate---lienmark-web-dryrun.a.run.app"
                health_check       = "PASSED"
                traffic_percent    = 100
            }
        }
    }

    $LogPath = Join-Path $OutputDir "demo_promotion_log.json"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($LogPath, ($syntheticPromotionLog | ConvertTo-Json -Depth 10), $utf8NoBom)
    Write-Host "`n=== ✅ DRY-RUN PROMOTION COMPLETE ===" -ForegroundColor Green
    Write-Host "Promotion Log written to: $LogPath" -ForegroundColor Cyan
    exit 0
}

# 2. Copy Immutable Images to Judge Demo Artifact Registry
Write-Host "`n--> [2/6] Copying exact immutable images to Judge Demo repository..." -ForegroundColor Yellow

function Copy-ContainerImage {
    param (
        [string]$SourceRef,
        [string]$TargetRef,
        [string]$TargetTagRef
    )
    Write-Host "    Transferring $SourceRef -> $TargetTagRef..." -ForegroundColor Gray

    # Strategy A: gcrane / crane if available
    $craneCmd = (Get-Command "gcrane" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
    if (-not $craneCmd) {
        $craneCmd = (Get-Command "crane" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
    }

    if ($craneCmd) {
        Write-Host "    Using local crane binary ($craneCmd)..." -ForegroundColor Gray
        & $craneCmd cp $SourceRef $TargetTagRef
        if ($LASTEXITCODE -ne 0) {
            Write-Error "crane copy failed for $SourceRef"
            exit $LASTEXITCODE
        }
    } else {
        # Strategy B: Remote Cloud Build worker running gcrane directly inside GCP
        Write-Host "    Using remote Cloud Build container copy step (gcr.io/go-containerregistry/gcrane)..." -ForegroundColor Gray
        $buildConfig = @"
steps:
- name: 'gcr.io/go-containerregistry/gcrane:latest'
  args: ['cp', '$SourceRef', '$TargetTagRef']
"@
        $tempBuildFile = Join-Path $OutputDir "temp_build_copy.yaml"
        $buildConfig | Set-Content -Path $tempBuildFile -Encoding UTF8
        try {
            & $gcloudCmd builds submit --no-source --config=$tempBuildFile --project=$TargetProjectId
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Cloud Build gcrane transfer failed."
                exit $LASTEXITCODE
            }
        } finally {
            if (Test-Path $tempBuildFile) { Remove-Item $tempBuildFile -Force }
        }
    }
}

Copy-ContainerImage -SourceRef $ApiSourceImage -TargetRef $TargetApiDigestRef -TargetTagRef $TargetApiTagRef
Copy-ContainerImage -SourceRef $WebSourceImage -TargetRef $TargetWebDigestRef -TargetTagRef $TargetWebTagRef

# 3. Verify SHA-256 Digest Equality
Write-Host "`n--> [3/6] Verifying immutable SHA-256 digest equality..." -ForegroundColor Yellow

$TargetApiActualSha = (& $gcloudCmd artifacts docker images describe $TargetApiTagRef --project=$TargetProjectId --format="value(image_summary.digest)").Trim()
$TargetWebActualSha = (& $gcloudCmd artifacts docker images describe $TargetWebTagRef --project=$TargetProjectId --format="value(image_summary.digest)").Trim()

Write-Host "    Source API Digest: $ApiSha256" -ForegroundColor Gray
Write-Host "    Target API Digest: $TargetApiActualSha" -ForegroundColor Gray
if ($ApiSha256 -ne $TargetApiActualSha) {
    Write-Error "CRITICAL: Digest mismatch for lienmark-api! Expected '$ApiSha256', got '$TargetApiActualSha'."
    exit 1
}
Write-Host "    [OK] API SHA-256 digest equality verified." -ForegroundColor Green

Write-Host "    Source Web Digest: $WebSha256" -ForegroundColor Gray
Write-Host "    Target Web Digest: $TargetWebActualSha" -ForegroundColor Gray
if ($WebSha256 -ne $TargetWebActualSha) {
    Write-Error "CRITICAL: Digest mismatch for lienmark-web! Expected '$WebSha256', got '$TargetWebActualSha'."
    exit 1
}
Write-Host "    [OK] Web SHA-256 digest equality verified." -ForegroundColor Green

# 4. Deploy Candidate Revisions with --no-traffic
Write-Host "`n--> [4/6] Deploying candidate revisions to Judge Demo Cloud Run (--no-traffic)..." -ForegroundColor Yellow
$DemoServiceAccount = "lienmark-demo-sa@$TargetProjectId.iam.gserviceaccount.com"

# Deploy lienmark-api candidate
Write-Host "    Deploying candidate for 'lienmark-api'..." -ForegroundColor Gray
& $gcloudCmd run deploy lienmark-api `
    --image=$TargetApiDigestRef `
    --no-traffic `
    --tag="candidate" `
    --platform="managed" `
    --region=$Region `
    --project=$TargetProjectId `
    --service-account=$DemoServiceAccount `
    --cpu="2" `
    --memory="2Gi" `
    --min-instances=0 `
    --max-instances=10 `
    --concurrency=80 `
    --timeout=300 `
    --port=8080 `
    --allow-unauthenticated `
    --set-env-vars="ENVIRONMENT=demo,GOOGLE_CLOUD_PROJECT=$TargetProjectId,GOOGLE_CLOUD_REGION=$Region"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Candidate deployment failed for lienmark-api."
    exit $LASTEXITCODE
}

# Resolve candidate URL and revision name for API
$CandidateApiUrl = (& $gcloudCmd run services describe lienmark-api `
    --platform managed --region $Region --project $TargetProjectId `
    --flatten="status.traffic" --filter="status.traffic.tag=candidate" `
    --format="value(status.traffic.url)").Trim()

$CandidateApiRevision = (& $gcloudCmd run services describe lienmark-api `
    --platform managed --region $Region --project $TargetProjectId `
    --flatten="status.traffic" --filter="status.traffic.tag=candidate" `
    --format="value(status.traffic.revisionName)").Trim()

Write-Host "    [OK] Candidate Revision (API): $CandidateApiRevision ($CandidateApiUrl)" -ForegroundColor Green

# Deploy lienmark-web candidate
Write-Host "    Deploying candidate for 'lienmark-web'..." -ForegroundColor Gray
& $gcloudCmd run deploy lienmark-web `
    --image=$TargetWebDigestRef `
    --no-traffic `
    --tag="candidate" `
    --platform="managed" `
    --region=$Region `
    --project=$TargetProjectId `
    --service-account=$DemoServiceAccount `
    --cpu="1" `
    --memory="1Gi" `
    --min-instances=0 `
    --max-instances=10 `
    --port=8080 `
    --allow-unauthenticated `
    --set-env-vars="NODE_ENV=production,NEXT_PUBLIC_BACKEND_URL=$CandidateApiUrl,INTERNAL_BACKEND_URL=$CandidateApiUrl"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Candidate deployment failed for lienmark-web."
    exit $LASTEXITCODE
}

# Resolve candidate URL and revision name for Web
$CandidateWebUrl = (& $gcloudCmd run services describe lienmark-web `
    --platform managed --region $Region --project $TargetProjectId `
    --flatten="status.traffic" --filter="status.traffic.tag=candidate" `
    --format="value(status.traffic.url)").Trim()

$CandidateWebRevision = (& $gcloudCmd run services describe lienmark-web `
    --platform managed --region $Region --project $TargetProjectId `
    --flatten="status.traffic" --filter="status.traffic.tag=candidate" `
    --format="value(status.traffic.revisionName)").Trim()

Write-Host "    [OK] Candidate Revision (Web): $CandidateWebRevision ($CandidateWebUrl)" -ForegroundColor Green

# 5. Probing Candidate Revisions at /health and /readyz
Write-Host "`n--> [5/6] Probing candidate revision health and readiness..." -ForegroundColor Yellow

function Probe-Endpoint {
    param ([string]$Url, [int]$MaxAttempts = 12, [int]$DelaySec = 3)
    Write-Host "    Probing $Url..." -ForegroundColor Gray
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) {
                Write-Host "    [OK] $Url returned 200 OK on attempt $i." -ForegroundColor Green
                return $true
            }
        } catch {
            # continue loop
        }
        Start-Sleep -Seconds $DelaySec
    }
    return $false
}

$apiHealthPass = Probe-Endpoint -Url "$CandidateApiUrl/health"
$apiReadyzPass = Probe-Endpoint -Url "$CandidateApiUrl/readyz"
$webHealthPass = Probe-Endpoint -Url "$CandidateWebUrl/"

if (-not $apiHealthPass -or -not $apiReadyzPass -or -not $webHealthPass) {
    Write-Error "CRITICAL: Candidate revision failed health/readiness probe! Aborting cutover. Live traffic remains 100% on previous revisions."
    exit 1
}
Write-Host "    [OK] All candidate health and readiness probes PASSED." -ForegroundColor Green

# 6. Atomic 100% Traffic Shift
Write-Host "`n--> [6/6] Executing atomic 100% live traffic cutover..." -ForegroundColor Yellow

& $gcloudCmd run services update-traffic lienmark-api `
    --platform=managed --region=$Region --project=$TargetProjectId `
    --to-revisions="${CandidateApiRevision}=100"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to update traffic for lienmark-api."
    exit $LASTEXITCODE
}
Write-Host "    [OK] 100% traffic shifted to $CandidateApiRevision." -ForegroundColor Green

& $gcloudCmd run services update-traffic lienmark-web `
    --platform=managed --region=$Region --project=$TargetProjectId `
    --to-revisions="${CandidateWebRevision}=100"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to update traffic for lienmark-web."
    exit $LASTEXITCODE
}
Write-Host "    [OK] 100% traffic shifted to $CandidateWebRevision." -ForegroundColor Green

# 7. Emit Promotion Confirmation Log
$PromotionLog = [PSCustomObject]@{
    status             = "SUCCESS"
    promoted_at        = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    source_environment = "dev"
    source_project     = $SourceProjectId
    target_environment = "demo"
    target_project     = $TargetProjectId
    region             = $Region
    git_commit         = $GitCommit
    git_commit_short   = $GitCommitShort
    services           = [PSCustomObject]@{
        "lienmark-api" = [PSCustomObject]@{
            source_digest      = $ApiSourceImage
            target_digest      = $TargetApiDigestRef
            sha256             = $ApiSha256
            digest_match       = $true
            candidate_revision = $CandidateApiRevision
            candidate_url      = $CandidateApiUrl
            health_check       = "PASSED"
            traffic_percent    = 100
        }
        "lienmark-web" = [PSCustomObject]@{
            source_digest      = $WebSourceImage
            target_digest      = $TargetWebDigestRef
            sha256             = $WebSha256
            digest_match       = $true
            candidate_revision = $CandidateWebRevision
            candidate_url      = $CandidateWebUrl
            health_check       = "PASSED"
            traffic_percent    = 100
        }
    }
}

$LogPath = Join-Path $OutputDir "demo_promotion_log.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($LogPath, ($PromotionLog | ConvertTo-Json -Depth 10), $utf8NoBom)

Write-Host "`n=== ✅ RELEASE PROMOTION COMPLETE ===" -ForegroundColor Green
Write-Host "Promotion Log: $LogPath" -ForegroundColor Cyan
Write-Host "Judge Demo API: $(& $gcloudCmd run services describe lienmark-api --platform managed --region $Region --project $TargetProjectId --format 'value(status.url)')" -ForegroundColor Cyan
Write-Host "Judge Demo Web: $(& $gcloudCmd run services describe lienmark-web --platform managed --region $Region --project $TargetProjectId --format 'value(status.url)')" -ForegroundColor Cyan
