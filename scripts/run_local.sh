#!/usr/bin/env bash
# One-Click Local Development Server Runner for Lienmark (Linux/macOS)
# Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "======================================================================"
echo ">> 🚀 LIENMARK CLEARANCE CHANGE CONTROL - LOCAL SERVER"
echo "   Google AntiGravity: Agentic Cinema Hackathon"
echo "======================================================================"

# Check for Python 3
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "[ERROR] Python is not installed. Please install Python 3.11+."
    exit 1
fi

# Activate virtual environment if present
if [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    echo "--> Activating virtual environment (.venv)..."
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
elif [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    echo "--> Activating virtual environment (venv)..."
    # shellcheck disable=SC1091
    source "venv/bin/activate"
fi

# Ensure .env exists
if [ ! -f .env ] && [ -f .env.example ]; then
    echo "--> Initializing .env from .env.example..."
    cp .env.example .env
fi

# Set PYTHONPATH to project root
export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"

echo "Server starting on:"
echo "  - Local UI & Health: http://127.0.0.1:8000/"
echo "  - Interactive API Docs: http://127.0.0.1:8000/docs"
echo "  - Health Check: http://127.0.0.1:8000/health"
echo ""
echo "Press Ctrl+C to terminate the server."
echo "======================================================================"
echo ""

# Run uvicorn with live reload on port 8000
if command -v uvicorn >/dev/null 2>&1; then
    exec uvicorn backend.main:app --reload --port 8000
else
    echo "--> Direct 'uvicorn' binary not found; falling back to '${PYTHON_BIN} -m uvicorn'..."
    exec "${PYTHON_BIN}" -m uvicorn backend.main:app --reload --port 8000
fi
