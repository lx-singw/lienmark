# Multi-stage Production Dockerfile for Lienmark API (Google Cloud Run)
# Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon

ARG PYTHON_VERSION=3.11

# ==============================================================================
# Stage 1: Builder
# ==============================================================================
FROM python:${PYTHON_VERSION}-slim as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# Stage 2: Final Production Runner
# ==============================================================================
FROM python:${PYTHON_VERSION}-slim as runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

RUN mkdir -p /app/backend /app/poller_watch_dir /app/output && \
    chown -R appuser:appgroup /app

COPY --chown=appuser:appgroup . ./backend/

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
