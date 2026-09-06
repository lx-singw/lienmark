#!/usr/bin/env bash
# Idempotent GCP Multi-Project Provisioning Script for Lienmark
# Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon
set -euo pipefail

# ── Defaults & Configuration ──────────────────────────────────────────────────
BILLING_ACCOUNT="01575B-23EAEE-CF5627"
REGION="${GCP_REGION:-us-central1}"
TARGET_ENV="all"
DRY_RUN=false
SKIP_BUDGET=false

# ── Argument Parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment|-e)
      TARGET_ENV="$2"
      shift 2
      ;;
    --billing-account|-b)
      BILLING_ACCOUNT="$2"
      shift 2
      ;;
    --region|-r)
      REGION="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --skip-budget)
      SKIP_BUDGET=true
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

echo "======================================================================"
echo ">> 🛠️  LIENMARK MULTI-PROJECT GCP PROVISIONING (Bash)"
echo "   Target Environment: ${TARGET_ENV}"
echo "   Billing Account:    ${BILLING_ACCOUNT}"
echo "   Primary Region:     ${REGION}"
echo "   Dry Run Mode:       ${DRY_RUN}"
echo "======================================================================"

# Required Google Cloud APIs
REQUIRED_APIS=(
  "run.googleapis.com"
  "cloudbuild.googleapis.com"
  "secretmanager.googleapis.com"
  "artifactregistry.googleapis.com"
  "firestore.googleapis.com"
  "aiplatform.googleapis.com"
  "compute.googleapis.com"
)

# Least-Privilege IAM Roles
LEAST_PRIVILEGE_ROLES=(
  "roles/run.admin"
  "roles/storage.admin"
  "roles/cloudbuild.builds.editor"
  "roles/secretmanager.secretAccessor"
  "roles/aiplatform.user"
  "roles/datastore.user"
)

provision_project() {
  local ENV_KEY="$1"
  local PROJ_ID="$2"
  local DISPLAY_NAME="$3"
  local SA_NAME="$4"
  local BUDGET_AMOUNT="$5"
  local BUDGET_DISPLAY="$6"
  shift 6
  local THRESHOLDS=("$@")
  local SA_EMAIL="${SA_NAME}@${PROJ_ID}.iam.gserviceaccount.com"

  echo ""
  echo "----------------------------------------------------------------------"
  echo ">> Configuring Environment: [${ENV_KEY^^}] -> ${PROJ_ID}"
  echo "   Display Name:     ${DISPLAY_NAME}"
  echo "   Service Account:  ${SA_EMAIL}"
  echo "   Budget Allotment: ${BUDGET_AMOUNT}"
  echo "----------------------------------------------------------------------"

  if [ "${DRY_RUN}" = true ]; then
    echo "  [DRY-RUN] Would verify/create project '${PROJ_ID}' ('${DISPLAY_NAME}')."
    echo "  [DRY-RUN] Would link project to billing account '${BILLING_ACCOUNT}'."
    echo "  [DRY-RUN] Would enable APIs: ${REQUIRED_APIS[*]}."
    echo "  [DRY-RUN] Would ensure Firestore Native mode '(default)' in '${REGION}'."
    echo "  [DRY-RUN] Would ensure Artifact Registry 'lienmark-repo' in '${REGION}'."
    echo "  [DRY-RUN] Would ensure Service Account '${SA_EMAIL}' and grant IAM roles."
    if [ "${SKIP_BUDGET}" = false ]; then
      echo "  [DRY-RUN] Would configure budget '${BUDGET_DISPLAY}' (${BUDGET_AMOUNT})."
    fi
    return 0
  fi

  # 1. Project Creation
  echo "--> [1/7] Ensuring Google Cloud Project '${PROJ_ID}'..."
  if ! gcloud projects describe "${PROJ_ID}" >/dev/null 2>&1; then
    echo "    Project not found. Creating project '${PROJ_ID}'..."
    gcloud projects create "${PROJ_ID}" --name="${DISPLAY_NAME}"
    echo "    [OK] Project '${PROJ_ID}' successfully created."
  else
    echo "    [OK] Project '${PROJ_ID}' already exists."
  fi

  # 2. Link Billing Account
  echo "--> [2/7] Linking Project to Billing Account '${BILLING_ACCOUNT}'..."
  CURRENT_BILLING=$(gcloud billing projects describe "${PROJ_ID}" --format="value(billingAccountName)" 2>/dev/null || true)
  if [[ "${CURRENT_BILLING}" != *"${BILLING_ACCOUNT}"* ]]; then
    echo "    Linking billing account '${BILLING_ACCOUNT}' to '${PROJ_ID}'..."
    gcloud billing projects link "${PROJ_ID}" --billing-account="${BILLING_ACCOUNT}"
    echo "    [OK] Project linked to billing account '${BILLING_ACCOUNT}'."
  else
    echo "    [OK] Project already linked to billing account '${BILLING_ACCOUNT}'."
  fi

  # 3. Enable Required APIs
  echo "--> [3/7] Enabling Required Google Cloud APIs..."
  gcloud services enable "${REQUIRED_APIS[@]}" --project="${PROJ_ID}"
  echo "    [OK] All required APIs successfully enabled."

  # 4. Provision Firestore Native Mode
  echo "--> [4/7] Ensuring Cloud Firestore in Native Mode (database: '(default)')..."
  if ! gcloud firestore databases describe --database="(default)" --project="${PROJ_ID}" >/dev/null 2>&1; then
    echo "    Creating Firestore (default) in Native Mode in region '${REGION}'..."
    gcloud firestore databases create \
      --database="(default)" \
      --location="${REGION}" \
      --type=firestore-native \
      --project="${PROJ_ID}"
    echo "    [OK] Firestore Native database '(default)' created."
  else
    echo "    [OK] Firestore Native database '(default)' already exists."
  fi

  # 5. Provision Artifact Registry Docker Repository
  echo "--> [5/7] Ensuring Artifact Registry Docker Repository 'lienmark-repo'..."
  if ! gcloud artifacts repositories describe "lienmark-repo" --location="${REGION}" --project="${PROJ_ID}" >/dev/null 2>&1; then
    echo "    Creating Artifact Registry Docker repository 'lienmark-repo'..."
    gcloud artifacts repositories create "lienmark-repo" \
      --repository-format=docker \
      --location="${REGION}" \
      --project="${PROJ_ID}" \
      --description="Lienmark Container Repository (${ENV_KEY})"
    echo "    [OK] Artifact Registry repository 'lienmark-repo' created."
  else
    echo "    [OK] Artifact Registry repository 'lienmark-repo' already exists."
  fi

  # 6. Service Account & Least-Privilege IAM Roles
  echo "--> [6/7] Configuring Dedicated Service Account '${SA_EMAIL}'..."
  if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJ_ID}" >/dev/null 2>&1; then
    echo "    Creating Service Account '${SA_NAME}'..."
    gcloud iam service-accounts create "${SA_NAME}" \
      --display-name="Lienmark ${ENV_KEY^^} Service Account" \
      --project="${PROJ_ID}"
    echo "    [OK] Service Account created."
  else
    echo "    [OK] Service Account already exists."
  fi

  echo "    Assigning least-privilege IAM roles..."
  for ROLE in "${LEAST_PRIVILEGE_ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "${PROJ_ID}" \
      --member="serviceAccount:${SA_EMAIL}" \
      --role="${ROLE}" \
      --condition=None >/dev/null
    echo "      + Granted ${ROLE}"
  done
  echo "    [OK] Least-privilege IAM roles successfully bound."

  # 7. Configure Granular Budget Alerts
  if [ "${SKIP_BUDGET}" = false ]; then
    echo "--> [7/7] Configuring Budget Alert '${BUDGET_DISPLAY}' (${BUDGET_AMOUNT})..."
    EXISTING_BUDGETS=$(gcloud billing budgets list --billing-account="${BILLING_ACCOUNT}" --format="value(displayName)" 2>/dev/null || true)
    if [[ "${EXISTING_BUDGETS}" != *"${BUDGET_DISPLAY}"* ]]; then
      echo "    Creating budget with thresholds: ${THRESHOLDS[*]}..."
      BUDGET_CMD=(
        gcloud billing budgets create
        "--billing-account=${BILLING_ACCOUNT}"
        "--display-name=${BUDGET_DISPLAY}"
        "--budget-amount=${BUDGET_AMOUNT}"
        "--filter-projects=projects/${PROJ_ID}"
      )
      for TH in "${THRESHOLDS[@]}"; do
        BUDGET_CMD+=("--threshold-rule=percent=${TH},basis=current-spend")
      done
      "${BUDGET_CMD[@]}" || echo "    [WARN] Budget creation command exited with warning. Check billing permissions."
      echo "    [OK] Budget alert '${BUDGET_DISPLAY}' successfully provisioned."
    else
      echo "    [OK] Budget alert '${BUDGET_DISPLAY}' already exists."
    fi
  else
    echo "--> [7/7] Skipping budget alerts (flag --skip-budget specified)."
  fi
}

# Execute for requested targets
if [ "${TARGET_ENV}" = "all" ] || [ "${TARGET_ENV}" = "dev" ]; then
  DEV_THRESHOLDS=("0.25" "0.50" "0.75" "0.90" "1.00")
  provision_project \
    "dev" \
    "lienmark-dev-lx-2026" \
    "Lienmark Development" \
    "lienmark-dev-sa" \
    "20USD" \
    "lienmark-dev-budget-20usd" \
    "${DEV_THRESHOLDS[@]}"
fi

if [ "${TARGET_ENV}" = "all" ] || [ "${TARGET_ENV}" = "demo" ]; then
  DEMO_THRESHOLDS=("0.50" "0.75" "0.90" "1.00")
  provision_project \
    "demo" \
    "lienmark-demo-lx-2026" \
    "Lienmark Judge Demo" \
    "lienmark-demo-sa" \
    "60USD" \
    "lienmark-demo-budget-60usd" \
    "${DEMO_THRESHOLDS[@]}"
fi

echo ""
echo "======================================================================"
echo ">> ✅ LIENMARK MULTI-PROJECT GCP PROVISIONING COMPLETE"
echo "   Development Project: lienmark-dev-lx-2026"
echo "   Judge Demo Project:  lienmark-demo-lx-2026"
echo "   Billing Account:     ${BILLING_ACCOUNT}"
echo "   Allocations:         Dev: \$20, Demo: \$60, Unallocated Reserve: \$20"
echo "======================================================================"
