#!/usr/bin/env bash
# Two-Project Isolated Production Deployment Script for Lienmark
# Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon
set -euo pipefail

# ── 1. Configuration & Defaults ───────────────────────────────────────────────
ENVIRONMENT="dev"
PROJECT_ID=""
REGION="${GCP_REGION:-us-central1}"
REPO_NAME="${REPO_NAME:-lienmark-repo}"
SERVICE_ACCOUNT=""
CPU_LIMIT="${CPU_LIMIT:-2}"
MEMORY_LIMIT="${MEMORY_LIMIT:-2Gi}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-10}"
CONCURRENCY="${CONCURRENCY:-80}"
TIMEOUT="${TIMEOUT:-300}"
DRY_RUN=false
USE_SECRET_MANAGER="${USE_SECRET_MANAGER:-false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/output"
mkdir -p "${OUTPUT_DIR}"

# ── Parse Arguments ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment|-e)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --project-id|-p)
      PROJECT_ID="$2"
      shift 2
      ;;
    --region|-r)
      REGION="$2"
      shift 2
      ;;
    --repo-name)
      REPO_NAME="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --use-secret-manager)
      USE_SECRET_MANAGER=true
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

# Resolve default Project ID
if [ -z "${PROJECT_ID}" ]; then
  if [ -n "${GOOGLE_CLOUD_PROJECT:-}" ]; then
    PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"
  elif [ "${ENVIRONMENT}" = "dev" ]; then
    PROJECT_ID="lienmark-dev-lx-2026"
  else
    PROJECT_ID="lienmark-demo-lx-2026"
  fi
fi

# Resolve default Service Account
if [ -z "${SERVICE_ACCOUNT}" ]; then
  if [ "${ENVIRONMENT}" = "dev" ]; then
    SERVICE_ACCOUNT="lienmark-dev-sa@${PROJECT_ID}.iam.gserviceaccount.com"
  else
    SERVICE_ACCOUNT="lienmark-demo-sa@${PROJECT_ID}.iam.gserviceaccount.com"
  fi
fi

# Determine Git commit SHA
GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "46b3e6684eaa91b10afb2e53ec39f855e697377c")
GIT_COMMIT_SHORT="${GIT_COMMIT:0:7}"

API_IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/lienmark-api:${GIT_COMMIT_SHORT}"
WEB_IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/lienmark-web:${GIT_COMMIT_SHORT}"

echo "======================================================================"
echo ">> 🚀 LIENMARK ISOLATED DEPLOYMENT PIPELINE (Bash)"
echo "   Environment:     ${ENVIRONMENT}"
echo "   Project ID:      ${PROJECT_ID}"
echo "   Region:          ${REGION}"
echo "   Repository:      ${REPO_NAME}"
echo "   Service Account: ${SERVICE_ACCOUNT}"
echo "   Git Commit:      ${GIT_COMMIT_SHORT} (${GIT_COMMIT})"
echo "   Dry Run Mode:    ${DRY_RUN}"
echo "======================================================================"

# Source .env if present
if [ -f "${ROOT_DIR}/.env" ]; then
  echo "--> Sourcing local configuration from ${ROOT_DIR}/.env..."
  set -a
  # shellcheck disable=SC1091
  . "${ROOT_DIR}/.env"
  set +a
fi

# Dry run simulation
if [ "${DRY_RUN}" = true ]; then
  echo ""
  echo "[DRY-RUN] Simulating Cloud Build and Cloud Run deployment for '${ENVIRONMENT}'..."
  SYNTHETIC_API_DIGEST="sha256:$(python -c 'import hashlib, sys; print(hashlib.sha256(("lienmark-api-" + sys.argv[1]).encode()).hexdigest())' "${GIT_COMMIT}")"
  SYNTHETIC_WEB_DIGEST="sha256:$(python -c 'import hashlib, sys; print(hashlib.sha256(("lienmark-web-" + sys.argv[1]).encode()).hexdigest())' "${GIT_COMMIT}")"
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  cat > "${OUTPUT_DIR}/release_manifest.json" <<EOF
{
  "schema_version": "1.0.0",
  "timestamp": "${TIMESTAMP}",
  "environment": "${ENVIRONMENT}",
  "project_id": "${PROJECT_ID}",
  "region": "${REGION}",
  "repository": "${REPO_NAME}",
  "git_commit": "${GIT_COMMIT}",
  "git_commit_short": "${GIT_COMMIT_SHORT}",
  "images": {
    "lienmark-api": {
      "service": "lienmark-api",
      "tag": "${API_IMAGE_TAG}",
      "digest": "${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/lienmark-api@${SYNTHETIC_API_DIGEST}",
      "sha256": "${SYNTHETIC_API_DIGEST}",
      "url": "https://lienmark-api-dryrun.a.run.app"
    },
    "lienmark-web": {
      "service": "lienmark-web",
      "tag": "${WEB_IMAGE_TAG}",
      "digest": "${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/lienmark-web@${SYNTHETIC_WEB_DIGEST}",
      "sha256": "${SYNTHETIC_WEB_DIGEST}",
      "url": "https://lienmark-web-dryrun.a.run.app"
    }
  }
}
EOF
  echo "  [DRY-RUN] Release manifest written to: ${OUTPUT_DIR}/release_manifest.json"
  echo ""
  echo "=== ✅ DRY-RUN DEPLOYMENT SIMULATION COMPLETE ==="
  exit 0
fi

# ── 1. Cloud Build: lienmark-api ──────────────────────────────────────────────
echo "--> [1/4] Building 'lienmark-api' container image via Cloud Build..."
cd "${ROOT_DIR}"
gcloud builds submit \
  --tag "${API_IMAGE_TAG}" \
  --project="${PROJECT_ID}" \
  .

echo "    Resolving immutable SHA-256 digest for 'lienmark-api'..."
API_SHA256=$(gcloud artifacts docker images describe "${API_IMAGE_TAG}" \
  --project="${PROJECT_ID}" \
  --format="value(image_summary.digest)")
API_DIGEST_REF="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/lienmark-api@${API_SHA256}"
echo "    [OK] Immutable Digest: ${API_SHA256}"

# ── 2. Cloud Build: lienmark-web ──────────────────────────────────────────────
echo "--> [2/4] Building 'lienmark-web' container image via Cloud Build..."
cd "${ROOT_DIR}/frontend"
gcloud builds submit \
  --tag "${WEB_IMAGE_TAG}" \
  --project="${PROJECT_ID}" \
  .

echo "    Resolving immutable SHA-256 digest for 'lienmark-web'..."
WEB_SHA256=$(gcloud artifacts docker images describe "${WEB_IMAGE_TAG}" \
  --project="${PROJECT_ID}" \
  --format="value(image_summary.digest)")
WEB_DIGEST_REF="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/lienmark-web@${WEB_SHA256}"
echo "    [OK] Immutable Digest: ${WEB_SHA256}"

# ── 3. Deploy Cloud Run: lienmark-api ─────────────────────────────────────────
echo "--> [3/4] Deploying 'lienmark-api' to Cloud Run..."
API_ENV_VARS="ENVIRONMENT=${ENVIRONMENT},GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_REGION=${REGION},FIRESTORE_PROJECT_ID=${PROJECT_ID},FIRESTORE_DATABASE=(default),GOOGLE_GENAI_USE_VERTEXAI=true"
if [ "${USE_SECRET_MANAGER}" != true ] && [ -n "${PARALLEL_API_KEY:-}" ]; then API_ENV_VARS="${API_ENV_VARS},PARALLEL_API_KEY=${PARALLEL_API_KEY}"; fi
if [ -n "${GEMINI_API_KEY:-}" ]; then API_ENV_VARS="${API_ENV_VARS},GEMINI_API_KEY=${GEMINI_API_KEY}"; fi

SECRETS_ARG=""
if [ "${USE_SECRET_MANAGER}" = true ]; then
  SECRETS_ARG="--set-secrets=PARALLEL_API_KEY=parallel-api-key:latest,SESSION_SECRET_KEY=session-secret-key:latest"
fi

# shellcheck disable=SC2086
gcloud run deploy lienmark-api \
  --image "${API_DIGEST_REF}" \
  --platform managed \
  --region "${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account "${SERVICE_ACCOUNT}" \
  --cpu "${CPU_LIMIT}" \
  --memory "${MEMORY_LIMIT}" \
  --min-instances "${MIN_INSTANCES}" \
  --max-instances "${MAX_INSTANCES}" \
  --concurrency "${CONCURRENCY}" \
  --timeout "${TIMEOUT}" \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "${API_ENV_VARS}" \
  ${SECRETS_ARG}

API_URL=$(gcloud run services describe lienmark-api \
  --platform managed \
  --region "${REGION}" \
  --project="${PROJECT_ID}" \
  --format='value(status.url)')
echo "    [OK] lienmark-api URL: ${API_URL}"

# ── 4. Deploy Cloud Run: lienmark-web ─────────────────────────────────────────
echo "--> [4/4] Deploying 'lienmark-web' to Cloud Run..."
WEB_ENV_VARS="NODE_ENV=production,INTERNAL_API_URL=${API_URL},BACKEND_URL=${API_URL},INTERNAL_BACKEND_URL=${API_URL},NEXT_PUBLIC_API_BASE_URL=${API_URL},NEXT_PUBLIC_BACKEND_URL=${API_URL}"

gcloud run deploy lienmark-web \
  --image "${WEB_DIGEST_REF}" \
  --platform managed \
  --region "${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account "${SERVICE_ACCOUNT}" \
  --cpu 1 \
  --memory 1Gi \
  --min-instances 0 \
  --max-instances 10 \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "${WEB_ENV_VARS}"

WEB_URL=$(gcloud run services describe lienmark-web \
  --platform managed \
  --region "${REGION}" \
  --project="${PROJECT_ID}" \
  --format='value(status.url)')
echo "    [OK] lienmark-web URL: ${WEB_URL}"

# ── Output: Release Manifest ──────────────────────────────────────────────────
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "${OUTPUT_DIR}/release_manifest.json" <<EOF
{
  "schema_version": "1.0.0",
  "timestamp": "${TIMESTAMP}",
  "environment": "${ENVIRONMENT}",
  "project_id": "${PROJECT_ID}",
  "region": "${REGION}",
  "repository": "${REPO_NAME}",
  "git_commit": "${GIT_COMMIT}",
  "git_commit_short": "${GIT_COMMIT_SHORT}",
  "images": {
    "lienmark-api": {
      "service": "lienmark-api",
      "tag": "${API_IMAGE_TAG}",
      "digest": "${API_DIGEST_REF}",
      "sha256": "${API_SHA256}",
      "url": "${API_URL}"
    },
    "lienmark-web": {
      "service": "lienmark-web",
      "tag": "${WEB_IMAGE_TAG}",
      "digest": "${WEB_DIGEST_REF}",
      "sha256": "${WEB_SHA256}",
      "url": "${WEB_URL}"
    }
  }
}
EOF

echo ""
echo "=== ✅ DEPLOYMENT COMPLETE ==="
echo "Release Manifest: ${OUTPUT_DIR}/release_manifest.json"
echo "Backend API URL:  ${API_URL}"
echo "Frontend Web URL: ${WEB_URL}"
