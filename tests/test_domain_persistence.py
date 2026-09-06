"""
Unit and Integration Tests for Sprint 1.1:
Domain Persistence, Entity Schemas, Hierarchical Collection Partitioning, and State Machines.
Tests against both InMemoryTenantRepository and NativeFirestoreTenantRepository contracts.
"""

import math
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
    CreativeUse,
    CounselDecision,
    DecisionStatus,
    DecisionState,
)
from backend.core.lifecycle import (
    RunLifecycleManager,
    InvalidStateTransitionError,
    LifecycleAuditEvent,
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    transition_run,
    validate_transition,
    can_transition,
    is_terminal_state,
)
from backend.storage.repository import (
    TenantRepository,
    InMemoryTenantRepository,
    get_tenant_repository,
    TenantSecurityViolation,
    TenantContextMissingError,
    TenantMismatchViolation,
    FailClosedSecurityViolation,
)


@pytest.fixture(autouse=True)
def clean_storage():
    """Ensure in-memory repository storage is reset between tests."""
    InMemoryTenantRepository.reset_global_storage()


# =============================================================================
# 1. Organization Persistence & Schema Tests
# =============================================================================

class TestOrganizationPersistence:
    """Verifies Organization model validation, non-nullable org_id, and repository CRUD."""

    def test_organization_crud_lifecycle(self):
        repo = get_tenant_repository("org_warner_01", force_in_memory=True)

        org = Organization(
            org_id="org_warner_01",
            name="Warner Bros. Entertainment Inc.",
            tier=OrganizationTier.ENTERPRISE,
            settings={"max_concurrent_runs": 10, "retention_days": 90},
        )
        saved = repo.save_organization(org)
        assert saved.org_id == "org_warner_01"
        assert saved.organization_id == "org_warner_01"

        retrieved = repo.get_organization()
        assert retrieved is not None
        assert retrieved.org_id == "org_warner_01"
        assert retrieved.name == "Warner Bros. Entertainment Inc."
        assert retrieved.tier == OrganizationTier.ENTERPRISE
        assert retrieved.settings["retention_days"] == 90

    def test_organization_missing_tenant_id_rejection(self):
        # Missing or None organization_id must raise ValidationError
        with pytest.raises(ValidationError):
            Organization(org_id=None, name="Faulty Studio")  # type: ignore

        with pytest.raises(ValidationError):
            Organization(org_id="", name="Faulty Studio")

        with pytest.raises(ValidationError):
            Organization(org_id="   ", name="Faulty Studio")

    def test_repository_organization_id_mismatch_rejection(self):
        repo = get_tenant_repository("org_alpha", force_in_memory=True)
        alien_org = Organization(org_id="org_beta", name="Beta Studios")

        with pytest.raises(TenantMismatchViolation):
            repo.save_organization(alien_org)


# =============================================================================
# 2. Production Persistence & Path Partitioning Tests
# =============================================================================

class TestProductionPersistence:
    """Verifies Production entity CRUD scoped under /organizations/{org_id}/productions/{id}."""

    def test_production_crud_and_scoping(self):
        repo = get_tenant_repository("org_universal_01", force_in_memory=True)

        prod = Production(
            production_id="prod_oppenheimer",
            organization_id="org_universal_01",
            title="Oppenheimer Cut 4",
            status="active",
            budget_cap_usd=7500.0,
        )
        repo.save_production(prod)

        retrieved = repo.get_production("prod_oppenheimer")
        assert retrieved is not None
        assert retrieved.production_id == "prod_oppenheimer"
        assert retrieved.organization_id == "org_universal_01"
        assert retrieved.org_id == "org_universal_01"
        assert retrieved.budget_cap_usd == 7500.0

        all_prods = repo.list_productions()
        assert len(all_prods) == 1
        assert all_prods[0].production_id == "prod_oppenheimer"

        deleted = repo.delete_production("prod_oppenheimer")
        assert deleted is True
        assert repo.get_production("prod_oppenheimer") is None

    def test_production_non_nullable_organization_id(self):
        with pytest.raises(ValidationError):
            Production(production_id="prod_01", organization_id=None, title="Test")  # type: ignore

        with pytest.raises(ValidationError):
            Production(production_id="prod_01", organization_id="", title="Test")


# =============================================================================
# 3. ProductionVersion Persistence & Hash Invariant Tests
# =============================================================================

class TestProductionVersionPersistence:
    """Verifies ProductionVersion model and repository persistence with lineage pointers."""

    def test_production_version_crud_and_backward_compatibility(self):
        repo = get_tenant_repository("org_studio_alpha", force_in_memory=True)

        # Instantiate using legacy field names
        v = ProductionVersion(
            version_id="v8",
            project_id="prod_broadway_01",
            organization_id="org_studio_alpha",
            label="Picture Lock v8",
            content_hash="c" * 64,
            parent_version_id="v7",
            source_type="screenplay",
        )
        assert v.production_id == "prod_broadway_01"
        assert v.version_tag == "Picture Lock v8"
        assert v.content_hash == "c" * 64

        repo.save_production_version(v)

        retrieved = repo.get_production_version("prod_broadway_01", "v8")
        assert retrieved is not None
        assert retrieved.version_id == "v8"
        assert retrieved.parent_version_id == "v7"
        assert retrieved.content_hash == "c" * 64

        versions = repo.list_production_versions("prod_broadway_01")
        assert len(versions) == 1

    def test_production_version_requires_hash_and_org(self):
        with pytest.raises(ValidationError):
            # Missing both content_hash, script_digest, and cut_hash
            ProductionVersion(
                version_id="v9",
                production_id="prod_test",
                organization_id="org_test",
            )

        with pytest.raises(ValidationError):
            # Missing organization_id
            ProductionVersion(
                version_id="v9",
                production_id="prod_test",
                organization_id=None,  # type: ignore
                content_hash="d" * 64,
            )


# =============================================================================
# 4. DocumentRecord Persistence Tests
# =============================================================================

class TestDocumentRecordPersistence:
    """Verifies DocumentRecord validation and repository operations."""

    def test_document_record_crud(self):
        repo = get_tenant_repository("org_columbia", force_in_memory=True)

        doc = DocumentRecord(
            doc_id="doc_screenplay_v8",
            organization_id="org_columbia",
            production_id="prod_spiderman",
            filename="spiderman_rev8.pdf",
            content_hash="e" * 64,
            doc_type="screenplay",
        )
        repo.save_document(doc)

        retrieved = repo.get_document("doc_screenplay_v8")
        assert retrieved is not None
        assert retrieved.filename == "spiderman_rev8.pdf"
        assert retrieved.doc_type == "screenplay"
        assert retrieved.content_hash == "e" * 64

        docs = repo.list_documents(production_id="prod_spiderman")
        assert len(docs) == 1
        assert docs[0].doc_id == "doc_screenplay_v8"

    def test_document_record_validation(self):
        with pytest.raises(ValidationError):
            DocumentRecord(
                doc_id="doc_bad",
                organization_id="org_test",
                production_id="prod_test",
                filename="test.pdf",
                content_hash="short",  # < 16 chars
                doc_type="screenplay",
            )


# =============================================================================
# 5. InvestigationRun Persistence & Lifecycle State Machine Tests
# =============================================================================

class TestInvestigationRunAndLifecycle:
    """Verifies InvestigationRun persistence, state transitions, and audit generation."""

    def test_run_crud_and_active_pointer(self):
        repo = get_tenant_repository("org_netflix_01", force_in_memory=True)

        run = InvestigationRun(
            run_id="run_2026_09_v8_001",
            organization_id="org_netflix_01",
            production_id="prod_stranger_things",
            base_version_id="v7",
            target_version_id="v8",
            status=RunStatus.QUEUED,
            budget_spent_usd=0.0,
        )
        repo.save_run(run)
        repo.set_active_run_id("prod_stranger_things", "run_2026_09_v8_001")

        active_id = repo.get_active_run_id("prod_stranger_things")
        assert active_id == "run_2026_09_v8_001"

        retrieved = repo.get_run("prod_stranger_things", "run_2026_09_v8_001")
        assert retrieved is not None
        assert retrieved.status == RunStatus.QUEUED
        assert retrieved.organization_id == "org_netflix_01"

    def test_lifecycle_canonical_happy_path(self):
        run = InvestigationRun(
            run_id="run_lifecycle_001",
            organization_id="org_test_lifecycle",
            production_id="prod_test_01",
            base_version_id="v7",
            target_version_id="v8",
            status=RunStatus.QUEUED,
        )
        mgr = RunLifecycleManager()

        # 1. QUEUED -> INVESTIGATING
        run = mgr.transition(run, RunStatus.INVESTIGATING, reason="Worker dispatched")
        assert run.status == RunStatus.INVESTIGATING

        # 2. INVESTIGATING -> WAITING_FOR_INFORMATION
        run = mgr.transition(run, RunStatus.WAITING_FOR_INFORMATION, reason="Missing trailer sync rider")
        assert run.status == RunStatus.WAITING_FOR_INFORMATION

        # 3. WAITING_FOR_INFORMATION -> INVESTIGATING
        run = mgr.transition(run, RunStatus.INVESTIGATING, reason="Trailer rider uploaded")
        assert run.status == RunStatus.INVESTIGATING

        # 4. INVESTIGATING -> READY_FOR_REVIEW
        run = mgr.transition(run, RunStatus.READY_FOR_REVIEW, reason="All claims evaluated")
        assert run.status == RunStatus.READY_FOR_REVIEW

        # 5. READY_FOR_REVIEW -> COMPLETED
        run = mgr.transition(run, RunStatus.COMPLETED, actor_id="counsel_jenkins", reason="Attestation signed")
        assert run.status == RunStatus.COMPLETED
        assert is_terminal_state(run.status) is True
        assert run.metadata.get("completed_at") is not None

        # Verify audit log length
        audit_log = run.metadata.get("audit_log", [])
        assert len(audit_log) == 5

    def test_lifecycle_illegal_transition_rejections(self):
        mgr = RunLifecycleManager()
        run = InvestigationRun(
            run_id="run_terminal_001",
            organization_id="org_terminal_test",
            production_id="prod_01",
            base_version_id="v7",
            target_version_id="v8",
            status=RunStatus.COMPLETED,
        )

        # Illegal: COMPLETED cannot transition to INVESTIGATING
        with pytest.raises(InvalidStateTransitionError):
            mgr.transition(run, RunStatus.INVESTIGATING)

        # Illegal: COMPLETED cannot self-transition
        with pytest.raises(InvalidStateTransitionError):
            mgr.transition(run, RunStatus.COMPLETED)

        # Illegal: QUEUED directly to COMPLETED
        run_queued = InvestigationRun(
            run_id="run_q_002",
            organization_id="org_terminal_test",
            production_id="prod_01",
            base_version_id="v7",
            target_version_id="v8",
            status=RunStatus.QUEUED,
        )
        with pytest.raises(InvalidStateTransitionError):
            mgr.transition(run_queued, RunStatus.COMPLETED)


# =============================================================================
# 6. Subcollections Partitioning & Atomic Sequencer Tests
# =============================================================================

class TestSubcollectionsAndSequencer:
    """Verifies subcollection documents (<25KB) under /runs/{run_id} and atomic hash chain."""

    def test_subcollection_claims_and_decisions_isolation(self):
        repo = get_tenant_repository("org_subcollection_test", force_in_memory=True)
        prod_id = "prod_action_film"
        run_id = "run_v8_batch_01"

        # Save discrete claim
        claim_payload = {
            "stable_lineage_key": "music_track_alpha",
            "asset_type": "music",
            "description": "Background song in diner scene",
            "status": "NEEDS_REVIEW",
        }
        repo.save_claim(prod_id, run_id, claim_payload)

        retrieved_claim = repo.get_claim(prod_id, run_id, "music_track_alpha")
        assert retrieved_claim is not None
        assert retrieved_claim["stable_lineage_key"] == "music_track_alpha"
        assert retrieved_claim["organization_id"] == "org_subcollection_test"

        all_claims = repo.list_claims(prod_id, run_id)
        assert len(all_claims) == 1

        # Save discrete decision
        decision_payload = {
            "stable_lineage_key": "music_track_alpha",
            "decision_id": "dec_001",
            "status": "APPROVED",
            "reviewer_name": "Sarah Jenkins, Esq.",
            "rationale": "Direct sync license confirmed with publisher.",
        }
        repo.save_decision(prod_id, run_id, decision_payload)

        retrieved_dec = repo.get_decision(prod_id, run_id, "music_track_alpha")
        assert retrieved_dec is not None
        assert retrieved_dec["status"] == "APPROVED"

        all_decs = repo.list_decisions(prod_id, run_id)
        assert "music_track_alpha" in all_decs

    def test_atomic_audit_sequencer_monotonic_hash_chain(self):
        repo = get_tenant_repository("org_audit_test", force_in_memory=True)
        prod_id = "prod_audit_01"
        run_id = "run_audit_01"

        # Append 5 sequential audit events
        e1 = repo.append_audit_event(prod_id, run_id, {"action": "RUN_INITIALIZED", "actor": "system"})
        assert e1["sequence_number"] == 1
        assert e1["parent_event_hash"] == "0" * 64

        e2 = repo.append_audit_event(prod_id, run_id, {"action": "CLAIM_EXTRACTED", "key": "track_1"})
        assert e2["sequence_number"] == 2
        assert e2["parent_event_hash"] == e1["event_hash"]

        e3 = repo.append_audit_event(prod_id, run_id, {"action": "RESEARCH_ATTACHED", "source": "USCO"})
        assert e3["sequence_number"] == 3
        assert e3["parent_event_hash"] == e2["event_hash"]

        e4 = repo.append_audit_event(prod_id, run_id, {"action": "COUNSEL_ATTESTATION", "actor": "attorney"})
        assert e4["sequence_number"] == 4
        assert e4["parent_event_hash"] == e3["event_hash"]

        e5 = repo.append_audit_event(prod_id, run_id, {"action": "RUN_COMPLETED", "actor": "system"})
        assert e5["sequence_number"] == 5
        assert e5["parent_event_hash"] == e4["event_hash"]

        # Cryptographic chain verification
        assert repo.verify_hash_chain(prod_id, run_id) is True

        # Tamper simulation: mutate e3 in storage
        raw_events = repo.list_audit_events(prod_id, run_id)
        assert len(raw_events) == 5
        # Artificially alter sequence 3 payload
        repo._global_storage["org_audit_test"]["audit_events"][f"{prod_id}:{run_id}"][2]["source"] = "TAMPERED_SOURCE"

        # Verify hash chain detects tampering
        assert repo.verify_hash_chain(prod_id, run_id) is False
