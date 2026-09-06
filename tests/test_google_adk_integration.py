"""
Google ADK (Agent Development Kit) & Agent Builder Integration Tests.
Verifies real Google ADK classes, tool definitions, agent orchestration,
workflow graph execution, fallback resilience, FastAPI endpoint, and
the 12 -> 10/2 clearance change control invariant.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app, counsel_checkpoint_manager
from backend.orchestration.agent_builder_config import (
    AgentBuilderConfig,
    get_agent_builder_config,
    configure_tracer,
    get_tracer,
    is_live_adk_available,
    init as config_init,
)
from backend.orchestration.adk_pipeline import (
    evaluate_clearance_drift_tool,
    revalidate_evidence_tool,
    build_adk_clearance_workflow,
    ADKClearancePipeline,
    run_adk_clearance_workflow,
)
from backend.orchestration.workflow import LienmarkWorkflow, WorkflowRunResult
from backend.middleware.spend_guard import spend_guard_manager


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_counsel_state():
    yield
    counsel_checkpoint_manager.reset()


# ============================================================================
# Module 1: Google ADK Imports & Core Configurations
# ============================================================================

def test_google_adk_core_imports():
    """Verify that official google.adk packages and classes import correctly."""
    import google.adk
    from google.adk import Workflow, Runner, Agent
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool
    from google.adk.sessions import InMemorySessionService

    assert hasattr(google.adk, "__version__")
    assert issubclass(LlmAgent, Agent)
    assert Workflow is not None
    assert Runner is not None
    assert FunctionTool is not None
    assert InMemorySessionService is not None


def test_agent_builder_config_initialization():
    """Verify AgentBuilderConfig loads defaults and preserves init() compatibility."""
    config = get_agent_builder_config()
    assert isinstance(config, AgentBuilderConfig)
    assert config.location == "us-central1"
    assert config.model == "gemini-2.5-flash"
    assert config.agent_id == "clearance_change_control_agent"
    assert config.is_configured is True

    # Check tracer initialization
    tracer = configure_tracer()
    assert tracer is not None
    assert get_tracer() is not None

    # Check backward-compatible init()
    res = config_init()
    assert res is not None
    assert res.agent_id == "clearance_change_control_agent"


# ============================================================================
# Module 2: ADK Tools Definition & Direct Invocation
# ============================================================================

@pytest.mark.asyncio
async def test_evaluate_clearance_drift_tool():
    """Verify evaluate_clearance_drift_tool executes semantic delta analysis."""
    from google.adk.tools import FunctionTool

    tool = FunctionTool(func=evaluate_clearance_drift_tool)
    assert tool.name == "evaluate_clearance_drift_tool"
    assert "Gemini" in tool.description

    # Test direct async invocation with sample payloads
    v7_claims = [{"stable_lineage_key": "c1", "description": "Artwork on wall", "duration_or_prominence": "wide 2s"}]
    v8_claims = [{"stable_lineage_key": "c1", "description": "Artwork on wall closeup", "duration_or_prominence": "closeup 10s"}]

    result = await evaluate_clearance_drift_tool(v7_claims, v8_claims)
    assert isinstance(result, dict)
    assert "total_claims" in result
    assert "drifted_count" in result
    assert "unaffected_count" in result
    assert "drift_details" in result


@pytest.mark.asyncio
async def test_revalidate_evidence_tool():
    """Verify revalidate_evidence_tool runs targeted search via Parallel API adapter."""
    from google.adk.tools import FunctionTool

    tool = FunctionTool(func=revalidate_evidence_tool)
    assert tool.name == "revalidate_evidence_tool"
    assert "Parallel" in tool.description

    result = await revalidate_evidence_tool(
        query="Detective Magazine 1948 cover copyright renewal LOC",
        asset_key="poster_noir_detective_magazine",
        objective="Verify public domain renewal status",
    )
    assert isinstance(result, dict)
    assert result["stable_lineage_key"] == "poster_noir_detective_magazine"
    assert "excerpt" in result
    assert "stance" in result
    assert "source_url" in result


# ============================================================================
# Module 3: ADK Workflow Construction & Schema Verification
# ============================================================================

def test_build_adk_clearance_workflow_graph():
    """Verify build_adk_clearance_workflow constructs the multi-agent graph with sub-agents."""
    from google.adk import Workflow

    wf = build_adk_clearance_workflow()
    assert isinstance(wf, Workflow)
    assert "clearance" in wf.name

    # Verify nodes present in the workflow graph
    node_names = [node.name for node in wf.graph.nodes]
    assert "ingest_and_eval" in node_names
    assert "carry_forward_claims" in node_names
    assert "revalidate_drifted_claims" in node_names
    assert "reconcile_and_report" in node_names
    assert len(wf.edges) >= 4


# ============================================================================
# Module 4: ADK Pipeline Execution & Clearance Invariants (12 -> 10/2)
# ============================================================================

@pytest.mark.asyncio
async def test_adk_pipeline_execution_offline_fallback():
    """Verify ADKClearancePipeline executes deterministically in offline fallback mode."""
    pipeline = ADKClearancePipeline()
    result = await pipeline.execute(force_offline=True)

    assert isinstance(result, WorkflowRunResult)
    assert result.base_version == "v7"
    assert result.target_version == "v8"
    assert result.total_claims == 12
    assert result.carried_forward_count == 10
    assert result.reopened_count == 2
    assert len(result.claims) == 12
    assert len(result.counsel_briefings) == 2
    assert "poster_noir_detective_magazine" in result.counsel_briefings
    assert "music_cue_midnight_serenade" in result.counsel_briefings
    assert len(result.reconciliation_results) == 12
    assert result.revalidation_plan is not None
    assert result.revalidation_plan.planned_count == 2

    # Verify execution traces reflect ADK steps
    trace_components = [t.component for t in result.execution_traces]
    assert "GoogleADK" in trace_components
    assert "AgentBuilder" in trace_components


@pytest.mark.asyncio
async def test_adk_pipeline_execution_auto_mode():
    """Verify ADKClearancePipeline auto mode executes cleanly under environment conditions."""
    pipeline = ADKClearancePipeline()
    result = await pipeline.execute(force_offline=False)

    assert isinstance(result, WorkflowRunResult)
    assert result.total_claims == 12
    assert result.carried_forward_count == 10
    assert result.reopened_count == 2


@pytest.mark.asyncio
async def test_run_adk_clearance_workflow_convenience_function():
    """Verify the top-level runner function run_adk_clearance_workflow."""
    result = await run_adk_clearance_workflow(use_fallback=True)
    assert isinstance(result, WorkflowRunResult)
    assert result.total_claims == 12
    assert result.carried_forward_count == 10
    assert result.reopened_count == 2


# ============================================================================
# Module 5: LienmarkWorkflow ADK Parity
# ============================================================================

@pytest.mark.asyncio
async def test_lienmark_workflow_adk_integration():
    """Verify LienmarkWorkflow.execute_adk_workflow achieves exact parity with domain invariants."""
    workflow = LienmarkWorkflow()
    adk_result = await workflow.execute_adk_workflow(force_offline=True)

    assert isinstance(adk_result, WorkflowRunResult)
    assert adk_result.total_claims == 12
    assert adk_result.carried_forward_count == 10
    assert adk_result.reopened_count == 2

    # Check that carried forward items have $0 cost / carried state
    carried = [c for c in adk_result.claims if c["state"] == "carried_forward"]
    assert len(carried) == 10

    stale = [c for c in adk_result.claims if c["state"] == "stale"]
    assert len(stale) == 2


# ============================================================================
# Module 6: FastAPI Endpoint POST /api/adk/clearance-workflow
# ============================================================================

def test_api_adk_clearance_workflow_endpoint_default():
    """Test POST /api/adk/clearance-workflow with empty body."""
    res = client.post("/api/adk/clearance-workflow")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["orchestrator"] == "Google Cloud Agent Builder / ADK"
    assert "session_id" in data
    assert "workflow_result" in data

    wf_res = data["workflow_result"]
    assert wf_res["total_claims"] == 12
    assert wf_res["carried_forward_count"] == 10
    assert wf_res["reopened_count"] == 2
    assert len(wf_res["claims"]) == 12
    assert len(wf_res["execution_traces"]) >= 4


def test_api_adk_clearance_workflow_endpoint_explicit_payload():
    """Test POST /api/adk/clearance-workflow with explicit payload parameters."""
    payload = {
        "base_version": "v7",
        "target_version": "v8",
        "force_offline": True,
        "use_fallback": True,
    }
    res = client.post("/api/adk/clearance-workflow", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    wf_res = data["workflow_result"]
    assert wf_res["base_version"] == "v7"
    assert wf_res["target_version"] == "v8"
    assert wf_res["total_claims"] == 12
    assert wf_res["carried_forward_count"] == 10
    assert wf_res["reopened_count"] == 2


def test_api_adk_clearance_workflow_spend_guard_integration():
    """Test POST /api/adk/clearance-workflow under spend guard limit enforcement."""
    sess_id = "test-adk-spend-guard-sess"
    spend_guard_manager._session_evaluations[sess_id] = (
        spend_guard_manager.max_session_evaluations + 1
    )

    res = client.post(
        "/api/adk/clearance-workflow",
        json={"force_offline": False},
        headers={"x-session-id": sess_id},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["spend_guard_status"] == "LIMIT_EXCEEDED"
    assert "sandbox mode" in data["spend_guard_message"]

    # Invariant still holds in sandbox mode
    wf_res = data["workflow_result"]
    assert wf_res["total_claims"] == 12
    assert wf_res["carried_forward_count"] == 10
    assert wf_res["reopened_count"] == 2


# ============================================================================
# Module 7: Zero Secret Leakage Security Check
# ============================================================================

def test_zero_secret_leakage_in_adk_traces():
    """Verify that workflow traces and outputs contain zero raw credentials or secrets."""
    res = client.post("/api/adk/clearance-workflow", json={"force_offline": True})
    assert res.status_code == 200
    res_text = res.text

    sensitive_patterns = [
        "AIzaSy",  # Google API key prefix
        "Bearer ya29.",  # GCP OAuth token prefix
        "sk-ant-",  # Anthropic key
        "parallel_secret",
    ]
    for pattern in sensitive_patterns:
        assert pattern not in res_text, f"Potential secret leakage found: {pattern}"
