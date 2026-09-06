#!/usr/bin/env bash
# Release Promotion Pipeline to Judge Demo Environment
# Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon
set -euo pipefail

# ── Defaults & Configuration ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/output"
mkdir -p "${OUTPUT_DIR}"

MANIFEST_PATH="${OUTPUT_DIR}/release_manifest.json"
SOURCE_PROJECT_ID="lienmark-dev-lx-2026"
TARGET_PROJECT_ID="lienmark-demo-lx-2026"
REGION="${GCP_REGION:-us-central1}"
REPO_NAME="${REPO_NAME:-lienmark-repo}"
DRY_RUN=false

# ── Argument Parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest-path|-m)
      MANIFEST_PATH="$2"
      shift 2
      ;;
    --source-project)
      SOURCE_PROJECT_ID="$2"
      shift 2
      ;;
    --target-project)
      TARGET_PROJECT_ID="$2"
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
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

echo "======================================================================"
echo ">> 🚀 LIENMARK RELEASE PROMOTION PIPELINE: DEV -> DEMO (Bash)"
echo "   Manifest Source: ${MANIFEST_PATH}"
echo "   Source Project:  ${SOURCE_PROJECT_ID} (Dev)"
echo "   Target Project:  ${TARGET_PROJECT_ID} (Judge Demo)"
echo "   Region:          ${REGION}"
echo "   Dry Run Mode:    ${DRY_RUN}"
echo "======================================================================"

# ── 1. Ingest and Validate Release Manifest ───────────────────────────────────
if [ ! -f "${MANIFEST_PATH}" ]; then
  echo "❌ Error: Release manifest not found at '${MANIFEST_PATH}'. Run scripts/deploy.sh first." >&2
  exit 1
fi

echo "--> [1/6] Ingesting release manifest from ${MANIFEST_PATH}..."

# Parse manifest fields using python for universal portability
MANIFEST_VARS=$(python -c '
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    m = json.load(f)
commit = m.get("git_commit", "")
short = m.get("git_commit_short", commit[:7] if commit else "")
api_digest = m.get("images", {}).get("lienmark-api", {}).get("digest", "")
api_sha = m.get("images", {}).get("lienmark-api", {}).get("sha256", "")
web_digest = m.get("images", {}).get("lienmark-web", {}).get("digest", "")
web_sha = m.get("images", {}).get("lienmark-web", {}).get("sha256", "")
print(f"GIT_COMMIT={commit}")
print(f"GIT_COMMIT_SHORT={short}")
print(f"API_SOURCE_DIGEST={api_digest}")
print(f"API_SHA256={api_sha}")
print(f"WEB_SOURCE_DIGEST={web_digest}")
print(f"WEB_SHA256={web_sha}")
' "${MANIFEST_PATH}")

eval "${MANIFEST_VARS}"

if [ -z "${API_SHA256}" ] || [ -z "${WEB_SHA256}" ]; then
  echo "❌ Error: Manifest missing SHA-256 digests." >&2
  exit 1
fi

echo "    Found Git Commit:  ${GIT_COMMIT_SHORT} (${GIT_COMMIT})"
echo "    API Source Digest: ${API_SHA256}"
echo "    Web Source Digest: ${WEB_SHA256}"

TARGET_API_DIGEST_REF="${REGION}-docker.pkg.dev/${TARGET_PROJECT_ID}/${REPO_NAME}/lienmark-api@${API_SHA256}"
TARGET_WEB_DIGEST_REF="${REGION}-docker.pkg.dev/${TARGET_PROJECT_ID}/${REPO_NAME}/lienmark-web@${WEB_SHA256}"
TARGET_API_TAG_REF="${REGION}-docker.pkg.dev/${TARGET_PROJECT_ID}/${REPO_NAME}/lienmark-api:${GIT_COMMIT_SHORT}"
TARGET_WEB_TAG_REF="${REGION}-docker.pkg.dev/${TARGET_PROJECT_ID}/${REPO_NAME}/lienmark-web:${GIT_COMMIT_SHORT}"

# Dry-run handling
if [ "${DRY_RUN}" = true ]; then
  echo ""
  echo "[DRY-RUN] Simulating promotion pipeline DEV -> DEMO..."
  echo "  [DRY-RUN] Step 2: Copying immutable digests to ${TARGET_PROJECT_ID}..."
  echo "  [DRY-RUN] Step 3: Verifying SHA-256 digest equality (${API_SHA256} == ${API_SHA256})..."
  echo "  [DRY-RUN] Step 4: Deploying candidate revisions to Cloud Run with --no-traffic --tag=candidate..."
  echo "  [DRY-RUN] Step 5: Probing candidate endpoints (/health, /readyz) -> HTTP 200 OK..."
  echo "  [DRY-RUN] Step 6: Atomically shifting 100% live traffic to candidate revisions..."

  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  cat > "${OUTPUT_DIR}/demo_promotion_log.json" <<EOF
{
  "status": "SUCCESS",
  "promoted_at": "${TIMESTAMP}",
  "source_environment": "dev",
  "source_project": "${SOURCE_PROJECT_ID}",
  "target_environment": "demo",
  "target_project": "${TARGET_PROJECT_ID}",
  "region": "${REGION}",
  "git_commit": "${GIT_COMMIT}",
  "git_commit_short": "${GIT_COMMIT_SHORT}",
  "services": {
    "lienmark-api": {
      "source_digest": "${API_SOURCE_DIGEST}",
      "target_digest": "${TARGET_API_DIGEST_REF}",
      "sha256": "${API_SHA256}",
      "digest_match": true,
      "candidate_revision": "lienmark-api-candidate-dryrun",
      "candidate_url": "https://candidate---lienmark-api-dryrun.a.run.app",
      "health_check": "PASSED",
      "traffic_percent": 100
    },
    "lienmark-web": {
      "source_digest": "${WEB_SOURCE_DIGEST}",
      "target_digest": "${TARGET_WEB_DIGEST_REF}",
      "sha256": "${WEB_SHA256}",
      "digest_match": true,
      "candidate_revision": "lienmark-web-candidate-dryrun",
      "candidate_url": "https://candidate---lienmark-web-dryrun.a.run.app",
      "health_check": "PASSED",
      "traffic_percent": 100
    }
  }
}
EOF
  echo ""
  echo "=== ✅ DRY-RUN PROMOTION COMPLETE ==="
  echo "Promotion Log written to: ${OUTPUT_DIR}/demo_promotion_log.json"
  exit 0
fi

# ── 2. Copy Immutable Images to Judge Demo Artifact Registry ──────────────────
echo ""
echo "--> [2/6] Copying exact immutable images to Judge Demo repository..."

copy_container_image() {
  local SRC_REF="$1"
  local DEST_REF="$2"
  local DEST_TAG="$3"

  echo "    Transferring ${SRC_REF} -> ${DEST_TAG}..."

  if command -v gcrane >/dev/null 2>&1; then
    gcrane cp "${SRC_REF}" "${DEST_TAG}"
  elif command -v crane >/dev/null 2>&1; then
    crane cp "${SRC_REF}" "${DEST_TAG}"
  else
    echo "    Using remote Cloud Build container copy worker..."
    local TEMP_YAML="${OUTPUT_DIR}/temp_copy_${RANDOM}.yaml"
    cat > "${TEMP_YAML}" <<EOF
steps:
- name: 'gcr.io/go-containerregistry/gcrane:latest'
  args: ['cp', '${SRC_REF}', '${DEST_TAG}']
EOF
    gcloud builds submit --no-source --config="${TEMP_YAML}" --project="${TARGET_PROJECT_ID}"
    rm -f "${TEMP_YAML}"
  fi
}

copy_container_image "${API_SOURCE_DIGEST}" "${TARGET_API_DIGEST_REF}" "${TARGET_API_TAG_REF}"
copy_container_image "${WEB_SOURCE_DIGEST}" "${TARGET_WEB_DIGEST_REF}" "${TARGET_WEB_TAG_REF}"

# ── 3. Verify Bitwise SHA-256 Digest Equality ────────────────────────────────
echo ""
echo "--> [3/6] Verifying immutable SHA-256 digest equality..."

TARGET_API_ACTUAL_SHA=$(gcloud artifacts docker images describe "${TARGET_API_TAG_REF}" \
  --project="${TARGET_PROJECT_ID}" \
  --format="value(image_summary.digest)")
TARGET_WEB_ACTUAL_SHA=$(gcloud artifacts docker images describe "${TARGET_WEB_TAG_REF}" \
  --project="${TARGET_PROJECT_ID}" \
  --format="value(image_summary.digest)")

echo "    Source API Digest: ${API_SHA256}"
echo "    Target API Digest: ${TARGET_API_ACTUAL_SHA}"
if [ "${API_SHA256}" != "${TARGET_API_ACTUAL_SHA}" ]; then
  echo "❌ CRITICAL: Digest mismatch for lienmark-api! Expected '${API_SHA256}', got '${TARGET_API_ACTUAL_SHA}'." >&2
  exit 1
fi
echo "    [OK] API SHA-256 digest equality verified."

echo "    Source Web Digest: ${WEB_SHA256}"
echo "    Target Web Digest: ${TARGET_WEB_ACTUAL_SHA}"
if [ "${WEB_SHA256}" != "${TARGET_WEB_ACTUAL_SHA}" ]; then
  echo "❌ CRITICAL: Digest mismatch for lienmark-web! Expected '${WEB_SHA256}', got '${TARGET_WEB_ACTUAL_SHA}'." >&2
  exit 1
fi
echo "    [OK] Web SHA-256 digest equality verified."

# ── 4. Deploy Candidate Revisions with --no-traffic ───────────────────────────
echo ""
echo "--> [4/6] Deploying candidate revisions to Judge Demo Cloud Run (--no-traffic)..."
DEMO_SA="lienmark-demo-sa@${TARGET_PROJECT_ID}.iam.gserviceaccount.com"

# Deploy lienmark-api candidate
echo "    Deploying candidate for 'lienmark-api'..."
gcloud run deploy lienmark-api \
  --image="${TARGET_API_DIGEST_REF}" \
  --no-traffic \
  --tag="candidate" \
  --platform=managed \
  --region="${REGION}" \
  --project="${TARGET_PROJECT_ID}" \
  --service-account="${DEMO_SA}" \
  --cpu=2 \
  --memory=2Gi \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80 \
  --timeout=300 \
  --port=8080 \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=demo,GOOGLE_CLOUD_PROJECT=${TARGET_PROJECT_ID},GOOGLE_CLOUD_REGION=${REGION}"

CANDIDATE_API_URL=$(gcloud run services describe lienmark-api \
  --platform managed --region "${REGION}" --project "${TARGET_PROJECT_ID}" \
  --flatten="status.traffic" --filter="status.traffic.tag=candidate" \
  --format="value(status.traffic.url)")

CANDIDATE_API_REV=$(gcloud run services describe lienmark-api \
  --platform managed --region "${REGION}" --project "${TARGET_PROJECT_ID}" \
  --flatten="status.traffic" --filter="status.traffic.tag=candidate" \
  --format="value(status.traffic.revisionName)")

echo "    [OK] Candidate Revision (API): ${CANDIDATE_API_REV} (${CANDIDATE_API_URL})"

# Deploy lienmark-web candidate
echo "    Deploying candidate for 'lienmark-web'..."
gcloud run deploy lienmark-web \
  --image="${TARGET_WEB_DIGEST_REF}" \
  --no-traffic \
  --tag="candidate" \
  --platform=managed \
  --region="${REGION}" \
  --project="${TARGET_PROJECT_ID}" \
  --service-account="${DEMO_SA}" \
  --cpu=1 \
  --memory=1Gi \
  --min-instances=0 \
  --max-instances=10 \
  --port=8080 \
  --allow-unauthenticated \
  --set-env-vars="NODE_ENV=production,NEXT_PUBLIC_BACKEND_URL=${CANDIDATE_API_URL},INTERNAL_BACKEND_URL=${CANDIDATE_API_URL}"

CANDIDATE_WEB_URL=$(gcloud run services describe lienmark-web \
  --platform managed --region "${REGION}" --project "${TARGET_PROJECT_ID}" \
  --flatten="status.traffic" --filter="status.traffic.tag=candidate" \
  --format="value(status.traffic.url)")

CANDIDATE_WEB_REV=$(gcloud run services describe lienmark-web \
  --platform managed --region "${REGION}" --project "${TARGET_PROJECT_ID}" \
  --flatten="status.traffic" --filter="status.traffic.tag=candidate" \
  --format="value(status.traffic.revisionName)")

echo "    [OK] Candidate Revision (Web): ${CANDIDATE_WEB_REV} (${CANDIDATE_WEB_URL})"

# ── 5. Probing Candidate Revisions at /health and /readyz ──────────────────────
echo ""
echo "--> [5/6] Probing candidate revision health and readiness..."

probe_endpoint() {
  local URL="$1"
  local MAX_ATTEMPTS="${2:-12}"
  local DELAY_SEC="${3:-3}"

  echo "    Probing ${URL}..."
  for ((i=1; i<=MAX_ATTEMPTS; i++)); do
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "${URL}" || true)
    if [ "${STATUS_CODE}" = "200" ]; then
      echo "    [OK] ${URL} returned 200 OK on attempt ${i}."
      return 0
    fi
    sleep "${DELAY_SEC}"
  done
  return 1
}

probe_endpoint "${CANDIDATE_API_URL}/health" || {
  echo "❌ CRITICAL: Candidate API failed /health probe! Aborting traffic shift." >&2
  exit 1
}
probe_endpoint "${CANDIDATE_API_URL}/readyz" || {
  echo "❌ CRITICAL: Candidate API failed /readyz probe! Aborting traffic shift." >&2
  exit 1
}
probe_endpoint "${CANDIDATE_WEB_URL}/" || {
  echo "❌ CRITICAL: Candidate Web failed root probe! Aborting traffic shift." >&2
  exit 1
}

echo "    [OK] All candidate health and readiness probes PASSED."

# ── 6. Atomic 100% Traffic Shift ──────────────────────────────────────────────
echo ""
echo "--> [6/6] Executing atomic 100% live traffic cutover..."

gcloud run services update-traffic lienmark-api \
  --platform=managed --region="${REGION}" --project="${TARGET_PROJECT_ID}" \
  --to-revisions="${CANDIDATE_API_REV}=100"

gcloud run services update-traffic lienmark-web \
  --platform=managed --region="${REGION}" --project="${TARGET_PROJECT_ID}" \
  --to-revisions="${CANDIDATE_WEB_REV}=100"

echo "    [OK] 100% live traffic shifted to candidate revisions."

# ── 7. Emit Promotion Confirmation Log ────────────────────────────────────────
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "${OUTPUT_DIR}/demo_promotion_log.json" <<EOF
{
  "status": "SUCCESS",
  "promoted_at": "${TIMESTAMP}",
  "source_environment": "dev",
  "source_project": "${SOURCE_PROJECT_ID}",
  "target_environment": "demo",
  "target_project": "${TARGET_PROJECT_ID}",
  "region": "${REGION}",
  "git_commit": "${GIT_COMMIT}",
  "git_commit_short": "${GIT_COMMIT_SHORT}",
  "services": {
    "lienmark-api": {
      "source_digest": "${API_SOURCE_DIGEST}",
      "target_digest": "${TARGET_API_DIGEST_REF}",
      "sha256": "${API_SHA256}",
      "digest_match": true,
      "candidate_revision": "${CANDIDATE_API_REV}",
      "candidate_url": "${CANDIDATE_API_URL}",
      "health_check": "PASSED",
      "traffic_percent": 100
    },
    "lienmark-web": {
      "source_digest": "${WEB_SOURCE_DIGEST}",
      "target_digest": "${TARGET_WEB_DIGEST_REF}",
      "sha256": "${WEB_SHA256}",
      "digest_match": true,
      "candidate_revision": "${CANDIDATE_WEB_REV}",
      "candidate_url": "${CANDIDATE_WEB_URL}",
      "health_check": "PASSED",
      "traffic_percent": 100
    }
  }
}
EOF

echo ""
echo "=== ✅ RELEASE PROMOTION COMPLETE ==="
echo "Promotion Log: ${OUTPUT_DIR}/demo_promotion_log.json"
echo "Judge Demo API: $(gcloud run services describe lienmark-api --platform managed --region "${REGION}" --project "${TARGET_PROJECT_ID}" --format 'value(status.url)')"
echo "Judge Demo Web: $(gcloud run services describe lienmark-web --platform managed --region "${REGION}" --project "${TARGET_PROJECT_ID}" --format 'value(status.url)')"
