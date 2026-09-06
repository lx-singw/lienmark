"""
backend/orchestration/agent_builder_config.py

Lienmark Google Cloud Agent Builder & ADK Configuration.
Defines GCP environment parameters, OpenTelemetry / Cloud Trace integration,
and backwards-compatible initialization hooks.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger("lienmark.orchestration.agent_builder_config")


class AgentBuilderConfig(BaseModel):
    """
    Configuration model for Google Cloud Agent Builder and Google ADK.
    Provides project, location, agent identifier, foundational model,
    and distributed tracing settings.
    """
    project_id: str = Field(
        default_factory=lambda: (
            os.getenv("AGENT_BUILDER_PROJECT_ID")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or os.getenv("GCP_PROJECT")
            or "lienmark-hackathon"
        ),
        description="Google Cloud Project ID hosting Agent Builder / Vertex AI",
    )
    location: str = Field(
        default_factory=lambda: (
            os.getenv("AGENT_BUILDER_LOCATION")
            or os.getenv("GOOGLE_CLOUD_REGION")
            or "us-central1"
        ),
        description="GCP Region for Agent Builder / Vertex AI endpoints (us-central1)",
    )
    agent_id: str = Field(
        default_factory=lambda: (
            os.getenv("AGENT_BUILDER_AGENT_ID")
            or "clearance_change_control_agent"
        ),
        description="Configured Agent Builder Agent Identifier",
    )
    model: str = Field(
        default_factory=lambda: (
            os.getenv("AGENT_BUILDER_MODEL")
            or os.getenv("GEMINI_FLASH_MODEL")
            or "gemini-2.5-flash"
        ),
        description="Default Gemini foundational model for ADK orchestration (gemini-2.5-flash)",
    )
    engine_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("AGENT_BUILDER_ENGINE_ID"),
        description="Optional Vertex AI Search / Agent Builder Engine ID",
    )
    enable_cloud_trace: bool = Field(
        default_factory=lambda: (
            os.getenv("ENABLE_CLOUD_TRACE", "true").lower() in ("true", "1", "yes")
        ),
        description="Whether to export distributed spans to GCP Cloud Trace",
    )
    trace_sample_rate: float = Field(
        default_factory=lambda: float(os.getenv("AGENT_BUILDER_TRACE_SAMPLE_RATE", "1.0")),
        description="Trace sampling probability between 0.0 and 1.0",
    )
    credentials_path: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        description="Path to GCP Service Account JSON key",
    )
    mcp_config_path: str = Field(
        default_factory=lambda: os.path.join(
            os.path.dirname(__file__), "agent_builder_mcp_config.json"
        ),
        description="Path to Model Context Protocol (MCP) server configurations",
    )

    @property
    def is_configured(self) -> bool:
        """Returns True if the essential Agent Builder project and location are defined."""
        return bool(self.project_id and self.location and self.model)


# Module-level singletons
_config_instance: Optional[AgentBuilderConfig] = None
_tracer_provider: Optional[Any] = None
_tracer: Optional[Any] = None


def is_live_adk_available() -> bool:
    """
    Determines whether live Google ADK and Vertex AI execution is viable.
    Checks ADC tokens, credentials, or valid GEMINI_API_KEY.
    """
    cfg = get_agent_builder_config()
    has_sa = bool(cfg.credentials_path and os.path.exists(cfg.credentials_path))
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    has_gemini = bool(gemini_key and not gemini_key.startswith("mock") and len(gemini_key) > 8)
    has_gcp_env = bool(
        os.getenv("K_SERVICE")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCP_PROJECT")
    )
    return has_sa or has_gemini or has_gcp_env


def configure_tracer(config: Optional[AgentBuilderConfig] = None) -> Any:
    """
    Configures OpenTelemetry TracerProvider with Cloud Trace exporter if available.
    Preserves audit trails without failing closed if GCP credentials or exporter are absent.
    """
    global _tracer_provider, _tracer
    cfg = config or get_agent_builder_config()

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, ParentBased
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({
            "service.name": "lienmark-clearance-adk",
            "service.version": "1.0.0",
            "cloud.provider": "gcp",
            "gcp.project_id": cfg.project_id,
            "gcp.zone": cfg.location,
            "agent.id": cfg.agent_id,
        })

        sampler = ParentBased(TraceIdRatioBased(cfg.trace_sample_rate))
        provider = TracerProvider(resource=resource, sampler=sampler)

        if cfg.enable_cloud_trace and is_live_adk_available():
            try:
                from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
                from opentelemetry.sdk.trace.export import BatchSpanProcessor
                cloud_exporter = CloudTraceSpanExporter(project_id=cfg.project_id)
                provider.add_span_processor(BatchSpanProcessor(cloud_exporter))
                logger.info(f"Cloud Trace exporter enabled for project '{cfg.project_id}'.")
            except ImportError:
                logger.debug("opentelemetry-exporter-gcp-trace not installed; using standard TracerProvider.")
            except Exception as e:
                logger.warning(f"Failed to initialize CloudTraceSpanExporter: {e}")

        trace.set_tracer_provider(provider)
        _tracer_provider = provider
        _tracer = trace.get_tracer("lienmark.adk", "1.0.0")
        return _tracer
    except Exception as ex:
        logger.debug(f"OpenTelemetry tracer initialization: {ex}")
        return None


def get_tracer() -> Any:
    """Returns the active OpenTelemetry Tracer."""
    global _tracer
    if _tracer is None:
        _tracer = configure_tracer()
    return _tracer


def get_agent_builder_config() -> AgentBuilderConfig:
    """Returns the cached singleton instance of AgentBuilderConfig."""
    global _config_instance
    if _config_instance is None:
        _config_instance = AgentBuilderConfig()
    return _config_instance


def init() -> AgentBuilderConfig:
    """
    Preserved for backwards compatibility with earlier initializers.
    Initializes Google Cloud Agent Builder configuration and sets up tracing.
    """
    cfg = get_agent_builder_config()
    configure_tracer(cfg)
    return cfg
