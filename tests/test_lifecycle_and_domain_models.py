"""
Unit and Integration Tests for Sprint 1.1:
Domain Models (Organization, Production, ProductionVersion, DocumentRecord, InvestigationRun)
and Lifecycle State Machine (RunStatus, transitions, InvalidStateTransitionError, audit logging).
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from backend.domain.models import (
    Organization,
    OrganizationTier,
    Production,
    ProductionVersion,
    DocumentRecord,
    InvestigationRun,
    RunStatus,
)
from backend.core.lifecycle import (
    InvalidStateTransitionError,
    LifecycleAuditEvent,
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    validate_transition,
    transition_run,
    RunLifecycleManager,
    can_transition,
    is_terminal_state,
    get_allowed_transitions,
)


# =============================================================================
# 1. Organization Model Tests
# =============================================================================

def test_organization_canonical_instantiation():
    """Verify Organization model instantiates cleanly with all required fields."""
    org = Organization(
        org_id="org_studio_alpha",
        name="Studio Alpha Productions LLC",
        tier=OrganizationTier.ENTERPRISE,
        settings={"max_concurrent_runs": 10, "default_budget_cap_usd": 10000.0},
    )
    assert org.org_id == "org_studio_alpha"
    assert org.organization_id == "org_studio_alpha"
    assert org.name == "Studio Alpha Productions LLC"
    assert org.tier == OrganizationTier.ENTERPRISE
    assert org.settings["max_concurrent_runs"] == 10
    assert org.created_at is not None


def test_organization_alias_and_property():
    """Verify organization_id works as alias and property."""
    org = Organization(
        organization_id="org_paramount_01",
        name="Paramount Clearances",
        tier="studio",
    )
    assert org.org_id == "org_paramount_01"
    assert org.organization_id == "org_paramount_01"


def test_organization_strictly_enforces_non_nullable_organization_id():
    """Verify Organization fails closed when organization_id/org_id is None or empty."""
    with pytest.raises(ValidationError):
        Organization(org_id=None, name="Bad Org")

    with pytest.raises(ValidationError):
        Organization(organization_id=None, name="Bad Org")

    with pytest.raises(ValidationError):
        Organization(org_id="", name="Bad Org")

    with pytest.raises(ValidationError):
        Organization(org_id="   ", name="Bad Org")

    with pytest.raises(ValidationError):
        Organization(name="Bad Org without ID")


def test_organization_roundtrip_serialization():
    """Verify dict and JSON serialization round-trip for Organization."""
    org = Organization(
        org_id="org_universal_studios",
        name="Universal Studios",
        tier="enterprise",
        settings={"clearance_mode": "strict"},
    )
    dumped = org.model_dump()
    reloaded = Organization.model_validate(dumped)
    assert reloaded == org

    json_str = org.model_dump_json()
    reloaded_json = Organization.model_validate_json(json_str)
    assert reloaded_json == org


# =============================================================================
# 2. Production Model Tests
# =============================================================================

def test_production_canonical_instantiation():
    """Verify Production model instantiates cleanly with all required fields."""
    prod = Production(
        production_id="prod_shadows_broadway",
        organization_id="org_studio_alpha",
        title="Shadows Over Broadway",
        status="active",
        budget_cap_usd=25000.0,
    )
    assert prod.production_id == "prod_shadows_broadway"
    assert prod.organization_id == "org_studio_alpha"
    assert prod.org_id == "org_studio_alpha"
    assert prod.title == "Shadows Over Broadway"
    assert prod.status == "active"
    assert prod.budget_cap_usd == 25000.0
    assert prod.created_at is not None


def test_production_strictly_enforces_non_nullable_organization_id():
    """Verify Production fails closed when organization_id is None or empty."""
    with pytest.raises(ValidationError):
        Production(
            production_id="prod_test",
            organization_id=None,
            title="Test Movie",
        )

    with pytest.raises(ValidationError):
        Production(
            production_id="prod_test",
            organization_id="",
            title="Test Movie",
        )

    with pytest.raises(ValidationError):
        Production(
            production_id="prod_test",
            organization_id="   ",
            title="Test Movie",
        )

    with pytest.raises(ValidationError):
        Production(
            production_id="prod_test",
            title="Test Movie without org",
        )


def test_production_roundtrip_serialization():
    """Verify dict and JSON serialization round-trip for Production."""
    prod = Production(
        production_id="prod_indie_01",
        organization_id="org_indie_collective",
        title="Midnight Express Cut",
        budget_cap_usd=3000.0,
    )
    reloaded = Production.model_validate(prod.model_dump())
    assert reloaded == prod

    reloaded_json = Production.model_validate_json(prod.model_dump_json())
    assert reloaded_json == prod


# =============================================================================
# 3. ProductionVersion Model Tests
# =============================================================================

def test_production_version_canonical_sprint_1_1_fields():
    """Verify ProductionVersion with canonical Sprint 1.1 fields."""
    pv = ProductionVersion(
        version_id="v8",
        production_id="prod_broadway_01",
        organization_id="org_studio_alpha",
        version_tag="Picture Lock v8",
        script_digest="a" * 64,
        cut_hash="b" * 64,
    )
    assert pv.version_id == "v8"
    assert pv.production_id == "prod_broadway_01"
    assert pv.project_id == "prod_broadway_01"  # Synced
    assert pv.organization_id == "org_studio_alpha"
    assert pv.version_tag == "Picture Lock v8"
    assert pv.label == "Picture Lock v8"  # Synced
    assert pv.script_digest == "a" * 64
    assert pv.cut_hash == "b" * 64
    assert pv.content_hash == "a" * 64  # Synced


def test_production_version_strictly_enforces_non_nullable_organization_id():
    """Verify ProductionVersion fails closed when organization_id is None."""
    with pytest.raises(ValidationError):
        ProductionVersion(
            version_id="v8",
            production_id="prod_test",
            organization_id=None,
            version_tag="v8",
            script_digest="a" * 64,
        )

    with pytest.raises(ValidationError):
        ProductionVersion(
            version_id="v8",
            production_id="prod_test",
            organization_id="",
            version_tag="v8",
            script_digest="a" * 64,
        )


def test_production_version_requires_content_hash():
    """Verify ProductionVersion fails when all content hash fields are missing."""
    with pytest.raises(ValidationError) as exc_info:
        ProductionVersion(
            version_id="v8",
            production_id="prod_test",
            organization_id="org_test",
            label="Cut without content hash",
        )
    assert "content_hash" in str(exc_info.value)


# =============================================================================
# 4. DocumentRecord Model Tests
# =============================================================================

def test_document_record_canonical_instantiation():
    """Verify DocumentRecord instantiates cleanly with all required fields."""
    doc = DocumentRecord(
        doc_id="doc_screenplay_v8",
        organization_id="org_studio_alpha",
        production_id="prod_broadway_01",
        filename="Shadows_Over_Broadway_v8_Locked.pdf",
        content_hash="d" * 64,
        doc_type="screenplay",
    )
    assert doc.doc_id == "doc_screenplay_v8"
    assert doc.organization_id == "org_studio_alpha"
    assert doc.org_id == "org_studio_alpha"
    assert doc.production_id == "prod_broadway_01"
    assert doc.filename == "Shadows_Over_Broadway_v8_Locked.pdf"
    assert doc.content_hash == "d" * 64
    assert doc.doc_type == "screenplay"
    assert doc.uploaded_at is not None


def test_document_record_strictly_enforces_non_nullable_organization_id():
    """Verify DocumentRecord fails closed when organization_id is None or empty."""
    with pytest.raises(ValidationError):
        DocumentRecord(
            doc_id="doc_1",
            organization_id=None,
            production_id="prod_1",
            filename="file.pdf",
            content_hash="c" * 64,
        )

    with pytest.raises(ValidationError):
        DocumentRecord(
            doc_id="doc_1",
            organization_id="",
            production_id="prod_1",
            filename="file.pdf",
            content_hash="c" * 64,
        )


def test_document_record_roundtrip_serialization():
    """Verify dict and JSON serialization round-trip for DocumentRecord."""
    doc = DocumentRecord(
        doc_id="doc_license_01",
        organization_id="org_studio_alpha",
        production_id="prod_broadway_01",
        filename="Times_Square_Signage_Sync_License.pdf",
        content_hash="e" * 64,
        doc_type="license",
    )
    reloaded = DocumentRecord.model_validate(doc.model_dump())
    assert reloaded == doc

    reloaded_json = DocumentRecord.model_validate_json(doc.model_dump_json())
    assert reloaded_json == doc


# =============================================================================
# 5. InvestigationRun Model Tests
# =============================================================================

def test_investigation_run_canonical_instantiation():
    """Verify InvestigationRun instantiates cleanly with defaults."""
    run = InvestigationRun(
        run_id="run_2026_09_v8_001",
        organization_id="org_studio_alpha",
        production_id="prod_broadway_01",
        base_version_id="v7",
        target_version_id="v8",
    )
    assert run.run_id == "run_2026_09_v8_001"
    assert run.organization_id == "org_studio_alpha"
    assert run.org_id == "org_studio_alpha"
    assert run.production_id == "prod_broadway_01"
    assert run.base_version_id == "v7"
    assert run.target_version_id == "v8"
    assert run.status == RunStatus.QUEUED
    assert run.budget_spent_usd == 0.0
    assert run.metadata == {}
    assert run.created_at is not None
    assert run.updated_at is not None


def test_investigation_run_strictly_enforces_non_nullable_organization_id():
    """Verify InvestigationRun fails closed when organization_id is missing or None."""
    with pytest.raises(ValidationError):
        InvestigationRun(
            run_id="run_bad",
            organization_id=None,
            production_id="prod_1",
            base_version_id="v7",
            target_version_id="v8",
        )

    with pytest.raises(ValidationError):
        InvestigationRun(
            run_id="run_bad",
            organization_id="",
            production_id="prod_1",
            base_version_id="v7",
            target_version_id="v8",
        )

    with pytest.raises(ValidationError):
        InvestigationRun(
            run_id="run_bad",
            production_id="prod_1",
            base_version_id="v7",
            target_version_id="v8",
        )


def test_investigation_run_roundtrip_serialization():
    """Verify dict and JSON serialization round-trip for InvestigationRun."""
    run = InvestigationRun(
        run_id="run_test_roundtrip",
        organization_id="org_paramount",
        production_id="prod_top_gun",
        base_version_id="v1",
        target_version_id="v2",
        status=RunStatus.INVESTIGATING,
        budget_spent_usd=42.50,
        metadata={"step_count": 5},
    )
    reloaded = InvestigationRun.model_validate(run.model_dump())
    assert reloaded == run

    reloaded_json = InvestigationRun.model_validate_json(run.model_dump_json())
    assert reloaded_json == run


# =============================================================================
# 6. Lifecycle State Machine & Transition Tests
# =============================================================================

def test_lifecycle_all_states_exist():
    """Verify all 9 canonical run states exist in RunStatus."""
    expected_states = {
        "queued",
        "investigating",
        "waiting_for_information",
        "waiting_for_budget",
        "ready_for_review",
        "completed",
        "failed",
        "cancelled",
        "superseded",
    }
    actual_states = {s.value for s in RunStatus}
    assert expected_states.issubset(actual_states)


def test_lifecycle_allowed_happy_path_flow():
    """Verify the standard happy-path lifecycle flow from queued to completed."""
    run = InvestigationRun(
        run_id="run_happy_path",
        organization_id="org_studio_alpha",
        production_id="prod_broadway_01",
        base_version_id="v7",
        target_version_id="v8",
    )
    assert run.status == RunStatus.QUEUED

    # 1. queued -> investigating
    run = transition_run(run, RunStatus.INVESTIGATING, actor_id="adk_dispatcher", reason="Job picked by queue")
    assert run.status == RunStatus.INVESTIGATING

    # 2. investigating -> waiting_for_information
    run = transition_run(run, RunStatus.WAITING_FOR_INFORMATION, actor_id="agent_researcher", reason="Need music rights clarification")
    assert run.status == RunStatus.WAITING_FOR_INFORMATION

    # 3. waiting_for_information -> investigating
    run = transition_run(run, RunStatus.INVESTIGATING, actor_id="clearance_coordinator", reason="Provided sync license doc")
    assert run.status == RunStatus.INVESTIGATING

    # 4. investigating -> waiting_for_budget
    run = transition_run(run, RunStatus.WAITING_FOR_BUDGET, actor_id="spend_guard", reason="Hit $50 threshold")
    assert run.status == RunStatus.WAITING_FOR_BUDGET

    # 5. waiting_for_budget -> investigating
    run = transition_run(run, RunStatus.INVESTIGATING, actor_id="studio_admin", reason="Budget cap elevated to $100")
    assert run.status == RunStatus.INVESTIGATING

    # 6. investigating -> ready_for_review
    run = transition_run(run, RunStatus.READY_FOR_REVIEW, actor_id="adk_pipeline", reason="Reconciliation complete")
    assert run.status == RunStatus.READY_FOR_REVIEW

    # 7. ready_for_review -> completed
    run = transition_run(run, RunStatus.COMPLETED, actor_id="counsel_attorney", reason="All claims cleared and attested")
    assert run.status == RunStatus.COMPLETED

    # Verify audit log exists on run.metadata
    audit_log = run.metadata.get("audit_log")
    assert audit_log is not None
    assert len(audit_log) == 7
    assert run.metadata.get("completed_at") is not None
    assert run.metadata.get("terminal_timestamp") is not None


def test_lifecycle_reinvestigation_loop():
    """Verify counsel can send a run from ready_for_review back to investigating."""
    run = InvestigationRun(
        run_id="run_reinvestigate",
        organization_id="org_studio_alpha",
        production_id="prod_broadway_01",
        base_version_id="v7",
        target_version_id="v8",
        status=RunStatus.READY_FOR_REVIEW,
    )
    run = transition_run(
        run,
        RunStatus.INVESTIGATING,
        actor_id="attorney_reviewer",
        reason="Counsel requested deeper USPTO trademark search",
    )
    assert run.status == RunStatus.INVESTIGATING


def test_lifecycle_illegal_transition_completed_to_investigating():
    """Verify completed -> investigating raises InvalidStateTransitionError."""
    run = InvestigationRun(
        run_id="run_completed_terminal",
        organization_id="org_studio_alpha",
        production_id="prod_broadway_01",
        base_version_id="v7",
        target_version_id="v8",
        status=RunStatus.COMPLETED,
    )
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        transition_run(run, RunStatus.INVESTIGATING)

    err = exc_info.value
    assert err.current_state == RunStatus.COMPLETED
    assert err.target_state == RunStatus.INVESTIGATING
    assert "completed" in str(err)
    assert "investigating" in str(err)


def test_lifecycle_illegal_transitions_matrix():
    """Verify multiple illegal transitions across lifecycle states raise InvalidStateTransitionError."""
    illegal_cases = [
        (RunStatus.QUEUED, RunStatus.COMPLETED),              # Cannot skip investigation
        (RunStatus.QUEUED, RunStatus.READY_FOR_REVIEW),       # Cannot skip investigation
        (RunStatus.INVESTIGATING, RunStatus.COMPLETED),       # Must go through review
        (RunStatus.WAITING_FOR_INFORMATION, RunStatus.COMPLETED), # Cannot bypass review
        (RunStatus.WAITING_FOR_BUDGET, RunStatus.COMPLETED),  # Cannot bypass review
        (RunStatus.FAILED, RunStatus.INVESTIGATING),          # Terminal state
        (RunStatus.CANCELLED, RunStatus.INVESTIGATING),       # Terminal state
        (RunStatus.SUPERSEDED, RunStatus.INVESTIGATING),      # Terminal state
        (RunStatus.COMPLETED, RunStatus.QUEUED),              # Terminal state
        (RunStatus.COMPLETED, RunStatus.CANCELLED),           # Terminal state
        (RunStatus.INVESTIGATING, RunStatus.INVESTIGATING),   # Self-transition disallowed
    ]

    for from_state, to_state in illegal_cases:
        run = InvestigationRun(
            run_id=f"run_test_{from_state.value}_to_{to_state.value}",
            organization_id="org_studio_alpha",
            production_id="prod_broadway_01",
            base_version_id="v7",
            target_version_id="v8",
            status=from_state,
        )
        assert not can_transition(from_state, to_state)
        with pytest.raises(InvalidStateTransitionError):
            transition_run(run, to_state)


def test_lifecycle_superseded_transitions():
    """Verify any non-terminal state can be superseded when a newer script arrives."""
    non_terminal_states = [
        RunStatus.QUEUED,
        RunStatus.INVESTIGATING,
        RunStatus.WAITING_FOR_INFORMATION,
        RunStatus.WAITING_FOR_BUDGET,
        RunStatus.READY_FOR_REVIEW,
    ]
    for state in non_terminal_states:
        run = InvestigationRun(
            run_id=f"run_supersede_{state.value}",
            organization_id="org_studio_alpha",
            production_id="prod_broadway_01",
            base_version_id="v7",
            target_version_id="v8",
            status=state,
        )
        assert can_transition(state, RunStatus.SUPERSEDED)
        updated = transition_run(run, RunStatus.SUPERSEDED, reason="New cut v9 ingested")
        assert updated.status == RunStatus.SUPERSEDED
        assert updated.metadata.get("terminal_timestamp") is not None


def test_lifecycle_manager_audit_ledger():
    """Verify RunLifecycleManager tracks full audit history across multiple transitions."""
    manager = RunLifecycleManager(default_actor="orchestrator")
    run = InvestigationRun(
        run_id="run_managed_001",
        organization_id="org_netflix",
        production_id="prod_stranger_cut",
        base_version_id="v1",
        target_version_id="v2",
    )

    manager.transition(run, RunStatus.INVESTIGATING, actor_id="adk_agent", reason="Started analysis")
    manager.transition(run, RunStatus.READY_FOR_REVIEW, actor_id="adk_pipeline", reason="Analysis done")
    manager.transition(run, RunStatus.COMPLETED, actor_id="legal_counsel", reason="Signed off")

    history = manager.get_audit_history("run_managed_001")
    assert len(history) == 3
    assert history[0].from_state == RunStatus.QUEUED
    assert history[0].to_state == RunStatus.INVESTIGATING
    assert history[1].from_state == RunStatus.INVESTIGATING
    assert history[1].to_state == RunStatus.READY_FOR_REVIEW
    assert history[2].from_state == RunStatus.READY_FOR_REVIEW
    assert history[2].to_state == RunStatus.COMPLETED
    assert history[2].actor_id == "legal_counsel"
    assert history[2].organization_id == "org_netflix"


def test_lifecycle_tenant_boundary_defense():
    """Verify transition fails closed if organization_id is somehow compromised/empty."""
    run = InvestigationRun(
        run_id="run_compromised",
        organization_id="org_test",
        production_id="prod_1",
        base_version_id="v7",
        target_version_id="v8",
    )
    # Tamper with internal organization_id to simulate tenant boundary corruption
    object.__setattr__(run, "organization_id", "")
    with pytest.raises(ValueError) as exc_info:
        transition_run(run, RunStatus.INVESTIGATING)
    assert "organization_id" in str(exc_info.value)
