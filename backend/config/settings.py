"""
settings.py

Lienmark Environment and System Configuration.
Loads environment variables and enforces validation for GCP, Gemini, Parallel, and Firestore settings.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Settings:
    # Google Cloud
    google_cloud_project: str = field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", "lienmark-hackathon"))
    google_cloud_region: str = field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_REGION", "us-central1"))
    google_application_credentials: Optional[str] = field(default_factory=lambda: os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

    # Gemini & Agent Builder
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-pro"))
    gemini_flash_model: str = field(default_factory=lambda: os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash"))
    gemini_flash_lite_model: str = field(default_factory=lambda: os.getenv("GEMINI_FLASH_LITE_MODEL", "gemini-2.5-flash-lite"))
    agent_builder_project_id: str = field(default_factory=lambda: os.getenv("AGENT_BUILDER_PROJECT_ID", "lienmark-hackathon"))
    agent_builder_location: str = field(default_factory=lambda: os.getenv("AGENT_BUILDER_LOCATION", "us-central1"))

    # Parallel Search & MCP
    parallel_api_key: Optional[str] = field(default_factory=lambda: os.getenv("PARALLEL_API_KEY"))
    parallel_search_api_base_url: str = field(default_factory=lambda: os.getenv("PARALLEL_SEARCH_API_BASE_URL", "https://api.parallel.ai"))
    parallel_mcp_server_url: str = field(default_factory=lambda: os.getenv("PARALLEL_MCP_SERVER_URL", "https://search.parallel.ai/mcp"))

    # Firestore
    firestore_project_id: str = field(default_factory=lambda: os.getenv("FIRESTORE_PROJECT_ID", "lienmark-hackathon"))
    firestore_database: str = field(default_factory=lambda: os.getenv("FIRESTORE_DATABASE", "(default)"))

    # Governance & Operational Controls
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "info"))
    demo_mode: bool = field(default_factory=lambda: os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes"))
    max_api_spend_usd: float = field(default_factory=lambda: float(os.getenv("MAX_API_SPEND_USD", "10.00")))
    max_pipeline_latency_seconds: int = field(default_factory=lambda: int(os.getenv("MAX_PIPELINE_LATENCY_SECONDS", "15")))
    gcs_watch_bucket: str = field(default_factory=lambda: os.getenv("GCS_WATCH_BUCKET", "gs://studio-locked-drafts/"))
    sir_deductible_usd: float = field(default_factory=lambda: float(os.getenv("SIR_DEDUCTIBLE_USD", "25000.0")))
    verification_ttl_days: int = field(default_factory=lambda: int(os.getenv("VERIFICATION_TTL_DAYS", "30")))
    risk_confidence_threshold: float = field(default_factory=lambda: float(os.getenv("RISK_CONFIDENCE_THRESHOLD", "0.7")))
    require_counsel_auth: bool = field(default_factory=lambda: os.getenv("REQUIRE_COUNSEL_AUTH", "false").lower() in ("true", "1", "yes"))
    service_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("SERVICE_TIMEOUT_SECONDS", "5.0")))
    max_service_retries: int = field(default_factory=lambda: int(os.getenv("MAX_SERVICE_RETRIES", "3")))
    max_payload_size_bytes: int = field(default_factory=lambda: int(os.getenv("MAX_PAYLOAD_SIZE_BYTES", str(1024 * 1024))))

# Singleton instance
settings = Settings()
