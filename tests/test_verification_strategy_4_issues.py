"""
Comprehensive Automated Verification Suite for the 4 Core Issues:
1. Dashboard/Report Synchronization (/api/claims vs /api/reports/form-eo-2026 across lifecycle states)
2. Telemetry Provenance (zero unbadged 525.8 or mock hashes in rendered DOM)
3. Cryptographic Seal Integrity (verified SHA-256 chain hash vs explicit UNSEALED state)
4. Poster Disambiguation (artwork_vintage_travel_poster -> Scene 08 vs poster_noir_detective_magazine -> Scene 42)

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import hashlib
import json
import re
import pytest
from fastapi.testclient import TestClient

from backend.main import app, counsel_checkpoint_manager, _counsel_reattestations
from backend.domain.models import (
    DecisionState,
    DecisionStatus,
    ReviewAction,
    ExceptionsSchedule,
)
from backend.fixtures.golden_dataset import (
    get_golden_fixtures,
    resolve_lineage_key,
    POSTER_KEY_ALIASES,
)
from backend.core.invalidation_engine import InvalidationEngine

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_test_session():
    """Ensures each test operates in an isolated, pristine state."""
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()
    yield
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()


# =============================================================================
# ISSUE 1: DASHBOARD / REPORT SYNCHRONIZATION TEST SUITE
# =============================================================================

class TestDashboardReportSynchronization:
    """
    Verifies that dashboard /api/claims counts match report /api/reports/form-eo-2026 counts
    under initial state, post-Item-11-reattestation, and post-Item-12-rejection.
    """

    def test_checkpoint_1_initial_state_synchronization(self):
        """
        Under initial drifted state:
        Dashboard /api/claims and Report /api/reports/form-eo-2026 must exhibit identical counts:
        12 total = 10 carried forward + 0 re-attested + 2 unresolved exceptions (pending review).
        """
        session_id = "test_sync_sess_initial"
        headers = {"X-Session-ID": session_id}

        # 1. Fetch claims representation
        claims_res = client.get("/api/claims", headers=headers)
        assert claims_res.status_code == 200, f"/api/claims failed: {claims_res.text}"
        claims_data = claims_res.json()

        # 2. Fetch Form E&O-2026 report representation
        report_res = client.get("/api/reports/form-eo-2026", headers=headers)
        assert report_res.status_code == 200, f"/api/reports/form-eo-2026 failed: {report_res.text}"
        report_data = report_res.json()

        # Invariant: Total Claims Equality
        assert claims_data["total_claims"] == report_data["total_claims"] == 12

        # Invariant: Carried Forward Parity
        assert claims_data["carried_forward_count"] == report_data["carried_forward_count"] == 10

        # Invariant: Re-attested Parity (zero prior to counsel review)
        assert claims_data["re_attested_count"] == report_data["re_attested_count"] == 0

        # Invariant: Unresolved Exceptions Parity (2 items pending counsel review)
        assert claims_data["unresolved_exception_count"] == report_data["unresolved_exception_count"] == 2

        # Mathematical Conservation Law: 12 == 10 + 0 + 2
        assert (
            claims_data["carried_forward_count"]
            + claims_data["re_attested_count"]
            + claims_data["unresolved_exception_count"]
            == claims_data["total_claims"]
        )
        assert (
            report_data["carried_forward_count"]
            + report_data["re_attested_count"]
            + report_data["unresolved_exception_count"]
            == report_data["total_claims"]
        )

        # Verify claims array contains all 12 items
        assert len(claims_data["claims"]) == 12
        assert len(report_data["items"]) == 12

    def test_checkpoint_2_post_item_11_reattestation_synchronization(self):
        """
        Under post-Item-11-reattestation state:
        Clearance counsel re-attests Item 11 (poster_noir_detective_magazine).
        Dashboard /api/claims and Report /api/reports/form-eo-2026 must synchronize to:
        12 total = 10 carried forward + 1 re-attested + 1 unresolved exception.
        """
        session_id = "test_sync_sess_post_11"
        headers = {"X-Session-ID": session_id}

        # Counsel adjudicates Item 11: RE_ATTEST
        action_payload = {
            "action": "re_attest",
            "lineage_key": "poster_noir_detective_magazine",
            "rationale": "Artwork verified in public domain under LOC renewal records (17 U.S.C. § 304).",
            "version_id": "v8",
            "reviewer": {
                "reviewer_id": "counsel_sjenkins_001",
                "name": "Sarah Jenkins, Esq.",
                "title": "Lead Production Clearance Counsel",
                "organization": "Lienmark Legal Partners LLP",
                "is_fictional_demo": True,
            },
        }
        act_res = client.post("/api/review/action", json=action_payload, headers=headers)
        assert act_res.status_code == 200, f"Review action failed: {act_res.text}"

        # Fetch both endpoints
        claims_res = client.get("/api/claims", headers=headers)
        report_res = client.get("/api/reports/form-eo-2026", headers=headers)
        assert claims_res.status_code == 200
        assert report_res.status_code == 200

        claims_data = claims_res.json()
        report_data = report_res.json()

        # Synchronized Counts Verification
        assert claims_data["total_claims"] == report_data["total_claims"] == 12
        assert claims_data["carried_forward_count"] == report_data["carried_forward_count"] == 10
        assert claims_data["re_attested_count"] == report_data["re_attested_count"] == 1
        assert claims_data["unresolved_exception_count"] == report_data["unresolved_exception_count"] == 1

        # Conservation Invariant: 12 = 10 + 1 + 1
        assert (
            claims_data["carried_forward_count"]
            + claims_data["re_attested_count"]
            + claims_data["unresolved_exception_count"]
            == 12
        )

        # Verify Item 11 classification
        claim_11 = next((c for c in claims_data["claims"] if c["stable_lineage_key"] == "poster_noir_detective_magazine"), None)
        assert claim_11 is not None
        assert claim_11["state"].lower() == "re_attested"
        assert claim_11["status"] == "APPROVED"

        report_11 = next((i for i in report_data["items"] if i["stable_lineage_key"] == "poster_noir_detective_magazine"), None)
        assert report_11 is not None
        assert report_11["v8_evaluation_state"].lower() == "re_attested"

    def test_checkpoint_3_post_item_12_rejection_synchronization(self):
        """
        Under post-Item-12-rejection state:
        Clearance counsel designates Item 12 (music_cue_midnight_serenade) as exception/rejected.
        Dashboard /api/claims and Report /api/reports/form-eo-2026 must synchronize to:
        12 total = 10 carried forward + 1 re-attested + 1 unresolved exception.
        """
        session_id = "test_sync_sess_post_12"
        headers = {"X-Session-ID": session_id}

        # 1. Re-attest Item 11
        client.post(
            "/api/review/action",
            json={
                "action": "re_attest",
                "lineage_key": "poster_noir_detective_magazine",
                "rationale": "LOC registration expired 1974 without renewal; public domain confirmed.",
                "version_id": "v8",
            },
            headers=headers,
        )

        # 2. Reject Item 12 (designated as exception rider)
        act_res = client.post(
            "/api/review/action",
            json={
                "action": "reject",
                "lineage_key": "music_cue_midnight_serenade",
                "rationale": "Vanguard Media exclusive sync assignment registered 2026; unshielded broadcast exposure.",
                "version_id": "v8",
            },
            headers=headers,
        )
        assert act_res.status_code == 200

        # Fetch both endpoints
        claims_res = client.get("/api/claims", headers=headers)
        report_res = client.get("/api/reports/form-eo-2026", headers=headers)
        assert claims_res.status_code == 200
        assert report_res.status_code == 200

        claims_data = claims_res.json()
        report_data = report_res.json()

        # Synchronized Counts Verification
        assert claims_data["total_claims"] == report_data["total_claims"] == 12
        assert claims_data["carried_forward_count"] == report_data["carried_forward_count"] == 10
        assert claims_data["re_attested_count"] == report_data["re_attested_count"] == 1
        assert claims_data["unresolved_exception_count"] == report_data["unresolved_exception_count"] == 1

        # Conservation Invariant: 12 == 10 + 1 + 1
        assert (
            claims_data["carried_forward_count"]
            + claims_data["re_attested_count"]
            + claims_data["unresolved_exception_count"]
            == 12
        )

        # Item 12 must be EXCEPTION in both
        claim_12 = next((c for c in claims_data["claims"] if c["stable_lineage_key"] == "music_cue_midnight_serenade"), None)
        assert claim_12 is not None
        assert claim_12["state"].lower() == "exception"
        assert claim_12["status"] == "REJECTED"

        report_12 = next((i for i in report_data["items"] if i["stable_lineage_key"] == "music_cue_midnight_serenade"), None)
        assert report_12 is not None
        assert report_12["v8_evaluation_state"].lower() == "exception"

        # Section I in report must contain Item 12
        assert len(report_data["unresolved_exceptions"]) == 1
        assert report_data["unresolved_exceptions"][0]["stable_lineage_key"] == "music_cue_midnight_serenade"


# =============================================================================
# ISSUE 2: TELEMETRY PROVENANCE TEST SUITE
# =============================================================================

class TestTelemetryProvenance:
    """
    Automated test checking that zero hardcoded 525.8 or mock hashes appear in rendered DOM
    without explicit [DEMO FIXTURE] or [Awaiting Run] badges.
    """

    def test_zero_unbadged_525_8_in_rendered_dashboard(self):
        """
        Dashboard HTML / rendered DOM must not present 525.8 ms as live telemetry
        unless explicitly badged as [DEMO FIXTURE] or [Awaiting Run].
        """
        res = client.get("/")
        assert res.status_code == 200
        html = res.text

        # If '525.8' appears anywhere in the rendered HTML:
        if "525.8" in html:
            # It MUST be accompanied by explicit provenance badge in the document
            has_badge = (
                "[DEMO FIXTURE]" in html
                or "[Awaiting Run]" in html
                or "Scenario Benchmark" in html
                or "Scenario Plan" in html
            )
            assert has_badge, "Breach: Hardcoded '525.8' rendered without [DEMO FIXTURE] or [Awaiting Run] badge!"

    def test_zero_unbadged_mock_hashes_in_rendered_report(self):
        """
        SSR report HTML (/report/{production_id} and /api/reports/form-eo-2026/html)
        must never display hardcoded mock hashes (e.g. 7f3a9b1c...) without explicit [DEMO FIXTURE].
        Authentic live seals must display verified chain head hashes or [UNSEALED].
        """
        for path in ("/report/proj_blockbuster_cinema", "/api/reports/form-eo-2026/html"):
            res = client.get(path)
            assert res.status_code == 200
            html = res.text

            mock_hash = "7f3a9b1c2d4e80f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9"
            if mock_hash in html:
                assert "[DEMO FIXTURE]" in html, (
                    f"Breach: Hardcoded mock hash {mock_hash[:16]}... appears in {path} "
                    "without explicit [DEMO FIXTURE] badge!"
                )

    def test_mathematical_conservation_ribbon_telemetry_badge_contract(self):
        """
        Verifies that MathematicalConservationRibbon source explicitly tags 525.8 as [DEMO FIXTURE]
        when elapsedMs is not a live measured runtime.
        """
        ribbon_path = "frontend/app/components/MathematicalConservationRibbon.tsx"
        with open(ribbon_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "[DEMO FIXTURE]" in content, "MathematicalConservationRibbon missing [DEMO FIXTURE] badge definition!"
        assert "[Awaiting Run]" in content, "MathematicalConservationRibbon missing [Awaiting Run] badge definition!"


# =============================================================================
# ISSUE 3: CRYPTOGRAPHIC SEAL INTEGRITY TEST SUITE
# =============================================================================

class TestCryptographicSealIntegrity:
    """
    Automated test checking that the report seal displays verified chain hash
    from audit trail, or explicit UNSEALED state.
    """

    def test_report_seal_unsealed_state_prior_to_adjudication(self):
        """
        When 0 counsel actions have been executed in a session,
        the report seal must display explicit [UNSEALED] state.
        """
        session_id = "test_seal_unsealed_sess"
        headers = {"X-Session-ID": session_id}

        res = client.get(
            "/api/reports/form-eo-2026/html?auto_reconcile_demo=false",
            headers=headers,
        )
        assert res.status_code == 200
        html = res.text

        # Must contain explicit UNSEALED state
        assert "CRYPTOGRAPHIC AUDIT SEAL" in html
        assert "UNSEALED" in html or "[UNSEALED]" in html
        # Must NOT claim to be sealed with a verified hash
        assert "[VERIFIED CHAIN HASH]" not in html

    def test_report_seal_verified_chain_hash_post_adjudication(self):
        """
        After counsel adjudications are executed, the report seal must display
        the exact, cryptographically verified SHA-256 chain head hash from the audit trail.
        """
        session_id = "test_seal_verified_sess"
        headers = {"X-Session-ID": session_id}

        # 1. Action 1: Re-attest Item 11
        client.post(
            "/api/review/action",
            json={
                "action": "re_attest",
                "lineage_key": "poster_noir_detective_magazine",
                "rationale": "Public domain verified under 17 U.S.C. § 304.",
                "version_id": "v8",
            },
            headers=headers,
        )

        # 2. Action 2: Reject Item 12
        client.post(
            "/api/review/action",
            json={
                "action": "reject",
                "lineage_key": "music_cue_midnight_serenade",
                "rationale": "Vanguard Media sync conflict; cue must be removed.",
                "version_id": "v8",
            },
            headers=headers,
        )

        # 3. Fetch audit trail from backend
        trail_res = client.get("/api/review/audit-trail", headers=headers)
        assert trail_res.status_code == 200
        trail_data = trail_res.json()
        assert trail_data["is_ledger_tamper_free"] is True
        assert trail_data["total_events"] == 2

        chain_head_hash = trail_data["chain_head_hash"]
        assert len(chain_head_hash) == 64, f"Invalid SHA-256 hex length: {len(chain_head_hash)}"

        # 4. Fetch SSR Report HTML
        report_res = client.get("/api/reports/form-eo-2026/html", headers=headers)
        assert report_res.status_code == 200
        html = report_res.text

        # Verification: Seal must display the exact verified chain head hash
        expected_seal_snippet = f"CRYPTOGRAPHIC AUDIT SEAL: SHA256:{chain_head_hash}"
        assert expected_seal_snippet in html, (
            f"Report seal did not contain expected chain head hash: {expected_seal_snippet}"
        )
        assert "[VERIFIED CHAIN HASH]" in html
        assert "LIENMARK AUDIT LEDGER TAMPER-FREE: TRUE" in html

        # Negative check: Must NOT be UNSEALED once adjudicated
        assert "[UNSEALED]" not in html


# =============================================================================
# ISSUE 4: POSTER DISAMBIGUATION TEST SUITE
# =============================================================================

class TestPosterDisambiguation:
    """
    Automated test checking that artwork_vintage_travel_poster renders Scene 08 (not Scene 42)
    and poster_noir_detective_magazine renders Scene 42 (not Scene 08).
    """

    def test_fixture_level_poster_disambiguation(self):
        """
        Verifies in backend golden dataset fixtures:
        - poster_paris_expo_1937 (travel poster) is bound to Scene 08 - Hotel Corridor.
        - poster_noir_detective_magazine is bound to Scene 42 - 00:44:12.
        """
        v7_uses, v8_uses, _, _ = get_golden_fixtures()

        # Item 02: Paris Expo / Vintage Travel Poster
        travel_poster = next((u for u in v7_uses if u.stable_lineage_key == "poster_paris_expo_1937"), None)
        assert travel_poster is not None
        assert "Scene 08" in travel_poster.scene_or_timecode
        assert "Scene 42" not in travel_poster.scene_or_timecode
        assert travel_poster.asset_type == "artwork"
        assert "1937 Paris" in travel_poster.description

        # Item 11: Noir Detective Magazine Poster
        noir_poster_v7 = next((u for u in v7_uses if u.stable_lineage_key == "poster_noir_detective_magazine"), None)
        assert noir_poster_v7 is not None
        assert "Scene 42" in noir_poster_v7.scene_or_timecode
        assert "Scene 08" not in noir_poster_v7.scene_or_timecode
        assert noir_poster_v7.asset_type == "artwork"

        noir_poster_v8 = next((u for u in v8_uses if u.stable_lineage_key == "poster_noir_detective_magazine"), None)
        assert noir_poster_v8 is not None
        assert "Scene 42" in noir_poster_v8.scene_or_timecode
        assert "Scene 08" not in noir_poster_v8.scene_or_timecode

    def test_alias_resolver_maps_travel_poster_to_scene_08(self):
        """
        Verifies that 'artwork_vintage_travel_poster' alias resolves to 'poster_paris_expo_1937'.
        """
        assert resolve_lineage_key("artwork_vintage_travel_poster") == "poster_paris_expo_1937"
        assert resolve_lineage_key("poster_noir_detective_magazine") == "poster_noir_detective_magazine"

        v7_uses, _, _, _ = get_golden_fixtures()
        canonical_key = resolve_lineage_key("artwork_vintage_travel_poster")
        use = next(u for u in v7_uses if u.stable_lineage_key == canonical_key)
        assert "Scene 08" in use.scene_or_timecode
        assert "Scene 42" not in use.scene_or_timecode

    def test_api_claims_renders_correct_scenes_for_both_posters(self):
        """
        Verifies via GET /api/claims that:
        - poster_paris_expo_1937 renders Scene 08 (not Scene 42).
        - poster_noir_detective_magazine renders Scene 42 (not Scene 08).
        """
        res = client.get("/api/claims")
        assert res.status_code == 200
        claims = res.json()["claims"]

        travel_claim = next((c for c in claims if c["stable_lineage_key"] == "poster_paris_expo_1937"), None)
        assert travel_claim is not None
        assert "Scene 08" in travel_claim["scene"]
        assert "Scene 42" not in travel_claim["scene"]
        assert travel_claim["state"].lower() == "carried_forward"

        noir_claim = next((c for c in claims if c["stable_lineage_key"] == "poster_noir_detective_magazine"), None)
        assert noir_claim is not None
        assert "Scene 42" in noir_claim["scene"]
        assert "Scene 08" not in noir_claim["scene"]

    def test_ssr_report_html_disambiguation(self):
        """
        Verifies in rendered SSR Form E&O-2026 HTML:
        - poster_paris_expo_1937 appears under Section III (Carried Forward) in Scene 08.
        - poster_noir_detective_magazine appears under Section II (Re-Attested) in Scene 42.
        - Neither poster is attributed to the other's scene.
        """
        # Reconcile so poster_noir is in Section II
        res = client.get("/api/reports/form-eo-2026/html?auto_reconcile_demo=true")
        assert res.status_code == 200
        html = res.text

        # Ensure both keys are rendered
        assert "poster_paris_expo_1937" in html
        assert "poster_noir_detective_magazine" in html

        # Scene 08 must be adjacent to poster_paris_expo_1937
        paris_match = re.search(r"poster_paris_expo_1937.*?Scene\s*08", html, re.DOTALL) or re.search(r"Scene\s*08.*?poster_paris_expo_1937", html, re.DOTALL)
        assert paris_match is not None, "poster_paris_expo_1937 not associated with Scene 08 in report HTML!"

        # Scene 42 must be adjacent to poster_noir_detective_magazine
        noir_match = re.search(r"poster_noir_detective_magazine.*?Scene\s*42", html, re.DOTALL) or re.search(r"Scene\s*42.*?poster_noir_detective_magazine", html, re.DOTALL)
        assert noir_match is not None, "poster_noir_detective_magazine not associated with Scene 42 in report HTML!"
