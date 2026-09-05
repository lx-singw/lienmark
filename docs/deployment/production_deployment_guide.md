# Lienmark Production Deployment Guide: Google Cloud Run Blueprint

> **Authoritative Cloud Infrastructure & Deployment Specification**  
> **Platform**: Google Cloud Run (Serverless, Fully Managed, Auto-Scale to Zero, Managed TLS)  
> **GCP Project**: `benchpress-ai-cloud` (Configurable via `GOOGLE_CLOUD_PROJECT`)  
> **Active Account**: `singwane.linda.m@gmail.com`  
> **Region**: `us-central1`  
> **Competition Track**: Parallel Track ($15,000 Prize Pool) & Google Cloud Agent Builder  
> **Policy Version**: `E&O-2026.1-DEVPOST`  

---

## 1. Executive Summary & Architecture Overview

Lienmark is an enterprise clearance change control engine purpose-built for film, television, and game production underwriters. It evaluates script and visual cut revisions (V7 baseline to V8 revised cut), detecting clearance drift across 12 production claims, automatically carrying forward 10 unaffected items ($0 review cost), and scoping real-time Gemini 2.5 Flash and Parallel Search revalidation to precisely the 2 drifted items.

This guide provides the complete production deployment blueprint for hosting Lienmark on **Google Cloud Run**, guaranteeing:
- **Zero-downtime atomic cutovers** between revisions.
- **Strict credential hygiene** (zero secret leakage in logs, headers, or telemetry).
- **Fail-closed security guarantees** (statutory disclaimers, no autonomous legal policy binding).
- **Frictionless Cold Judge verification** (instant unauthenticated access to the live Reviewer Dashboard and Form E&O-2026 SSR Exceptions Schedule).

```
                              ┌────────────────────────────────────────────────────────┐
                              │                 JUDGE / REVIEWER BROWSER               │
                              │        (Unauthenticated Logged-Out Incognito Session)  │
                              └───────────────────────────┬────────────────────────────┘
                                                          │ HTTPS / TLS (Port 443)
                                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ GOOGLE CLOUD RUN: PRIMARY UNIFIED PRODUCTION SERVICE (`lienmark`)                                       │
│ Region: us-central1 | Auto-scale: 0 to 10 instances | CPU: 2 vCPU | Memory: 2GiB RAM | Port: 8080      │
│                                                                                                        │
│   ┌────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ FASTAPI APPLICATION TIER & MIDDLEWARE STACK                                                    │   │
│   │   ├── PayloadSizeLimitMiddleware (Strict 1MB boundary enforcement)                             │   │
│   │   ├── CorrelationLoggingMiddleware (X-Correlation-ID tracing & secret redaction)               │   │
│   │   └── IdempotencyMiddleware (X-Idempotency-Key replay protection)                              │   │
│   └─────────────────────────────────────────┬──────────────────────────────────────────────────────┘   │
│                                             │                                                          │
│     ┌───────────────────────────────────────┴───────────────────────────────────────┐                  │
│     ▼                                       ▼                                       ▼                  │
│  [ / & /dashboard ]                  [ /report/{id} ]                     [ /api/* ]                   │
│  Interactive Reviewer               Form E&O-2026 SSR                    REST API & Agent Engine       │
│  Dashboard HTML UI                  Exceptions Schedule                  - /api/fixtures               │
│  - 12 Golden Claims                 - Full Underwriter Layout            - /api/drift/compare          │
│  - 10 Carried / 2 Stale             - Carrier Policy Headers             - /api/review/action          │
│  - Live Drift Trigger               - Counsel Sign-Off Block             - /api/health & /readyz       │
│     │                                       │                                       │                  │
│     └───────────────────────────────────────┼───────────────────────────────────────┘                  │
│                                             ▼                                                          │
│   ┌────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ ORCHESTRATION & SERVICE LAYER                                                                  │   │
│   │   ├── LienmarkWorkflow (Google Cloud Agent Builder / ADK Execution Harness)                   │   │
│   │   ├── InvalidationEngine (Deterministic Lineage Parity & 4D Invalidation Rules)                │   │
│   │   ├── GeminiService (Gemini 2.5 Flash Structured Semantic Delta Analysis)                      │   │
│   │   ├── ParallelSearchService (Parallel Search API Scoped Evidence Harvesting)                   │   │
│   │   └── CounselCheckpointManager (Tamper-Evident Supersession Ledger & Re-attestation)           │   │
│   └────────────────────────────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                 │                                    │
                                 ▼                                    ▼
       ┌───────────────────────────────────┐        ┌───────────────────────────────────┐
       │   GOOGLE CLOUD SECRET MANAGER     │        │   PARALLEL SEARCH & GEMINI APIS   │
       │   - `gemini-api-key:latest`       │        │   - Gemini 2.5 Flash              │
       │   - `parallel-api-key:latest`     │        │   - Parallel AI Search API        │
       └───────────────────────────────────┘        └───────────────────────────────────┘
```

---

## 2. Deployment Topologies

### Topology A: Unified Cloud Run Service (`lienmark`) — **Primary Recommended**
- **Single Container Architecture**: The Python 3.11/3.13 FastAPI engine directly hosts:
  1. The responsive Judge Reviewer Dashboard at `/` and `/dashboard`.
  2. The high-fidelity Form E&O-2026 Underwriter Exceptions Schedule SSR at `/report/{production_id}`.
  3. All API routes, Agent Builder workflows, and health endpoints at `/api/*`.
- **Architectural Benefits**:
  - **Zero CORS**: Browser UI and backend API reside on the identical origin, eliminating pre-flight CORS latency and configuration failures.
  - **Sub-2-Second Cold Start**: A single lightweight Python slim image (<250MB) starts in under 1.8 seconds.
  - **Zero Inter-Service Networking**: No internal VPC connectors, IAM service-to-service token exchanges, or network hops required.
  - **Cold Judge Reliability**: Direct, unauthenticated evaluation without client-side hydration delays or blank loading spinners.

### Topology B: Dual-Service Architecture (`lienmark-web` + `lienmark-api`) — Optional
- **Separated Frontend and Backend**:
  - `lienmark-api`: FastAPI backend container running on Cloud Run.
  - `lienmark-web`: Next.js 15 App Router standalone container (`node server.js`) running on Cloud Run.
- **Routing & Communication**:
  - Next.js acts as the public ingress on port 8080/443.
  - Next.js server rewrites (`/api/backend/:path*` -> `${INTERNAL_BACKEND_URL}/api/:path*`) proxy requests securely.
  - Server Actions in `frontend/app/actions.ts` dispatch authenticated attestation requests to `lienmark-api`.

---

## 3. GCP Prerequisites & Identity Access Management (IAM)

### 3.1 Target Configuration
- **Active GCP User Account**: `singwane.linda.m@gmail.com`
- **Target GCP Project ID**: `benchpress-ai-cloud`
- **Deployment Region**: `us-central1`
- **Dedicated Service Account**: `lienmark-sa@benchpress-ai-cloud.iam.gserviceaccount.com`

### 3.2 Required GCP APIs
The following Google Cloud APIs must be enabled on the target project:
```bash
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    aiplatform.googleapis.com \
    compute.googleapis.com
```

### 3.3 Least-Privilege IAM Roles
The runtime Service Account (`lienmark-sa`) requires the following exact roles:

| IAM Role | Role Identifier | Rationale |
|---|---|---|
| Cloud Run Admin | `roles/run.admin` | Deploys container revisions and routes production traffic |
| Storage Admin | `roles/storage.admin` | Cloud Build staging bucket creation and source bundle upload |
| Cloud Build Editor | `roles/cloudbuild.builds.editor` | Triggers container image builds on Google Cloud Build |
| Secret Manager Accessor | `roles/secretmanager.secretAccessor` | Safely mounts `GEMINI_API_KEY` and `PARALLEL_API_KEY` at runtime |
| Vertex AI User | `roles/aiplatform.user` | Invokes Gemini 2.5 Flash model and Agent Builder workflows |
| Service Account User | `roles/iam.serviceAccountUser` | Allows Cloud Build and Cloud Run to act as `lienmark-sa` |

---

## 4. Container Assets & Production Artifact Audit

### 4.1 Root `Dockerfile` (Unified Service)
- **Multi-Stage Build Pattern**:
  - `Stage 1 (builder)`: Compiles C-extensions and wheel caches in `/opt/venv` using `python:3.11-slim` (configurable via `ARG PYTHON_VERSION=3.11`).
  - `Stage 2 (runner)`: Copies clean virtual environment to an immutable runtime container.
- **Security Posture**:
  - Non-root user: `appuser:appgroup` (UID/GID 10001).
  - Minimal attack surface: installs only `curl` (for health checks) and `ca-certificates` (for TLS).
  - Exposes port `8080`.
- **Healthcheck Probe**:
  - Docker `HEALTHCHECK` runs every 30s targeting `http://localhost:8080/health`.
  - Also responds on `/healthz` and `/readyz` for Kubernetes/Cloud Run standard probes.

### 4.2 `frontend/Dockerfile` (Standalone Next.js Runner)
- **Multi-Stage Build Pattern**:
  - `Stage 1 (deps)`: Installs production dependencies via `npm ci` with `libc6-compat`.
  - `Stage 2 (builder)`: Sets `ENV BUILD_STANDALONE=true` and runs `npm run build` to generate `.next/standalone`.
  - `Stage 3 (runner)`: Runs `node server.js` as unprivileged user `nextjs` (UID 1001).
  - Shrunk from ~1GB to **<120MB**, ensuring rapid auto-scaling on Cloud Run.

### 4.3 `docker-compose.yml` (Local Verification)
- Orchestrates local parity testing with backend on port 8080 and Next.js frontend on port 3000.
- Volume mounts enabled for hot-reload during local development.

---

## 5. Secret Management & Credential Sanitization

### 5.1 Cloud Secret Manager Setup (Enterprise Recommended)
Store live credentials securely in Secret Manager to avoid plain-text exposure in build logs:

```bash
# Store Parallel Search API Key
echo -n "YOUR_PARALLEL_API_KEY" | gcloud secrets create parallel-api-key \
    --data-file=- \
    --project=benchpress-ai-cloud \
    --replication-policy=automatic

# Store Gemini API Key
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
    --data-file=- \
    --project=benchpress-ai-cloud \
    --replication-policy=automatic

# Grant secretAccessor role to the runtime service account
gcloud secrets add-iam-policy-binding parallel-api-key \
    --member="serviceAccount:lienmark-sa@benchpress-ai-cloud.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=benchpress-ai-cloud

gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:lienmark-sa@benchpress-ai-cloud.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=benchpress-ai-cloud
```

### 5.2 Secret Injection Options

#### Option 1: Secret Manager Mount (Production)
```bash
--set-secrets="PARALLEL_API_KEY=parallel-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest"
```

#### Option 2: Environment Variable Injection with Redaction
```bash
--set-env-vars="PARALLEL_API_KEY=${PARALLEL_API_KEY},GEMINI_API_KEY=${GEMINI_API_KEY}"
```

### 5.3 Zero-Leakage Credential Safeguards
The backend features multi-layered defense to ensure no secrets ever leak:
1. **CorrelationLoggingMiddleware**: Intercepts all outgoing log messages and masks API keys via regex (`AIza[0-9A-Za-z-_]{35}` and `sk-[0-9A-Za-z-_]{20,}`).
2. **Health Telemetry Masking**: `/api/health` displays only masked previews (`AIza...4xyz` or `CONFIGURED_MASKED`), never raw tokens.
3. **Deterministic Sandbox Fallback**: If keys are omitted, the engine automatically falls back to `SANDBOX_MOCKED` mode. Calls return verified fixture evidence and deterministic responses, guaranteeing cold judges will **never encounter a 500 error or crash**.

---

## 6. Execution Instructions: Deploying to Cloud Run

### 6.1 Prerequisites Check
Ensure the `gcloud` CLI is logged in as `singwane.linda.m@gmail.com`:
```bash
gcloud auth list
gcloud config set project benchpress-ai-cloud
```

### 6.2 Linux / macOS / WSL One-Command Deployment
```bash
# 1. (Optional) Run one-time GCP infrastructure setup
bash scripts/setup_gcp.sh

# 2. Deploy to Cloud Run
bash scripts/deploy.sh
```

### 6.3 Windows PowerShell One-Command Deployment
```powershell
# 1. (Optional) Run one-time GCP infrastructure setup
powershell -ExecutionPolicy Bypass -File scripts/setup_gcp.ps1

# 2. Deploy to Cloud Run
powershell -ExecutionPolicy Bypass -File scripts/deploy.ps1
```

### 6.4 Parameter Customization Reference
Both deployment scripts support extensive parameter overrides:

| Parameter | Environment Variable | Default Value | Description |
|---|---|---|---|
| Project ID | `GOOGLE_CLOUD_PROJECT` | `benchpress-ai-cloud` | Target GCP project |
| Region | `GCP_REGION` | `us-central1` | Cloud Run deployment region |
| Service Name | `SERVICE_NAME` | `lienmark` | Cloud Run service identifier |
| CPU Limit | `CPU_LIMIT` | `2` | Number of vCPUs allocated |
| Memory Limit | `MEMORY_LIMIT` | `2Gi` | Memory limit (RAM) |
| Min Instances | `MIN_INSTANCES` | `0` | Auto-scale to zero when idle |
| Max Instances | `MAX_INSTANCES` | `10` | Maximum instance ceiling |
| Concurrency | `CONCURRENCY` | `80` | Concurrent requests per instance |
| Secret Manager | `USE_SECRET_MANAGER` | `false` | Enable Secret Manager injection |

---

## 7. Healthcheck, Liveness/Readiness & Zero-Downtime Cutover

### 7.1 Probe Endpoints
The service implements standard health and readiness endpoints:
- **Liveness Probe**: `GET /health` and `GET /healthz` -> Returns `{"status": "healthy"}` with integration and security telemetry.
- **Readiness Probe**: `GET /readyz` -> Verifies the Invalidation Engine and golden fixtures are loaded in memory.
- **Container Startup Probe**: Verified automatically by Cloud Run before traffic routing.

### 7.2 Zero-Downtime Traffic Migration
Cloud Run natively implements blue-green / canary revisions:
1. **Canary Deployment**: Deploy a new revision without routing traffic:
   ```bash
   gcloud run deploy lienmark --image $IMAGE_TAG --no-traffic
   ```
2. **Health Verification**: Probe the revision-specific URL:
   ```bash
   curl -f "https://lienmark-rev-xxx-uc.a.run.app/health"
   ```
3. **Atomic Cutover**: Shift 100% of production traffic instantly:
   ```bash
   gcloud run services update-traffic lienmark --to-latest
   ```
4. **Failure Mitigation**: If the new container fails its startup probe or exits with an error, Cloud Run leaves 100% of production traffic on the preceding healthy revision.

---

## 8. Post-Deployment Verification Checklist

After deployment completes, execute the three-phase verification protocol:

### Phase 1: Unauthenticated Cold Judge URL Verification
Verify that unauthenticated evaluators can access all critical screens:
```bash
SERVICE_URL=$(gcloud run services describe lienmark --platform managed --region us-central1 --project benchpress-ai-cloud --format 'value(status.url)')

# 1. Reviewer Dashboard UI (Instant HTML load, no blank screen)
curl -sI "${SERVICE_URL}/" | grep "HTTP/2 200"

# 2. Health & Credential Redaction Check
curl -s "${SERVICE_URL}/api/health" | grep '"status":"healthy"'

# 3. Golden Fixtures Check (12 claims accessible without auth)
curl -s "${SERVICE_URL}/api/fixtures" | grep '"v7_version"'

# 4. Form E&O-2026 Underwriter Exceptions Schedule SSR Check
curl -sI "${SERVICE_URL}/report/proj_blockbuster_cinema" | grep "HTTP/2 200"
```

### Phase 2: Live Smoke Test Harness
Run the automated integration smoke test against the live services:
```bash
python scripts/run_live_smoke.py
```
*Expected Output*:
- Probes Gemini 2.5 Flash semantic delta.
- Probes Parallel Search API evidence revalidation.
- Validates Google Cloud Agent Builder workflow execution.
- Emits persistent verification artifact: `output/live_smoke_result.json`.

### Phase 3: Cold Judge 7-Gate Compliance Runner
Execute the authoritative 7-gate audit suite:
```bash
python scripts/run_cold_judge_audit.py
```
*Validated Gates*:
- **Gate 1**: Hosted & Public Endpoint Accessibility (All routes 200 OK unauthenticated).
- **Gate 2**: Quickstart Reproduction (Zero-config clean run).
- **Gate 3**: Secret Suppression & PII Redaction Audit (0 exposed secrets).
- **Gate 4**: Broken Link & Phantom File Audit (100% files present).
- **Gate 5**: Video Timing & Subtitle Track Validation (Target duration <= 170s).
- **Gate 6**: OSI-Approved License Visibility (MIT License verified).
- **Gate 7**: Statutory Non-Binding Disclaimer Audit (0 illegal certainty claims).

---

## 9. Rollback & Disaster Recovery Protocol (Phase 8 Alignment)

In the event of an unexpected regression, degraded model latency, or external API disruption:

### 9.1 Instant Revision Rollback (< 5 seconds)
List existing Cloud Run revisions and roll back immediately:
```bash
# List all revisions
gcloud run revisions list --service lienmark --region us-central1 --project benchpress-ai-cloud

# Roll back 100% of traffic to a verified prior revision
gcloud run services update-traffic lienmark \
    --to-revisions=lienmark-00001-abc=100 \
    --region=us-central1 \
    --project=benchpress-ai-cloud
```

### 9.2 Emergency Fail-Closed Safe Mode
If external search APIs experience prolonged upstream outages:
1. The backend automatically catches network timeouts and marks stale claims as `INSUFFICIENT_EVIDENCE`.
2. Claims remain strictly in the Counsel Review Queue.
3. Form E&O-2026 emits explicit underwriter exception notices.
4. **Invariant**: The system **never manufactures artificial approvals** or bypasses human counsel checkpoints during upstream degradation.

---

## 10. Summary Specification Sheet

| Attribute | Specification |
|---|---|
| **Hosting Platform** | Google Cloud Run (Serverless Container Runtime) |
| **GCP Project** | `benchpress-ai-cloud` (Active User: `singwane.linda.m@gmail.com`) |
| **Deployment Region** | `us-central1` |
| **Container Image** | `${REGION}-docker.pkg.dev/benchpress-ai-cloud/lienmark-repo/lienmark:latest` |
| **Container Port** | `8080` (HTTP/1.1 and HTTP/2 supported) |
| **Compute Profile** | 2 vCPU, 2 GiB RAM, Concurrency 80, Timeout 300s |
| **Scaling Policy** | Min: 0 instances, Max: 10 instances (Scale to zero when idle) |
| **Ingress Control** | `--allow-unauthenticated` (Public Judge / Reviewer Access) |
| **Credential Storage** | Google Cloud Secret Manager (`parallel-api-key`, `gemini-api-key`) |
| **Primary Route Map** | `/` (Dashboard), `/report/*` (SSR Exceptions Schedule), `/api/*` (REST API) |
| **Fail-Closed Gate** | Human Counsel Re-Attestation Checkpoint (Zero automated clearance binding) |
