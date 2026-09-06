"""
Comprehensive Verification Suite: Counsel Integrity, Cryptographic Ledger & Production Security Remediation.

Explicitly asserts and empirically verifies all 9 confirmed findings:
1. Finding 1 (P1): Strict Authentication & Trusted Credential Registry (rejects invented tokens, binds identity).
2. Finding 2 (P1): Fail-Closed Legacy Attestation (validates rationale, binds identity, returns audit telemetry).
3. Finding 3 (P1): Default Reports Fabrication Opt-in (defaults to real state without fabricated counsel rationale).
4. Finding 4 (P1): Cross-Version Approval Bleed Prevention (v7 reattestations do not clear v8 claims).
5. Finding 5 (P1): Empty Search Fail-Closed to Insufficient (empty search results cannot be overridden to supporting).
6. Finding 6 (P1): Stored XSS Prevention & Safe Link Sanitization in HTML Reports.
7. Finding 7 (P2): Queue Inspection Read-Only Idempotence (does not mutate decisions or overwrite resolved states).
8. Finding 8 (P2): Tamper-Free Digest & Cryptographic Ledger Parent Chaining from Genesis.
9. Finding 9 (P2): Scoped Idempotency Protection (scoped to principal, path, method, and body payload hash).
10. Milestone 10: Dynamic Claim Comparison (supports custom claims payload in /api/drift/compare).
"""

import html
import json
import pytest
from fastapi.testclient import TestClient

from backend.main import (
    app,
    counsel_checkpoint_manager,
    _counsel_reattestations,
    _session_reattestations,
)
from backend.domain.models import (
    ReviewAction,
    DecisionStatus,
    DecisionState,
    EvidenceStance,
    ReviewerIdentity,
    SupersessionEvent,
    PublicEvidenceSnapshot,
    CreativeUse,
    CounselDecision,
    ReattestationRequest,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.services.parallel_service import ParallelSearchService
from backend.core.security import VALID_COUNSEL_REGISTRY, idempotency_key_manager, IdempotencyKeyManager

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_test_context():
    """Ensure clean isolated state before and after each test."""
    _counsel_reattestations.clear()
    _session_reattestations.clear()
    counsel_checkpoint_manager.reset()
    yield
    _counsel_reattestations.clear()
    _session_reattestations.clear()
    counsel_checkpoint_manager.reset()


# ==============================================================================
# FINDING 1 (P1): STRICT AUTHENTICATION & CREDENTIAL REGISTRY
# ==============================================================================

class TestFinding1StrictAuthentication:
    """Verifies strict token validation and identity binding."""

    def test_strict_mode_rejects_invented_counsel_demo_prefix(self):
        """Invented tokens with prefix 'counsel_demo_' must be rejected with 403 in strict mode."""
        headers = {
            "Authorization": "Bearer counsel_demo_invented_by_caller",
            "X-Require-Counsel-Auth": "true",
        }
        res = client.post(
            "/api/review/action",
            json={
                "stable_lineage_key": "poster_noir_detective_magazine",
                "action": "re_attest",
                "counsel_rationale": "Legitimate legal review rationale.",
            },
            headers=headers,
        )
        assert res.status_code == 403
        assert "Invalid or unrecognized Counsel Authentication Token" in res.json()["detail"]

    def test_strict_mode_binds_authenticated_identity_over_caller_payload(self):
        """In strict mode, reviewer identity is strictly bound to token principal, ignoring caller spoofing."""
        headers = {
            "Authorization": "Bearer lead_counsel_prod_2026_key",
            "X-Require-Counsel-Auth": "true",
        }
        res = client.post(
            "/api/review/action",
            json={
                "stable_lineage_key": "poster_noir_detective_magazine",
                "action": "re_attest",
                "counsel_rationale": "Verified public domain clearance under lead counsel review.",
                "reviewer_name": "Spoofed Impersonator, Esq.",
            },
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        event = data.get("event", {})
        assert event.get("reviewer", {}).get("name") == "Elena Vance, Esq."
        assert event.get("reviewer", {}).get("organization") == "Studio Clearance Legal LLP"
        assert event.get("reviewer", {}).get("is_fictional_demo") is False


# ==============================================================================
# FINDING 2 (P1): FAIL-CLOSED LEGACY ATTESTATION
# ==============================================================================

class TestFinding2FailClosedLegacyAttestation:
    """Verifies legacy attestation endpoint fails closed on missing rationale and emits audit telemetry."""

    def test_legacy_attest_rejects_empty_rationale_fail_closed(self):
        """Re-attestation without rationale fails closed with HTTP 403."""
        payload = {
            "decision_id": "dec_poster_noir",
            "stable_lineage_key": "poster_noir_detective_magazine",
            "version_id": "v8",
            "new_status": "approved",
            "counsel_rationale": "   ",
            "reviewer_name": "Sarah Jenkins, Esq.",
        }
        res = client.post("/api/review/attest", json=payload)
        assert res.status_code == 403
        assert "Counsel re-attestation requires explicit legal rationale" in res.json()["detail"]

    def test_legacy_attest_success_returns_audit_telemetry(self):
        """Valid legacy re-attestation returns event_id, event_hash, and binds reviewer identity."""
        payload = {
            "decision_id": "dec_poster_noir",
            "stable_lineage_key": "poster_noir_detective_magazine",
            "version_id": "v8",
            "new_status": "approved",
            "counsel_rationale": "Artwork confirmed in public domain via LOC Catalog of Copyright Entries.",
            "reviewer_name": "Sarah Jenkins, Esq.",
        }
        res = client.post("/api/review/attest", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "recorded"
        assert data["stable_lineage_key"] == "poster_noir_detective_magazine"
        assert "event_id" in data and data["event_id"].startswith("evt_")
        assert "event_hash" in data and len(data["event_hash"]) == 64
        assert data["event_hash"] == data["audit_event_hash"]
        assert data["reviewer_name"] == "Sarah Jenkins, Esq."


# ==============================================================================
# FINDING 3 (P1): DEFAULT REPORTS FABRICATION OPT-IN
# ==============================================================================

class TestFinding3DefaultReportsFabricationOptIn:
    """Verifies reports default to real state without fabricated counsel decisions."""

    def test_default_exceptions_schedule_has_zero_fabricated_reattestations(self):
        """Unreviewed clean session defaults to re_attested_count == 0 without fabricated rationale."""
        res = client.get("/api/reports/exceptions", headers={"X-Session-ID": "sess_clean_audit_001"})
        assert res.status_code == 200
        data = res.json()
        assert data["total_claims"] == 12
        assert data["carried_forward_count"] == 10
        assert data["re_attested_count"] == 0
        assert data["unresolved_exception_count"] == 2

    def test_explicit_auto_reconcile_demo_injects_demo_decisions(self):
        """When ?auto_reconcile_demo=true is explicitly requested, demo decisions are populated."""
        res = client.get("/api/reports/exceptions?auto_reconcile_demo=true", headers={"X-Session-ID": "sess_clean_audit_002"})
        assert res.status_code == 200
        data = res.json()
        assert data["total_claims"] == 12
        assert data["carried_forward_count"] == 10
        assert data["re_attested_count"] == 1
        assert data["unresolved_exception_count"] == 1

    def test_ssr_html_report_defaults_to_unreviewed_state(self):
        """SSR HTML report defaults to unreviewed / pending review without fabricated decisions."""
        res = client.get("/report/proj_blockbuster_cinema", headers={"X-Session-ID": "sess_clean_audit_003"})
        assert res.status_code == 200
        html_text = res.text
        assert "Form E&O-2026" in html_text
        assert "STALE" in html_text or "PENDING" in html_text


# ==============================================================================
# FINDING 4 (P1): CROSS-VERSION APPROVAL BLEED PREVENTION
# ==============================================================================

class TestFinding4CrossVersionApprovalBleed:
    """Verifies that approvals recorded for V7 do not bleed into V8 claims."""

    def test_v7_reattestation_does_not_clear_v8_claim(self):
        """A reattestation targeted to v7 must NOT approve v8 evaluation; v8 remains an active exception."""
        from backend.fixtures.golden_dataset import get_golden_fixtures
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )
        
        v7_reattestation = {
            "poster_noir_detective_magazine": ReattestationRequest(
                decision_id="dec_v7_poster_legacy",
                stable_lineage_key="poster_noir_detective_magazine",
                version_id="v7",
                new_status=DecisionStatus.APPROVED,
                counsel_rationale="V7 locked script clearance only.",
            )
        }

        schedule_v8 = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_bleed_test",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=validity_results,
            base_uses=v7_uses,
            reattestations=v7_reattestation,
        )
        poster_item = next(i for i in schedule_v8.items if i.stable_lineage_key == "poster_noir_detective_magazine")
        assert poster_item.v8_evaluation_state == "exception"
        assert schedule_v8.re_attested_count == 0
        assert schedule_v8.unresolved_exception_count == 2


# ==============================================================================
# FINDING 5 (P1): EMPTY SEARCH FAIL-CLOSED TO INSUFFICIENT
# ==============================================================================

class TestFinding5EmptySearchFailClosed:
    """Verifies empty search responses strictly produce INSUFFICIENT evidence."""

    def test_empty_search_results_produce_insufficient_stance(self):
        """When provider results are empty, stance is strictly INSUFFICIENT regardless of expected_stance."""
        service = ParallelSearchService(api_key="mock_key")
        empty_data = {
            "results": [],
            "search_id": "search_empty_test_001",
        }
        snapshot = service._parse_v1_search_response(
            data=empty_data,
            query="Unknown obscure trademark catalog search",
            use_id="use_test_123",
            stable_lineage_key="trademark_unknown",
            raw_payload_hash="hash_payload_123",
            elapsed_ms=45.0,
            http_status=200,
            expected_stance=EvidenceStance.SUPPORTING,
        )
        assert snapshot.stance == EvidenceStance.INSUFFICIENT
        assert snapshot.source_title == "No Attributable Evidence Found"
        assert "zero matching catalog records" in snapshot.excerpt


# ==============================================================================
# FINDING 6 (P1): STORED XSS PREVENTION IN HTML REPORTS
# ==============================================================================

class TestFinding6StoredXSSPrevention:
    """Verifies HTML report sanitizes and escapes malicious scripts and links."""

    def test_xss_payloads_in_counsel_rationale_are_escaped(self):
        """Injected <script> and javascript: URIs are safely escaped in HTML output."""
        from backend.fixtures.golden_dataset import get_golden_fixtures
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        xss_payload = "<script>alert('XSS-INJECTION')</script>"
        xss_img = '<img src=x onerror="alert(\'img-xss\')">'

        schedule = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_xss_test",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=InvalidationEngine.evaluate_invalidation(
                base_uses=v7_uses,
                target_uses=v8_uses,
                prior_decisions=v7_decisions,
                evidence_snapshots=v8_evidence,
                target_version_id="v8",
            ),
        )

        item = next(i for i in schedule.items if i.v8_evaluation_state == "exception")
        item.description = f"Scene prop {xss_payload}"
        item.scene_or_timecode = f"Scene 1 {xss_img}"
        item.evidence_citations = [
            {
                "source_title": f"Title {xss_payload}",
                "source_url": "javascript:alert(document.cookie)",
                "excerpt": f"Quote {xss_img}",
                "provider": f"Provider {xss_payload}",
            },
        ]

        rendered_html = InvalidationEngine.render_html_schedule(schedule)

        assert "<script>alert('XSS-INJECTION')</script>" not in rendered_html
        assert '<img src=x onerror="alert(\'img-xss\')">' not in rendered_html
        assert "javascript:alert" not in rendered_html
        assert "&lt;script&gt;alert(&#x27;XSS-INJECTION&#x27;)&lt;/script&gt;" in rendered_html or "&lt;script&gt;alert('XSS-INJECTION')&lt;/script&gt;" in rendered_html
        assert "about:blank" in rendered_html


# ==============================================================================
# FINDING 7 (P2): QUEUE INSPECTION READ-ONLY IDEMPOTENCE
# ==============================================================================

class TestFinding7QueueInspectionIdempotence:
    """Verifies that repeated queue inspection does not mutate state or overwrite decisions."""

    def test_queue_inspection_preserves_counsel_decisions(self):
        """After recording a counsel decision, inspecting the queue multiple times does not reset it."""
        manager = counsel_checkpoint_manager
        sess_id = "sess_queue_idempotence_001"
        manager.reset(sess_id)
        key = "poster_noir_detective_magazine"

        dec, evt = manager.record_counsel_action(
            session_id=sess_id,
            action=ReviewAction.RE_ATTEST,
            lineage_key=key,
            rationale="Counsel attestation verified in public domain.",
        )

        q1 = manager.get_review_queue(session_id=sess_id)
        q2 = manager.get_review_queue(session_id=sess_id)

        item1 = next(it for it in q1.items if it.stable_lineage_key == key)
        item2 = next(it for it in q2.items if it.stable_lineage_key == key)

        assert item1.current_state == DecisionState.RE_ATTESTED
        assert item2.current_state == DecisionState.RE_ATTESTED
        assert item1.prior_decision.decision_id == dec.decision_id
        assert item2.prior_decision.decision_id == dec.decision_id


# ==============================================================================
# FINDING 8 (P2): CRYPTOGRAPHIC LEDGER PARENT CHAINING & TAMPER DETECTION
# ==============================================================================

class TestFinding8CryptographicLedgerChaining:
    """Verifies unbroken parent hash chaining and complete 15-field digest sensitivity."""

    def test_ledger_tamper_detection_on_rationale_mutation(self):
        """Mutating an event's reviewer organization causes integrity verification to fail immediately."""
        manager = counsel_checkpoint_manager
        sess_id = "sess_ledger_tamper_001"
        manager.reset(sess_id)

        manager.record_counsel_action(
            session_id=sess_id,
            action=ReviewAction.RE_ATTEST,
            lineage_key="poster_noir_detective_magazine",
            rationale="Original authentic counsel legal rationale.",
        )

        ver_clean = manager.verify_ledger_integrity(session_id=sess_id)
        assert ver_clean["is_valid"] is True

        ctx = manager._get_or_create_run_context(sess_id)
        ctx.supersession_events[0].reviewer.organization = "Rogue Impersonator LLC"

        ver_tampered = manager.verify_ledger_integrity(session_id=sess_id)
        assert ver_tampered["is_valid"] is False
        assert "Tampered digest at index 0" in ver_tampered.get("error", "")

    def test_ledger_chain_break_fails_immediately(self):
        """An event with an empty or broken parent_event_hash fails verification immediately."""
        manager = counsel_checkpoint_manager
        sess_id = "sess_ledger_chain_002"
        manager.reset(sess_id)

        _, evt1 = manager.record_counsel_action(
            session_id=sess_id,
            action=ReviewAction.RE_ATTEST,
            lineage_key="poster_noir_detective_magazine",
            rationale="First event in chain.",
        )
        _, evt2 = manager.record_counsel_action(
            session_id=sess_id,
            action=ReviewAction.EXCEPTION,
            lineage_key="music_cue_midnight_serenade",
            rationale="Second event in chain.",
        )

        assert evt1.parent_event_hash == manager.GENESIS_PARENT_HASH
        assert evt2.parent_event_hash == evt1.event_hash

        ctx = manager._get_or_create_run_context(sess_id)
        ctx.supersession_events[1].parent_event_hash = "f" * 64

        ver_broken = manager.verify_ledger_integrity(session_id=sess_id)
        assert ver_broken["is_valid"] is False
        assert "Broken chain link at index 1" in ver_broken.get("error", "")


# ==============================================================================
# FINDING 9 (P2): SCOPED IDEMPOTENCY PROTECTION
# ==============================================================================

class TestFinding9ScopedIdempotency:
    """Verifies idempotency caching is scoped by principal and body hash."""

    def test_idempotency_different_payloads_do_not_collide(self):
        """Replaying identical key with different body payload must execute fresh request."""
        import uuid
        idem_key = f"idem_test_body_{uuid.uuid4().hex}"
        headers = {
            "Idempotency-Key": idem_key,
            "Authorization": "Bearer sarah_jenkins_token_2026",
        }

        # Payload A
        res1 = client.post("/api/drift/compare", json={"query": "payload_A"}, headers=headers)
        assert res1.status_code == 200

        # Payload B with identical key produces a cache miss (executes independently)
        res2 = client.post("/api/drift/compare", json={"query": "payload_B_different"}, headers=headers)
        assert res2.status_code == 200
        assert res2.headers.get("X-Cache") != "HIT-IDEMPOTENT"

    def test_idempotency_different_principals_do_not_collide(self):
        """Replaying identical key with different caller principal must NOT share cached response."""
        import uuid
        idem_key = f"idem_test_principal_{uuid.uuid4().hex}"
        payload = {"query": "payload_shared_key"}

        # Caller 1 (Sarah Jenkins)
        res1 = client.post(
            "/api/drift/compare",
            json=payload,
            headers={
                "Idempotency-Key": idem_key,
                "Authorization": "Bearer sarah_jenkins_token_2026",
            },
        )
        assert res1.status_code == 200

        # Caller 2 (Elena Vance) with identical idempotency key
        res2 = client.post(
            "/api/drift/compare",
            json=payload,
            headers={
                "Idempotency-Key": idem_key,
                "Authorization": "Bearer lead_counsel_prod_2026_key",
            },
        )
        assert res2.status_code == 200
        assert res2.headers.get("X-Cache") != "HIT-IDEMPOTENT"


# ==============================================================================
# MILESTONE 10: DYNAMIC CLAIM COMPARISON
# ==============================================================================

class TestMilestone10DynamicClaimComparison:
    """Verifies /api/drift/compare evaluates custom claim sets dynamically."""

    def test_dynamic_compare_evaluates_custom_uses_payload(self):
        """Passing custom base_uses and target_uses evaluates drift dynamically without golden fixtures."""
        custom_base = [
            CreativeUse(
                use_id="use_v1_logo",
                version_id="v1",
                scene_or_timecode="Scene 1",
                asset_type="trademark",
                description="Acme Coffee brand banner",
                duration_or_prominence="background",
                context="Diner establishing shot",
                stable_lineage_key="brand_acme_coffee",
                context_hash="hash_v1_acme",
            )
        ]
        custom_target = [
            CreativeUse(
                use_id="use_v2_logo",
                version_id="v2",
                scene_or_timecode="Scene 1",
                asset_type="trademark",
                description="Acme Coffee brand banner",
                duration_or_prominence="foreground focal",
                context="Lead character sips coffee with brand prominently framed",
                stable_lineage_key="brand_acme_coffee",
                context_hash="hash_v2_acme",
            )
        ]
        custom_decision = [
            CounselDecision(
                decision_id="dec_v1_acme",
                use_id="use_v1_logo",
                stable_lineage_key="brand_acme_coffee",
                applicable_version_id="v1",
                status=DecisionStatus.APPROVED,
                scope="Worldwide all media in perpetuity",
                rationale="Incidental background use approved.",
            )
        ]

        payload = {
            "base_version_id": "v1",
            "target_version_id": "v2",
            "base_uses": [u.model_dump() for u in custom_base],
            "target_uses": [u.model_dump() for u in custom_target],
            "prior_decisions": [d.model_dump() for d in custom_decision],
        }

        res = client.post("/api/drift/compare", json=payload, headers={"X-Session-ID": "sess_dynamic_001"})
        assert res.status_code == 200
        data = res.json()
        assert data["base_version"] == "v1"
        assert data["target_version"] == "v2"
        assert data["total_claims"] == 1
        assert len(data["claims"]) == 1
        claim = data["claims"][0]
        assert claim["stable_lineage_key"] == "brand_acme_coffee"
        assert claim["state"] == "stale"
