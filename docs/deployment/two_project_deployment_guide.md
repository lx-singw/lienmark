# Lienmark Two-Project Isolated Deployment Architecture: Multi-Project GCP Automation & Promotion Pipeline

> **Authoritative Operational Blueprint & Engineering Specification**  
> **Platform**: Google Cloud Run (Fully Managed Serverless, HTTP/2, Managed TLS, Zero-Downtime Traffic Migration)  
> **Development Environment**: `lienmark-dev-lx-2026` (Display: *Lienmark Development*)  
> **Judge Demo Environment**: `lienmark-demo-lx-2026` (Display: *Lienmark Judge Demo*)  
> **Master Billing Account**: `01575B-23EAEE-CF5627`  
> **Primary Region**: `us-central1`  
> **Budget Allocation**: Dev: $20.00 | Judge Demo: $60.00 | Unallocated Reserve: $20.00 (Total: $100.00)  
> **Policy Engine Version**: `E&O-2026.1-DEVPOST`  
> **Competition Track**: Parallel Track ($15,000 Prize Pool) & Google Cloud Agent Builder  

---

## 1. Architectural Philosophy: Hard Environmental Isolation

Lienmark is an enterprise clearance change control engine built for film, television, and video game underwriters. It reconciles script and visual cut revisions (e.g., baseline V7 cut to revised V8 cut), isolating clearance drift across 12 golden production claims, carrying forward 10 unaffected items at $0 review cost, and dispatching targeted Gemini 2.5 Flash and Parallel Search revalidation tasks to precisely the 2 drifted items.

To ensure strict production-readiness, zero state corruption, and an uncompromised evaluation experience for hackathon judges, Lienmark establishes a **Two-Project Isolated Architecture**:

```
 ┌────────────────────────────────────────────────────────┐       ┌────────────────────────────────────────────────────────┐
 │           DEVELOPMENT PROJECT ENVIRONMENT              │       │              JUDGE DEMO ENVIRONMENT                    │
 │               (lienmark-dev-lx-2026)                   │       │              (lienmark-demo-lx-2026)                   │
 │                                                        │       │                                                        │
 │  ┌─────────────────┐       ┌────────────────────────┐  │       │  ┌────────────────────────┐      ┌──────────────────┐  │
 │  │ Cloud Build CLI │  -->  │ Artifact Registry:     │  │       │  │ Artifact Registry:     │ ---> │ Cloud Run:       │  │
 │  │ (Dockerfile)    │       │ lienmark-repo (Dev)    │  │       │  │ lienmark-repo (Demo)   │      │ lienmark-api     │  │
 │  └─────────────────┘       │ - lienmark-api:SHA     │  │       │  │ - lienmark-api:SHA     │      │ lienmark-web     │  │
 │                            │ - lienmark-web:SHA     │  │       │  │ - lienmark-web:SHA     │      └────────┬─────────┘  │
 │                            └───────────┬────────────┘  │       │  └───────────▲────────────┘               │            │
 └────────────────────────────────────────┼───────────────┘       └──────────────┼────────────────────────────┼────────────┘
                                          │                                      │                            │
                                          │      IMMUTABLE REGISTRY COPY         │                            ▼
                                          └──────────────────────────────────────┘                  PROBE GATE (/health)
                                                (Exact SHA-256 Bitwise Match)                                 │
                                                                                                              ▼
                                                                                                    ATOMIC TRAFFIC SHIFT
                                                                                                    (--to-revisions=100)
```

### Core Invariants of Environmental Isolation
1. **Zero Data Bleed**: Development Firestore databases and Artifact Registry repositories are strictly isolated from Judge Demo. Development state, experimental runs, and scratch testing can never mutate or pollute judge-facing state.
2. **Immutable Artifact Promotion**: No container image is ever re-built in Judge Demo. All images are built once in Development, verified via SHA-256 content-addressable digests, recorded in `output/release_manifest.json`, and transferred bitwise to Judge Demo.
3. **Fail-Safe Canary Verification**: Every promotion deploys with `--no-traffic --tag=candidate`. An automated probing harness validates `/health`, `/readyz`, and root UI endpoints before a single live request is routed.
4. **Sub-5-Second Reversible Cutover**: Revisions are routed atomically via Cloud Run revision traffic splitting. Rolling back to a prior proven revision requires zero image rebuilds and executes in under 5 seconds.

---

## 2. Project Topology & Resource Specifications

| Attribute | Development (`dev`) | Judge Demo (`demo`) | Reserve / Shared |
|---|---|---|---|
| **Project ID** | `lienmark-dev-lx-2026` | `lienmark-demo-lx-2026` | N/A |
| **Display Name** | *Lienmark Development* | *Lienmark Judge Demo* | N/A |
| **Master Billing Account** | `01575B-23EAEE-CF5627` | `01575B-23EAEE-CF5627` | `01575B-23EAEE-CF5627` |
| **Budget Limit** | **$20.00 USD** | **$60.00 USD** | **$20.00 USD** (Unallocated) |
| **Budget Thresholds** | 25%, 50%, 75%, 90%, 100% | 50%, 75%, 90%, 100% | N/A |
| **Primary Region** | `us-central1` (Iowa) | `us-central1` (Iowa) | `us-central1` |
| **Artifact Registry** | `lienmark-repo` (Docker) | `lienmark-repo` (Docker) | N/A |
| **Firestore Database** | `(default)` in Native Mode | `(default)` in Native Mode | N/A |
| **Backend Service** | `lienmark-api` (2 vCPU, 2GiB) | `lienmark-api` (2 vCPU, 2GiB) | N/A |
| **Frontend Service** | `lienmark-web` (1 vCPU, 1GiB) | `lienmark-web` (1 vCPU, 1GiB) | N/A |
| **Min Instances** | 0 (Scale to zero) | 0 (Scale to zero) | N/A |
| **Max Instances** | 10 | 10 | N/A |
| **Dedicated Service Account** | `lienmark-dev-sa@...` | `lienmark-demo-sa@...` | N/A |

---

## 3. Identity and Access Management (IAM) Matrix

Both environments enforce least-privilege role bindings. Human credentials are never used in service execution.

| Role | Target Identity | Operational Purpose |
|---|---|---|
| `roles/run.admin` | Dedicated Service Account | Manages Cloud Run service deployments, traffic splitting, and revision lifecycle. |
| `roles/storage.admin` | Dedicated Service Account | Accesses Cloud Storage buckets for build artifacts, Golden Fixtures, and reports. |
| `roles/cloudbuild.builds.editor` | Dedicated Service Account | Submits and executes Cloud Build jobs for container packaging and image transfers. |
| `roles/secretmanager.secretAccessor` | Dedicated Service Account | Retrieves runtime API keys (`gemini-api-key`, `parallel-api-key`) from Secret Manager. |
| `roles/aiplatform.user` | Dedicated Service Account | Invokes Google Cloud Vertex AI Gemini 2.5 Flash foundation models. |
| `roles/datastore.user` | Dedicated Service Account | Reads and writes clearance state and supersession records in Cloud Firestore Native mode. |

---

## 4. Multi-Project Infrastructure Provisioning

The repository provides fully automated, idempotent provisioning scripts for both Windows PowerShell and POSIX Bash:
- `scripts/provision_environments.ps1`
- `scripts/provision_environments.sh`

### What Provisioning Executes
For each project (`lienmark-dev-lx-2026` and `lienmark-demo-lx-2026`):
1. **Checks / Creates Project**: Runs `gcloud projects describe` and creates the project if absent.
2. **Links Master Billing Account**: Links account `01575B-23EAEE-CF5627` to guarantee continuous API quotas.
3. **Enables 7 Required APIs**:
   - `run.googleapis.com` (Cloud Run)
   - `cloudbuild.googleapis.com` (Cloud Build)
   - `secretmanager.googleapis.com` (Secret Manager)
   - `artifactregistry.googleapis.com` (Artifact Registry)
   - `firestore.googleapis.com` (Cloud Firestore)
   - `aiplatform.googleapis.com` (Vertex AI / Gemini 2.5 Flash)
   - `compute.googleapis.com` (GCE networking backend)
4. **Provisions Firestore Native Mode**: Creates the `(default)` database in `us-central1`.
5. **Provisions Artifact Registry**: Creates the Docker repository `lienmark-repo` in `us-central1`.
6. **Configures Service Accounts**: Creates `lienmark-*-sa` and attaches least-privilege IAM bindings.
7. **Establishes Budget Alerts**:
   - Dev: $20 budget alerting at 25%, 50%, 75%, 90%, 100%.
   - Demo: $60 budget alerting at 50%, 75%, 90%, 100%.

### Provisioning Execution Commands

#### Windows PowerShell:
```powershell
# Dry run simulation (no cloud mutation):
powershell -ExecutionPolicy Bypass -File scripts/provision_environments.ps1 -DryRun

# Full idempotent execution across both environments:
powershell -ExecutionPolicy Bypass -File scripts/provision_environments.ps1

# Target development environment only:
powershell -ExecutionPolicy Bypass -File scripts/provision_environments.ps1 -TargetEnvironment dev
```

#### POSIX Bash:
```bash
# Dry run simulation:
bash scripts/provision_environments.sh --dry-run

# Full idempotent execution across both environments:
bash scripts/provision_environments.sh

# Target judge demo environment only:
bash scripts/provision_environments.sh --environment demo
```

---

## 5. Build & Deployment Pipeline (`deploy.ps1` / `deploy.sh`)

The deployment script operates directly against the target environment (defaulting to `dev` / `lienmark-dev-lx-2026`):
1. **Inspects Git Metadata**: Extracts the current commit hash (e.g., `46b3e668...`) and short SHA (`46b3e66`).
2. **Builds Backend (`lienmark-api`)**: Submits `Dockerfile` via Cloud Build directly to Artifact Registry.
3. **Extracts SHA-256 API Digest**: Queries Artifact Registry for the exact immutable content hash (`sha256:...`).
4. **Builds Frontend (`lienmark-web`)**: Submits `frontend/Dockerfile` via Cloud Build with Next.js 15 standalone output.
5. **Extracts SHA-256 Web Digest**: Resolves the exact immutable content hash for the web container.
6. **Deploys Cloud Run Services**: Deploys both services pinned directly to their immutable SHA-256 references.
7. **Emits Release Manifest**: Serializes the cryptographic proof to `output/release_manifest.json`.

### Release Manifest Schema (`output/release_manifest.json`)
```json
{
  "schema_version": "1.0.0",
  "timestamp": "2026-09-06T07:36:07Z",
  "environment": "dev",
  "project_id": "lienmark-dev-lx-2026",
  "region": "us-central1",
  "repository": "lienmark-repo",
  "git_commit": "46b3e6684eaa91b10afb2e53ec39f855e697377c",
  "git_commit_short": "46b3e66",
  "images": {
    "lienmark-api": {
      "service": "lienmark-api",
      "tag": "us-central1-docker.pkg.dev/lienmark-dev-lx-2026/lienmark-repo/lienmark-api:46b3e66",
      "digest": "us-central1-docker.pkg.dev/lienmark-dev-lx-2026/lienmark-repo/lienmark-api@sha256:...",
      "sha256": "sha256:...",
      "url": "https://lienmark-api-dryrun.a.run.app"
    },
    "lienmark-web": {
      "service": "lienmark-web",
      "tag": "us-central1-docker.pkg.dev/lienmark-dev-lx-2026/lienmark-repo/lienmark-web:46b3e66",
      "digest": "us-central1-docker.pkg.dev/lienmark-dev-lx-2026/lienmark-repo/lienmark-web@sha256:...",
      "sha256": "sha256:...",
      "url": "https://lienmark-web-dryrun.a.run.app"
    }
  }
}
```

---

## 6. Promotion Pipeline to Judge Demo (`promote_to_demo.ps1` / `promote_to_demo.sh`)

Promotion promotes verified code from Development to Judge Demo without re-building:

```
[output/release_manifest.json]
             │
             ▼
  1. Parse & Ingest Immutable Digests (API + Web)
             │
             ▼
  2. Registry Copy: lienmark-dev-lx-2026 -> lienmark-demo-lx-2026
             │
             ▼
  3. Strict SHA-256 Digest Equality Verification
             │   (Source SHA == Destination SHA)
             ▼
  4. Deploy Candidate Revisions (--no-traffic --tag=candidate)
             │
             ▼
  5. Pre-Cutover Probing: /health & /readyz & root UI (200 OK)
             │
             ├── If Failed: ABORT traffic shift. Alert engineer.
             │
             ▼
  6. Atomic Live Cutover: gcloud run services update-traffic --to-revisions=100
             │
             ▼
  7. Audit Telemetry: output/demo_promotion_log.json
```

### Promotion Execution Commands

#### Windows PowerShell:
```powershell
# Dry run verification:
powershell -ExecutionPolicy Bypass -File scripts/promote_to_demo.ps1 -DryRun

# Full automated promotion to Judge Demo:
powershell -ExecutionPolicy Bypass -File scripts/promote_to_demo.ps1
```

#### POSIX Bash:
```bash
# Dry run verification:
bash scripts/promote_to_demo.sh --dry-run

# Full automated promotion to Judge Demo:
bash scripts/promote_to_demo.sh
```

---

## 7. Disaster Recovery & Instant Rollback Protocol (< 5 Seconds)

In the event of upstream API degradation, unexpected model latency, or runtime regression:

### 1. Instant Traffic Rollback
Cloud Run revisions are immutable and preserved. You can immediately route 100% of live production traffic back to a prior verified revision:

```bash
# 1. List active revisions in Judge Demo:
gcloud run revisions list \
  --service=lienmark-api \
  --region=us-central1 \
  --project=lienmark-demo-lx-2026

# 2. Shift 100% traffic back to known healthy revision:
gcloud run services update-traffic lienmark-api \
  --to-revisions=lienmark-api-00002-prev=100 \
  --region=us-central1 \
  --project=lienmark-demo-lx-2026

gcloud run services update-traffic lienmark-web \
  --to-revisions=lienmark-web-00002-prev=100 \
  --region=us-central1 \
  --project=lienmark-demo-lx-2026
```

### 2. Fail-Closed Safe Mode Guarantee
If external search APIs (Parallel Search or Vertex AI) encounter unexpected service disruptions:
- Lienmark automatically flags affected claims as `INSUFFICIENT_EVIDENCE`.
- Invariant: **No automated clearance approval is ever granted on insufficient evidence.**
- Claims remain safely queued for human clearance counsel evaluation.

---

## 8. Verification Commands for Judges & Underwriters

Judges can verify endpoint health, statutory disclaimers, and ledger integrity unauthenticated:

```bash
# 1. Query live Judge Demo health probe:
curl -fsS "https://lienmark-api-demo.a.run.app/health"

# 2. Query engine readiness probe:
curl -fsS "https://lienmark-api-demo.a.run.app/readyz"

# 3. Inspect Form E&O-2026 SSR Underwriter Schedule:
curl -fsS "https://lienmark-api-demo.a.run.app/report/proj_blockbuster_cinema" | grep "FORM E&O-2026"

# 4. Run automated test suite:
python -m pytest tests/test_promotion_pipeline.py -v
```
