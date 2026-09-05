# Multi-stage Production Dockerfile for Lienmark Clearance Change Control (Google Cloud Run)
# Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon

ARG PYTHON_VERSION=3.11

# ==============================================================================
# Stage 1: Builder
# ==============================================================================
FROM python:${PYTHON_VERSION}-slim as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Install compilation and build tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create isolated virtual environment for clean layer extraction
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install backend Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# Stage 2: Final Production Runner
# ==============================================================================
FROM python:${PYTHON_VERSION}-slim as runner

# Production container environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

# Install minimal runtime dependencies (curl for health check, ca-certificates for TLS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create least-privilege non-root user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Prepare directories and permissions
RUN mkdir -p /app/backend /app/poller_watch_dir /app/output && \
    chown -R appuser:appgroup /app

# Copy backend application codebase
COPY --chown=appuser:appgroup backend/ ./backend/

# Switch to non-root user
USER appuser

# Expose standard Cloud Run container port
EXPOSE 8080

# Container Health Check (Cloud Run and Docker Engine compliant)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Production ASGI server entrypoint
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]

