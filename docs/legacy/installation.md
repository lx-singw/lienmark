# Installation & Local Setup Guide — Lienmark

This guide provides step-by-step instructions for installing, configuring, testing, and running **Lienmark** locally and deploying to Google Cloud Platform.

---

## 1. System Requirements & Minimums

| Category | Requirement | Minimum Recommendation |
|---|---|---|
| **Operating System** | macOS 12+, Ubuntu 22.04 LTS, Windows WSL2 (Ubuntu) | Linux / macOS preferred |
| **Python Runtime** | Python 3.11 or 3.12 | `python3 --version` >= 3.11 |
| **Node.js Runtime** | Node.js 18.x or 20.x LTS, npm 9+ | `node -v` >= 18.0.0 |
| **Containers & Cloud CLI** | Docker Engine 24+, Google Cloud SDK (`gcloud`) | Docker & `gcloud` installed |
| **Hardware Minimums** | 4 CPU Cores, 8 GB RAM, 10 GB Disk Space | 16 GB RAM recommended |

---

## 2. Step-by-Step Setup Instructions

### Step 1: Clone the Repository & Configure Workspace
```bash
git clone https://github.com/lx-singw/lienmark.git
cd lienmark
```

### Step 2: Environment Variable Configuration
Copy the template `.env.example` file and configure your API keys:
```bash
cp .env.example .env
```
Edit `.env` and fill in your Parallel Search API key and GCP credentials:
```ini
PARALLEL_API_KEY=lm_live_your_actual_api_key_here
GOOGLE_CLOUD_PROJECT=lienmark-dev
GOOGLE_APPLICATION_CREDENTIALS=./secrets/service-account.json
DEMO_MODE=true
```

### Step 3: Backend Setup & Python Dependencies
Create a virtual environment and install backend dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

### Step 4: Frontend Setup & Dependencies
Install Node dependencies for the Next.js frontend:
```bash
cd frontend
npm install
cd ..
```

### Step 5: Provision GCP Infrastructure & IAM Roles (Production/Staging)
Run the automated GCP setup script to provision Cloud Storage buckets, Firestore collections, service accounts, and IAM roles:
```bash
chmod +x scripts/setup_gcp.sh
./scripts/setup_gcp.sh
```

---

## 3. Running Local Servers & Demos

### One-Click Local Runner (Recommended)
Launch both the Python FastAPI backend and Next.js frontend concurrently with one command:
```bash
chmod +x scripts/run_local_demo.sh
./scripts/run_local_demo.sh
```
* **Frontend UI**: `http://localhost:3000`
* **Backend REST API**: `http://localhost:8080`
* **API Documentation**: `http://localhost:8080/docs`

---

## 4. Running Verification & Automated Test Suite

### 60-Second Compliance Verification Script
Run the automated judge verification script to verify Parallel API connectivity, service account IAM rules, and Firestore append-only ledger enforcement:
```bash
python scripts/verify_integrations.py
```

### Running Full Pytest Test Suite
```bash
pytest tests/test_intake_agent.py          # Intake extraction unit tests
pytest tests/test_research_agent.py        # Research agent Parallel API tests
pytest tests/test_ledger_immutability.py   # Firestore security rule tests
pytest tests/test_risk_scoring_determinism.py # Risk scoring determinism tests
pytest tests/test_e2e_pipeline.py          # End-to-end benchmark test suite
```

---

## 5. Troubleshooting Matrix

| Error Message / Symptom | Root Cause | Concrete Resolution Command |
|---|---|---|
| `ParallelAPIError: Invalid API Key` | Missing or invalid `PARALLEL_API_KEY` in `.env` | Verify `.env` contains `PARALLEL_API_KEY=...` and run `python scripts/verify_integrations.py`. |
| `PERMISSION_DENIED: False for 'create' or 'update'` | Firestore security rule blocking unauthorized ledger write | Verify service account credentials in `GOOGLE_APPLICATION_CREDENTIALS` match `sa-ledger-agent` (`07-env-vars.md` §4). |
| `Could not resolve host: github.com` / Network blip | Temporary network DNS issue during git push or API fetch | Retry with backoff: `git push origin main` or check network connection. |
| `ModuleNotFoundError: No module named 'parallel'` | `parallel-web` Python package missing from venv | Ensure virtual environment is active (`source venv/bin/activate`) and run `pip install -r backend/requirements.txt`. |
| `Port 3000 is already in use` | Another process is holding Next.js default port | Kill existing node process: `npx kill-port 3000` or run Next.js on custom port `PORT=3001 npm run dev`. |
