#!/usr/bin/env bash
# GCP Infrastructure Setup Script for Lienmark
# Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-benchpress-ai-cloud}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_ACCOUNT_NAME="lienmark-sa"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
REPO_NAME="lienmark-repo"

echo "======================================================================"
echo ">> 🛠️ SETTING UP GCP INFRASTRUCTURE FOR LIENMARK"
echo "   Project:         ${PROJECT_ID}"
echo "   Region:          ${REGION}"
echo "   Service Account: ${SERVICE_ACCOUNT}"
echo "======================================================================"

# 1. Set gcloud configuration
gcloud config set project "${PROJECT_ID}"
gcloud config set run/region "${REGION}"

# 2. Enable Required Google Cloud APIs
echo "--> Enabling Google Cloud APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    aiplatform.googleapis.com \
    compute.googleapis.com

# 3. Create Artifact Registry Docker Repository if not existing
echo "--> Provisioning Artifact Registry repository '${REPO_NAME}'..."
if ! gcloud artifacts repositories describe "${REPO_NAME}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud artifacts repositories create "${REPO_NAME}" \
        --repository-format=docker \
        --location="${REGION}" \
        --project="${PROJECT_ID}" \
        --description="Lienmark Container Repository"
    echo "  [OK] Artifact Registry repository created"
else
    echo "  [OK] Artifact Registry repository already exists"
fi

# 4. Create Dedicated Service Account if not existing
echo "--> Configuring Service Account '${SERVICE_ACCOUNT}'..."
if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
        --display-name="Lienmark Cloud Run Service Account" \
        --project="${PROJECT_ID}"
    echo "  [OK] Service Account created"
else
    echo "  [OK] Service Account already exists"
fi

# 5. Grant Least-Privilege IAM Roles
echo "--> Assigning IAM Roles to Service Account..."
ROLES=(
    "roles/run.admin"
    "roles/storage.admin"
    "roles/cloudbuild.builds.editor"
    "roles/secretmanager.secretAccessor"
    "roles/aiplatform.user"
)

for ROLE in "${ROLES[@]}"; do
    echo "  Assigning ${ROLE}..."
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="${ROLE}" \
        --condition=None >/dev/null
done

echo "=== ✅ GCP SETUP COMPLETE ==="
echo "Project ${PROJECT_ID} is ready for Lienmark Cloud Run deployment."
