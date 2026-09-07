# Production Cutover & Operations Runbook

> **Service**: `lienmark-clearance-engine`  
> **Version**: `1.0.0-production`  
> **Platform**: Google Cloud Run (Fully Managed, Serverless Container)  
> **SLO Commitments**: Liveness Latency < 20ms, Workflow Drift SLA < 15.0s, Fail-Closed Security  

---

## 1. Cloud Run Production Specification

Production services are deployed with pinned resource limits, concurrency profiles, and fail-safe instance scaling.

```bash
gcloud run deploy lienmark-api \
  --image="gcr.io/${GOOGLE_CLOUD_PROJECT}/lienmark-api:1.0.0" \
  --region="us-central1" \
  --platform="managed" \
  --min-instances=1 \
  --max-instances=10 \
  --concurrency=80 \
  --session-affinity \
  --memory=2Gi \
  --cpu=2 \
  --port=8080 \
  --timeout=30s \
  --set-env-vars="ENVIRONMENT=production,TENANT_STRICT_MODE=true,DEMO_MODE=false,MAX_API_SPEND_USD=500.0"
```

### Key Parameter Rationales
- `--min-instances=1`: Guarantees warm-container availability, preventing cold starts from degrading clearance SLA.
- `--concurrency=80`: Optimized for async I/O coroutines in FastAPI, allowing high-throughput concurrent review sessions.
- `--session-affinity`: Ensures sticky routing for Server-Sent Events (SSE) connections (`/api/events/subscribe`) and multi-step clearance workflows, preventing cross-instance connection churn during traffic shifting.
- `--memory=2Gi`: Reserves ample headroom for screenplay AST token parsing, PDF deliverable rendering, and SHA-256 stamping.

---

## 2. Secret Manager Integration

Production secrets are bound exclusively through Google Secret Manager. Secrets are mounted as environment variables at container initialization.

```bash
gcloud run services update lienmark-api \
  --region="us-central1" \
  --set-secrets="SESSION_SECRET_KEY=lienmark-session-secret:latest,\
GEMINI_API_KEY=lienmark-gemini-key:latest,\
PARALLEL_API_KEY=lienmark-parallel-key:latest,\
AUDIT_SIGNING_KEY=lienmark-audit-key:latest"
```

### Secret Invariants
1. Default secrets (`lienmark-session-secret-salt-2026`) are rejected at startup by `settings.validate_production_readiness()`.
2. All secret variables are redacted in access logs via `CorrelationLoggingMiddleware`.
3. Secret rotation takes effect immediately on the next deployed revision without codebase modifications.

---

## 3. Pre-Cutover Verification & Readiness Probing

Before routing live production traffic, automated harnesses validate process health.

### Liveness Probe (`GET /healthz`)
- Response constraint: `< 20ms` latency, returns `{"status": "alive"}`.
- Kubernetes / Cloud Run health checker uses this endpoint for process restart decisions.

### Deep Readiness Probe (`GET /readyz`)
- Inspects core dependencies:
  - `firestore`: Tenant database connectivity and permission checks.
  - `settings`: Verification of production flags, strict mode, and secret validation.
  - `parallel_search`: Search service credential check.
  - `gemini`: Gemini 2.5 Flash API credentials or Vertex ADC connectivity.
- **Fail-Closed Rule (INV-S73-02)**: Returns `HTTP 503 Service Unavailable` if any dependency is degraded or unready.

```bash
CANDIDATE_URL=$(gcloud run services describe lienmark-api --format='value(status.url)')
curl -fsS -m 5 "${CANDIDATE_URL}/readyz" || {
  echo "FATAL: Candidate failed readiness probe. Aborting cutover." >&2
  exit 1
}
```

---

## 4. Canary Promotion & Atomic Traffic Shift

Canary deployments ensure zero-downtime cutover and automatic rollback capability.

### Step 1: Deploy Candidate Revision with Zero Traffic
```bash
gcloud run deploy lienmark-api \
  --image="gcr.io/${GOOGLE_CLOUD_PROJECT}/lienmark-api:1.0.0" \
  --no-traffic \
  --tag="candidate" \
  --session-affinity
```

### Step 2: Validate Candidate Tag
```bash
curl -fsS -m 10 "https://candidate---lienmark-api-uc.a.run.app/readyz"
python scripts/verify_integrations.py --url="https://candidate---lienmark-api-uc.a.run.app"
```

### Step 3: Shift Traffic Incrementally
```bash
# 10% Canary Shift
gcloud run services update-traffic lienmark-api --to-tags=candidate=10
sleep 60

# 100% Full Cutover
gcloud run services update-traffic lienmark-api --to-tags=candidate=100
```

---

## 5. Instant Rollback Procedures

If elevated error rates or degraded probes occur post-cutover:

### 1-Second Instant Revision Reversion
```bash
PREV_REVISION=$(gcloud run revisions list --service=lienmark-api --format='value(name)' --limit=2 | sed -n '2p')
gcloud run services update-traffic lienmark-api --to-revisions="${PREV_REVISION}=100"
```

### Disaster Recovery & Cold Start State Restoration
In the event of an abrupt process termination during active workflow evaluation:
```bash
curl -fsS -X POST "https://lienmark-api-uc.a.run.app/api/recovery/cold-start?stale_threshold_sec=60.0"
```

---

## 6. SLO Alerts & Cloud Monitoring

| Metric | Target SLO | Alert Condition | Action Required |
| :--- | :--- | :--- | :--- |
| **Liveness Latency** | P99 < 20ms | > 50ms for 3 consecutive minutes | Check CPU throttling or container memory usage. |
| **Workflow Drift Latency** | P95 < 15.0s | > 15.0s over 5-minute window | Investigate Gemini / Parallel API upstream latencies. |
| **System Availability** | 99.9% 2xx/3xx | > 1% 5xx error rate over 5 min | Trigger automatic revision rollback to prior healthy SHA. |
| **Readiness Probes** | 100% 200 OK | Any 503 response on `/readyz` | Cloud Run restarts unhealthy container; check Secret Manager. |

### Incident Escalation Contacts
- Primary On-Call: `devops@lienmark.cloud`
- Security Operations: `security@lienmark.cloud`
- Underwriting Compliance: `legal-tech@lienmark.cloud`
