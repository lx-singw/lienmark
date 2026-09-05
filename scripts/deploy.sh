#!/usr/bin/env bash
# Production Deployment Script for Lienmark on Google Cloud Run
# Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon
set -euo pipefail

# ── 1. Configuration & Defaults ───────────────────────────────────────────────
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-lienmark-production}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="lienmark"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-lienmark-sa@${PROJECT_ID}.iam.gserviceaccount.com}"

CPU="${CPU_LIMIT:-2}"
MEMORY="${MEMORY_LIMIT:-2Gi}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-10}"
CONCURRENCY="${CONCURRENCY:-80}"
TIMEOUT="${TIMEOUT:-300}"

echo "======================================================================"
echo ">> 🚀 DEPLOYING LIENMARK TO GOOGLE CLOUD RUN"
echo "   Service:         ${SERVICE_NAME}"
echo "   Project:         ${PROJECT_ID}"
echo "   Region:          ${REGION}"
echo "   Image:           ${IMAGE_TAG}"
echo "   Service Account: ${SERVICE_ACCOUNT}"
echo "   Resources:       ${CPU} CPU, ${MEMORY} RAM"
echo "======================================================================"

# ── 2. Environment Configuration ─────────────────────────────────────────────
# Automatically read .env if present in root or scripts directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -f "${ROOT_DIR}/.env" ]; then
  echo "--> Sourcing local configuration from ${ROOT_DIR}/.env..."
  set -a
  # shellcheck disable=SC1091
  . "${ROOT_DIR}/.env"
  set +a
fi

# Build Cloud Run environment variable parameters
ENV_VARS="ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_REGION=${REGION}"

if [ -n "${PARALLEL_API_KEY:-}" ]; then
  ENV_VARS="${ENV_VARS},PARALLEL_API_KEY=${PARALLEL_API_KEY}"
  echo "  [OK] Attached PARALLEL_API_KEY environment variable"
else
  echo "  [INFO] PARALLEL_API_KEY not provided (will operate in deterministic mock mode)"
fi

if [ -n "${GEMINI_API_KEY:-}" ]; then
  ENV_VARS="${ENV_VARS},GEMINI_API_KEY=${GEMINI_API_KEY}"
  echo "  [OK] Attached GEMINI_API_KEY environment variable"
else
  echo "  [INFO] GEMINI_API_KEY not provided (will operate in deterministic mock mode)"
fi

# Optional: Support Google Cloud Secret Manager if USE_SECRET_MANAGER=true
SECRETS_ARG=""
if [ "${USE_SECRET_MANAGER:-false}" = "true" ]; then
  echo "--> Using Google Cloud Secret Manager for credentials..."
  SECRETS_ARG="--set-secrets=PARALLEL_API_KEY=parallel-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest"
fi

# ── 3. Build Container Image using Cloud Build ────────────────────────────────
echo "--> Step 1: Building container image via Google Cloud Build..."
cd "${ROOT_DIR}"
gcloud builds submit \
  --tag "${IMAGE_TAG}" \
  --project="${PROJECT_ID}" \
  .

# ── 4. Deploy to Google Cloud Run ─────────────────────────────────────────────
echo "--> Step 2: Deploying '${SERVICE_NAME}' to Cloud Run..."
# shellcheck disable=SC2086
gcloud run deploy lienmark \
  --image "${IMAGE_TAG}" \
  --platform managed \
  --region "${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account "${SERVICE_ACCOUNT}" \
  --cpu "${CPU}" \
  --memory "${MEMORY}" \
  --min-instances "${MIN_INSTANCES}" \
  --max-instances "${MAX_INSTANCES}" \
  --concurrency "${CONCURRENCY}" \
  --timeout "${TIMEOUT}" \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "${ENV_VARS}" \
  ${SECRETS_ARG}

# ── 5. Verification and Status ────────────────────────────────────────────────
echo "=== ✅ DEPLOYMENT COMPLETE ==="
SERVICE_URL=$(gcloud run services describe lienmark \
  --platform managed \
  --region "${REGION}" \
  --project="${PROJECT_ID}" \
  --format 'value(status.url)')

echo "Service URL:       ${SERVICE_URL}"
echo "Health Endpoint:   ${SERVICE_URL}/health"
echo "API Documentation: ${SERVICE_URL}/docs"
echo "Review Dashboard:  ${SERVICE_URL}/"

