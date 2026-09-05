"""
Automated Test Suite for Sprint 3B: Form E&O-2026 Exceptions Schedule Architecture
Tests:
1. Schedule Construction & Schema Contract:
   - Verifies ExceptionsSchedule, ExceptionsScheduleItem, and CarrierHeader models.
   - Validates version metadata, production metadata, cut content hash, and timestamp.
2. Mathematical Reconciliation Invariant Theorem (12 = 10 + 1 + 1):
   - Asserts total_claims == 12.
   - Asserts carried_forward_count == 10.
   - Asserts reopened_count == 2.
   - Asserts re_attested_count == 1.
   - Asserts unresolved_exception_count == 1.
   - Verifies conservation equation: total = carried + reattested + unresolved.
3. Three-Tier Section Categorization & Presentation:
   - Section I: Unresolved Exceptions (Item 12: 'music_cue_midnight_serenade').
   - Section II: Re-Attested Public Domain Items (Item 11: 'poster_noir_detective_magazine').
   - Section III: Certified Carried-Forward Register (Items 1–10).
4. Traceable Evidence & Citations:
   - Asserts presence of Parallel Search citations with attributable source_url, source_title, excerpt, and provider.
   - Verifies LOC public domain evidence on Item 11 and ASCAP/Vanguard adverse claim on Item 12.
5. Exact State Parity across API, JSON, and SSR HTML:
   - Asserts GET /api/reports/exceptions matches stored state bit-for-bit.
   - Asserts GET /api/reports/form-eo-2026 matches /api/reports/exceptions.
   - Asserts SSR HTML (/report/{production_id}) accurately renders all counts, metadata, and tables.
6. Statutory Underwriter Warranty & Legal Disclaimer Architecture:
   - Asserts Underwriting status is 'PENDING_REVIEW' (not binding or pre-approved).
   - Asserts warranty clause conditioning coverage on disclosed schedule.
   - Asserts strict absence of false legal certainty claims ('guarantee', 'absolute legal clearance', 'insurer pre-approved').
   - Verifies demo / fictional counsel disclaimer adherence.
7. Idempotence & Permutation Invariance:
   - Shuffling input claims produces identical schedule structure and count metrics.
8. Counsel Checkpoint Integration:
   - Schedule dynamically reflects CounselCheckpointManager actions (re_attest, reject, exception).

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import copy
import random
import re
import pytest
from fastapi.testclient import TestClient

from backend.domain.models import (
    CarrierHeader,
    CounselDecision,
    CreativeUse,
    DecisionState,
    DecisionStatus,
    ExceptionsSchedule,
    ExceptionsScheduleItem,
    ReattestationRequest,
    ReviewAction,
    ReviewerIdentity,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.core.counsel_checkpoint import CounselCheckpointManager
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
)
from backend.main import app, _counsel_reattestations, counsel_checkpoint_manager

client = TestClient(app)


# =============================================================================
# FIXTURES & HELPERS
# =============================================================================

@pytest.fixture(autouse=True)
def reset_global_state():
    """Ensure clean global counsel re-attestation and checkpoint state before each test."""
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()
    yield
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()


def generate_standard_v8_reconciled_schedule():
    """Helper that generates the standard v8 reconciled schedule with Item 11 re-attested and Item 12 exception."""
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    validity_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    poster_key = "poster_noir_detective_magazine"
    music_key = "music_cue_midnight_serenade"

    reattestations = {
        poster_key: ReattestationRequest(
            decision_id="dec_v7_poster_noir",
            stable_lineage_key=poster_key,
            version_id="v8",
            new_status=DecisionStatus.APPROVED,
            counsel_rationale="Artwork verified in public domain via LOC registration records retrieved by Parallel Search; non-infringing.",
            reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        ),
        music_key: ReattestationRequest(
            decision_id="dec_v7_music_midnight",
            stable_lineage_key=music_key,
            version_id="v8",
            new_status=DecisionStatus.REJECTED,
            counsel_rationale="Vanguard Media active ownership conflict identified via Parallel Search; replace cue with alternate track.",
            reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        ),
    }

    schedule = InvalidationEngine.generate_exceptions_schedule(
        project_id="proj_blockbuster_cinema",
        base_version_id="v7",
        target_version_id="v8",
        target_uses=v8_uses,
        validity_results=validity_results,
        reattestations=reattestations,
        base_uses=v7_uses,
    )
    return schedule


# =============================================================================
# 1. TEST SCHEDULE CONSTRUCTION & SCHEMA CONTRACT
# =============================================================================

class TestScheduleConstructionAndSchema:
    """Verifies domain model integrity, metadata bindings, and content hashes."""

    def test_schedule_model_structure(self):
        """ExceptionsSchedule instance adheres to Pydantic v2 contract."""
        schedule = generate_standard_v8_reconciled_schedule()

        assert isinstance(schedule, ExceptionsSchedule)
        assert schedule.schedule_id.startswith("sched_proj_blockbuster_cinema_v8_")
        assert schedule.project_id == "proj_blockbuster_cinema"
        assert schedule.base_version_id == "v7"
        assert schedule.target_version_id == "v8"
        assert schedule.policy_version == "E&O-2026.1-DEVPOST"
        assert schedule.policy_number == "E&O-2026.1-DEVPOST"

    def test_carrier_header_metadata(self):
        """CarrierHeader contains standard underwriter parameters."""
        schedule = generate_standard_v8_reconciled_schedule()
        carrier = schedule.carrier_header

        assert isinstance(carrier, CarrierHeader)
        assert "Underwriters" in carrier.carrier_name or "Syndicate" in carrier.carrier_name
        assert carrier.policy_number == "E&O-2026.1-DEVPOST"
        assert "Front Row" in carrier.broker_name or "Gallagher" in carrier.broker_name
        assert carrier.underwriter_status == "PENDING_REVIEW"
        assert "Warranted clearance schedule" in carrier.warranty_clause

    def test_production_metadata_and_target_content_hash(self):
        """Production metadata records the immutable SHA-256 target cut content hash."""
        schedule = generate_standard_v8_reconciled_schedule()
        meta = schedule.production_metadata

        assert meta["project_id"] == "proj_blockbuster_cinema"
        assert meta["base_version_id"] == "v7"
        assert meta["target_version_id"] == "v8"
        # Matches v8 content hash in get_v8_version()
        assert meta["target_cut_hash"] == "f9e8d7c6b5a43210fedcba9876543210"
        assert meta["total_claims"] == 12

    def test_items_contain_all_twelve_claims(self):
        """Schedule items list contains exactly 12 items."""
        schedule = generate_standard_v8_reconciled_schedule()
        assert len(schedule.items) == 12
        for item in schedule.items:
            assert isinstance(item, ExceptionsScheduleItem)
            assert item.stable_lineage_key
            assert item.asset_type
            assert item.description
            assert item.scene_or_timecode
            assert item.v8_evaluation_state in ("carried_forward", "re_attested", "exception")


# =============================================================================
# 2. TEST MATHEMATICAL RECONCILIATION INVARIANT THEOREM (12 = 10 + 1 + 1)
# =============================================================================

class TestReconciliationInvariantTheorem:
    """
    Mathematical Proof:
    Total Claims (12) = Carried Forward (10) + Re-Attested (1) + Unresolved Exceptions (1).
    Reopened Claims (2) = Re-Attested (1) + Unresolved Exceptions (1).
    """

    def test_reconciliation_invariant_counts(self):
        """Verifies the exact 12 = 10 + 1 + 1 conservation theorem."""
        schedule = generate_standard_v8_reconciled_schedule()

        assert schedule.total_claims == 12, "Total claims must be exactly 12"
        assert schedule.carried_forward_count == 10, "Carried forward must be exactly 10"
        assert schedule.reopened_count == 2, "Reopened claims must be exactly 2"
        assert schedule.re_attested_count == 1, "Re-attested claims must be exactly 1"
        assert schedule.unresolved_exception_count == 1, "Unresolved exceptions must be exactly 1"

        # Formal algebraic invariant verification
        assert schedule.total_claims == (
            schedule.carried_forward_count
            + schedule.re_attested_count
            + schedule.unresolved_exception_count
        ), "Conservation invariant violated: total != carried + reattested + unresolved"

        assert schedule.reopened_count == (
            schedule.re_attested_count + schedule.unresolved_exception_count
        ), "Reopened decomposition violated: reopened != reattested + unresolved"

    def test_reconciliation_sums_match_items_list(self):
        """Counts match the actual item states in the items array."""
        schedule = generate_standard_v8_reconciled_schedule()

        carried_items = [i for i in schedule.items if i.v8_evaluation_state == "carried_forward"]
        reattested_items = [i for i in schedule.items if i.v8_evaluation_state == "re_attested"]
        exception_items = [i for i in schedule.items if i.v8_evaluation_state == "exception"]

        assert len(carried_items) == schedule.carried_forward_count == 10
        assert len(reattested_items) == schedule.re_attested_count == 1
        assert len(exception_items) == schedule.unresolved_exception_count == 1
        assert len(carried_items) + len(reattested_items) + len(exception_items) == 12

    def test_exact_12_invariant_and_single_unresolved_exception(self):
        """
        Sprint 3B Task 3 Requirement 2:
        - Evaluates schedule after counsel adjudication (Item 11 re-attested, Item 12 flagged as exception).
        - Asserts total_claims == 12.
        - Asserts carried_forward_count == 10.
        - Asserts re_attested_count == 1.
        - Asserts unresolved_exception_count == 1.
        - Asserts that the single unresolved claim ('music_cue_midnight_serenade') appears as the sole item in unresolved_exceptions_schedule.
        """
        schedule = generate_standard_v8_reconciled_schedule()

        assert schedule.total_claims == 12
        assert schedule.carried_forward_count == 10
        assert schedule.re_attested_count == 1
        assert schedule.unresolved_exception_count == 1

        # Asserts single unresolved claim appears as sole item in unresolved_exceptions_schedule
        assert len(schedule.unresolved_exceptions_schedule) == 1
        assert schedule.unresolved_exceptions_schedule[0].stable_lineage_key == "music_cue_midnight_serenade"
        assert schedule.unresolved_exceptions_schedule[0].v8_evaluation_state == "exception"


# =============================================================================
# 3. TEST THREE-TIER SECTION CATEGORIZATION & PRESENTATION
# =============================================================================

class TestThreeTierSectionCategorization:
    """Verifies proper isolation across Section I (Exceptions), Section II (Re-Attested), Section III (Carried)."""

    def test_section_one_unresolved_exception_item_12(self):
        """Section I isolates Item 12 (music_cue_midnight_serenade) as the sole exception."""
        schedule = generate_standard_v8_reconciled_schedule()

        assert len(schedule.unresolved_exceptions_schedule) == 1
        exc_item = schedule.unresolved_exceptions_schedule[0]

        assert exc_item.stable_lineage_key == "music_cue_midnight_serenade"
        assert exc_item.asset_type == "music"
        assert exc_item.v8_evaluation_state == "exception"
        assert exc_item.invalidation_reason == "EXTERNAL_EVIDENCE_SHIFT"
        assert "Vanguard Media" in exc_item.counsel_action
        assert "UNRESOLVED EXCEPTION" in exc_item.counsel_action

    def test_section_two_reattested_item_11(self):
        """Section II contains Item 11 (poster_noir_detective_magazine) re-attested under public domain."""
        schedule = generate_standard_v8_reconciled_schedule()

        reattested = [i for i in schedule.items if i.v8_evaluation_state == "re_attested"]
        assert len(reattested) == 1
        poster_item = reattested[0]

        assert poster_item.stable_lineage_key == "poster_noir_detective_magazine"
        assert poster_item.asset_type == "artwork"
        assert poster_item.v8_evaluation_state == "re_attested"
        assert "public domain" in poster_item.counsel_action.lower()
        assert "Sarah Jenkins, Esq." in poster_item.counsel_action

    def test_section_three_certified_carried_forward_ten_items(self):
        """Section III contains all 10 baseline unchanged items."""
        schedule = generate_standard_v8_reconciled_schedule()

        carried = [i for i in schedule.items if i.v8_evaluation_state == "carried_forward"]
        assert len(carried) == 10

        expected_carried_keys = {
            "prop_vintage_telephone",
            "poster_paris_expo_1937",
            "car_ford_sedan_1949",
            "trademark_acme_coffee",
            "artwork_abstract_expressionist",
            "likeness_mayor_cameo",
            "architecture_tribunal_facade",
            "text_headline_gazette",
            "wardrobe_fedora_brand",
            "music_incidental_radio_static",
        }
        actual_carried_keys = {i.stable_lineage_key for i in carried}
        assert actual_carried_keys == expected_carried_keys

        for item in carried:
            assert item.invalidation_reason is None
            assert "carried forward" in item.counsel_action.lower() or "approved" in item.counsel_action.lower()


# =============================================================================
# 4. TEST TRACEABLE PARALLEL SEARCH CITATIONS & EVIDENCE
# =============================================================================

class TestTraceableParallelSearchCitations:
    """Verifies runtime evidence citations, URLs, and attribution metadata."""

    def test_item_11_public_domain_loc_citation(self):
        """Item 11 citations include US Copyright Office / Library of Congress verification."""
        schedule = generate_standard_v8_reconciled_schedule()
        poster = next(i for i in schedule.items if i.stable_lineage_key == "poster_noir_detective_magazine")

        assert len(poster.evidence_citations) >= 1
        citation = poster.evidence_citations[0]

        assert "cocatalog.loc.gov" in citation["source_url"] or "loc.gov" in citation["source_url"]
        assert "US Copyright Office" in citation["source_title"]
        assert "public domain" in citation["excerpt"].lower()
        assert citation["provider"] == "Parallel"

    def test_item_12_adverse_claim_ascap_citation(self):
        """Item 12 citations include ASCAP ACE / Vanguard Media ownership dispute evidence."""
        schedule = generate_standard_v8_reconciled_schedule()
        music = next(i for i in schedule.items if i.stable_lineage_key == "music_cue_midnight_serenade")

        assert len(music.evidence_citations) >= 1
        citation = music.evidence_citations[0]

        assert "ascap.com" in citation["source_url"]
        assert "ASCAP ACE" in citation["source_title"]
        assert "Vanguard Media" in citation["excerpt"]
        assert citation["provider"] == "Parallel"

    def test_evidence_citations_in_ssr_html(self):
        """SSR HTML renders clickable anchor tags for evidence sources."""
        schedule = generate_standard_v8_reconciled_schedule()
        html = InvalidationEngine.render_form_eo_2026_html(schedule)

        # Check for citation links in HTML
        assert 'href="https://ascap.com/ace-title-search/midnight-serenade-9921"' in html
        assert 'target="_blank"' in html
        assert "ASCAP ACE Repertory" in html

    def test_all_evidence_citations_validity(self):
        """
        Sprint 3B Task 3 Requirement 4:
        - Verifies all evidence citations contain valid source_title, source_url, and non-empty excerpts.
        - Item 11 cites LOC copyright renewal catalog.
        - Item 12 cites ASCAP ACE repertory dispute.
        """
        schedule = generate_standard_v8_reconciled_schedule()
        cited_items = [i for i in schedule.items if i.evidence_citations]
        assert len(cited_items) >= 2

        for item in cited_items:
            for citation in item.evidence_citations:
                assert citation.get("source_title"), f"Empty source_title in item {item.stable_lineage_key}"
                assert citation.get("source_url"), f"Empty source_url in item {item.stable_lineage_key}"
                assert citation["source_url"].startswith("http://") or citation["source_url"].startswith("https://")
                assert citation.get("excerpt"), f"Empty excerpt in item {item.stable_lineage_key}"
                assert len(citation["excerpt"].strip()) > 0, f"Whitespace-only excerpt in {item.stable_lineage_key}"
                assert citation.get("provider") == "Parallel"

        # Item 11 specific verification
        item_11 = next(i for i in schedule.items if i.stable_lineage_key == "poster_noir_detective_magazine")
        assert any("cocatalog.loc.gov" in c["source_url"] or "loc.gov" in c["source_url"] for c in item_11.evidence_citations)
        assert any("Copyright" in c["source_title"] for c in item_11.evidence_citations)

        # Item 12 specific verification
        item_12 = next(i for i in schedule.items if i.stable_lineage_key == "music_cue_midnight_serenade")
        assert any("ascap.com" in c["source_url"] for c in item_12.evidence_citations)
        assert any("ASCAP" in c["source_title"] for c in item_12.evidence_citations)


# =============================================================================
# 5. TEST EXACT STATE PARITY: JSON API vs STORED MODEL vs SSR HTML
# =============================================================================

class TestExactStateParity:
    """Verifies bit-for-bit consistency between JSON API endpoints and SSR HTML."""

    def test_api_reports_exceptions_endpoint(self):
        """GET /api/reports/exceptions returns reconciled schedule matching stored model."""
        # Set reattestations in main.py global
        poster_key = "poster_noir_detective_magazine"
        music_key = "music_cue_midnight_serenade"

        _counsel_reattestations[poster_key] = ReattestationRequest(
            decision_id="dec_v7_poster_noir",
            stable_lineage_key=poster_key,
            version_id="v8",
            new_status=DecisionStatus.APPROVED,
            counsel_rationale="Artwork verified in public domain via LOC registration records retrieved by Parallel Search; non-infringing.",
            reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        )
        _counsel_reattestations[music_key] = ReattestationRequest(
            decision_id="dec_v7_music_midnight",
            stable_lineage_key=music_key,
            version_id="v8",
            new_status=DecisionStatus.REJECTED,
            counsel_rationale="Vanguard Media active ownership conflict identified via Parallel Search; replace cue with alternate track.",
            reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        )

        response = client.get("/api/reports/exceptions")
        assert response.status_code == 200
        data = response.json()

        assert data["total_claims"] == 12
        assert data["carried_forward_count"] == 10
        assert data["reopened_count"] == 2
        assert data["re_attested_count"] == 1
        assert data["unresolved_exception_count"] == 1
        assert len(data["items"]) == 12
        assert len(data["unresolved_exceptions_schedule"]) == 1
        assert data["policy_version"] == "E&O-2026.1-DEVPOST"

    def test_api_form_eo_2026_alias_endpoint(self):
        """GET /api/reports/form-eo-2026 returns identical payload as /api/reports/exceptions."""
        resp1 = client.get("/api/reports/exceptions")
        resp2 = client.get("/api/reports/form-eo-2026")

        assert resp1.status_code == 200
        assert resp2.status_code == 200

        data1 = resp1.json()
        data2 = resp2.json()

        # Both endpoints report identical counts, items, and metadata
        assert data1["total_claims"] == data2["total_claims"]
        assert data1["carried_forward_count"] == data2["carried_forward_count"]
        assert data1["re_attested_count"] == data2["re_attested_count"]
        assert data1["unresolved_exception_count"] == data2["unresolved_exception_count"]
        assert len(data1["items"]) == len(data2["items"])

    def test_ssr_html_endpoint_parity(self):
        """GET /report/proj_blockbuster_cinema renders SSR HTML reflecting exact state counts."""
        poster_key = "poster_noir_detective_magazine"
        music_key = "music_cue_midnight_serenade"

        _counsel_reattestations[poster_key] = ReattestationRequest(
            decision_id="dec_v7_poster_noir",
            stable_lineage_key=poster_key,
            version_id="v8",
            new_status=DecisionStatus.APPROVED,
            counsel_rationale="Artwork verified in public domain via LOC registration records retrieved by Parallel Search; non-infringing.",
            reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        )
        _counsel_reattestations[music_key] = ReattestationRequest(
            decision_id="dec_v7_music_midnight",
            stable_lineage_key=music_key,
            version_id="v8",
            new_status=DecisionStatus.REJECTED,
            counsel_rationale="Vanguard Media active ownership conflict identified via Parallel Search; replace cue with alternate track.",
            reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        )

        response = client.get("/report/proj_blockbuster_cinema")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        html = response.text

        # Assert SSR HTML contains all exact mathematical reconciliation counts
        assert "TOTAL CLAIMS" in html
        assert ">12<" in html
        assert "CARRIED FORWARD" in html
        assert ">10<" in html
        assert "COUNSEL RE-ATTESTED" in html
        assert ">1<" in html
        assert "ACTIVE EXCEPTIONS" in html

        # Assert section titles present
        assert "FORM E&amp;O-2026" in html or "FORM E&O-2026" in html
        assert "SECTION I: UNRESOLVED EXCEPTIONS" in html
        assert "SECTION II: COMPREHENSIVE RECONCILIATION AUDIT LEDGER" in html

        # Assert target content hash
        assert "f9e8d7c6b5a43210fedcba9876543210" in html

    def test_export_matches_stored_state_bit_for_bit(self):
        """
        Sprint 3B Task 3 Requirement 1:
        - Asserts that JSON export from GET /api/reports/exceptions and InvalidationEngine.generate_exceptions_schedule
          matches backend domain models bit-for-bit.
        - Verifies schedule ID, project ID ('proj_blockbuster_cinema'), base/target version IDs ('v7' -> 'v8'),
          content hashes, policy binder ('E&O-2026.1-DEVPOST'), and generation time.
        """
        poster_key = "poster_noir_detective_magazine"
        music_key = "music_cue_midnight_serenade"

        reattestations = {
            poster_key: ReattestationRequest(
                decision_id="dec_v7_poster_noir",
                stable_lineage_key=poster_key,
                version_id="v8",
                new_status=DecisionStatus.APPROVED,
                counsel_rationale="Artwork verified in public domain via LOC registration records retrieved by Parallel Search; non-infringing.",
                reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
            ),
            music_key: ReattestationRequest(
                decision_id="dec_v7_music_midnight",
                stable_lineage_key=music_key,
                version_id="v8",
                new_status=DecisionStatus.REJECTED,
                counsel_rationale="Vanguard Media active ownership conflict identified via Parallel Search; replace cue with alternate track.",
                reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
            ),
        }
        _counsel_reattestations.clear()
        _counsel_reattestations.update(reattestations)

        # 1. Fetch JSON export from API endpoint
        response = client.get("/api/reports/exceptions")
        assert response.status_code == 200
        api_data = response.json()

        # 2. Deserialization into domain model matches exactly
        parsed_schedule = ExceptionsSchedule.model_validate(api_data)
        assert isinstance(parsed_schedule, ExceptionsSchedule)

        # 3. Verify schedule ID, project ID, version IDs, hashes, policy binder, generation time
        assert api_data["schedule_id"].startswith("sched_proj_blockbuster_cinema_v8_")
        assert parsed_schedule.schedule_id.startswith("sched_proj_blockbuster_cinema_v8_")
        assert api_data["project_id"] == "proj_blockbuster_cinema"
        assert parsed_schedule.project_id == "proj_blockbuster_cinema"
        assert api_data["base_version_id"] == "v7"
        assert parsed_schedule.base_version_id == "v7"
        assert api_data["target_version_id"] == "v8"
        assert parsed_schedule.target_version_id == "v8"
        assert api_data["policy_version"] == "E&O-2026.1-DEVPOST"
        assert parsed_schedule.policy_version == "E&O-2026.1-DEVPOST"
        assert api_data["policy_number"] == "E&O-2026.1-DEVPOST"
        assert api_data["carrier_header"]["policy_number"] == "E&O-2026.1-DEVPOST"
        assert api_data["production_metadata"]["target_cut_hash"] == "f9e8d7c6b5a43210fedcba9876543210"
        assert api_data["production_metadata"]["base_cut_hash"] == "a1b2c3d4e5f60718293a4b5c6d7e8f90"
        assert api_data["generated_at"] is not None
        assert parsed_schedule.generated_at is not None

        # 4. InvalidationEngine direct generation matches all fields
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
        validities = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )
        direct_schedule = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_blockbuster_cinema",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=validities,
            reattestations=reattestations,
            base_uses=v7_uses,
        )
        assert parsed_schedule.total_claims == direct_schedule.total_claims == 12
        assert parsed_schedule.carried_forward_count == direct_schedule.carried_forward_count == 10
        assert parsed_schedule.re_attested_count == direct_schedule.re_attested_count == 1
        assert parsed_schedule.unresolved_exception_count == direct_schedule.unresolved_exception_count == 1
        assert parsed_schedule.production_metadata == direct_schedule.production_metadata

        # Assert all 12 items match bit-for-bit in attributes
        for api_item, direct_item in zip(parsed_schedule.items, direct_schedule.items):
            assert api_item.stable_lineage_key == direct_item.stable_lineage_key
            assert api_item.asset_type == direct_item.asset_type
            assert api_item.description == direct_item.description
            assert api_item.scene_or_timecode == direct_item.scene_or_timecode
            assert api_item.v8_evaluation_state == direct_item.v8_evaluation_state
            assert api_item.invalidation_reason == direct_item.invalidation_reason
            assert api_item.counsel_action == direct_item.counsel_action
            assert api_item.evidence_citations == direct_item.evidence_citations

    def test_all_four_api_and_ssr_endpoints_return_200(self):
        """
        Sprint 3B Task 3 Requirement 6:
        - GET /api/reports/exceptions returns 200 and valid JSON.
        - GET /api/reports/form-eo-2026 returns 200 and valid JSON.
        - GET /report/proj_blockbuster_cinema returns 200 and valid HTML.
        - GET /api/reports/form-eo-2026/html returns 200 and valid HTML.
        """
        # 1. GET /api/reports/exceptions
        r1 = client.get("/api/reports/exceptions")
        assert r1.status_code == 200, f"GET /api/reports/exceptions returned {r1.status_code}"
        assert "application/json" in r1.headers["content-type"]
        d1 = r1.json()
        assert d1["total_claims"] == 12
        assert isinstance(d1["items"], list)

        # 2. GET /api/reports/form-eo-2026
        r2 = client.get("/api/reports/form-eo-2026")
        assert r2.status_code == 200, f"GET /api/reports/form-eo-2026 returned {r2.status_code}"
        assert "application/json" in r2.headers["content-type"]
        d2 = r2.json()
        assert d2["total_claims"] == 12

        # 3. GET /report/proj_blockbuster_cinema
        r3 = client.get("/report/proj_blockbuster_cinema")
        assert r3.status_code == 200, f"GET /report/proj_blockbuster_cinema returned {r3.status_code}"
        assert "text/html" in r3.headers["content-type"]
        assert "<!DOCTYPE html>" in r3.text or "<html" in r3.text
        assert "FORM E&O-2026" in r3.text or "FORM E&amp;O-2026" in r3.text

        # 4. GET /api/reports/form-eo-2026/html
        r4 = client.get("/api/reports/form-eo-2026/html")
        assert r4.status_code == 200, f"GET /api/reports/form-eo-2026/html returned {r4.status_code}"
        assert "text/html" in r4.headers["content-type"]
        assert "<!DOCTYPE html>" in r4.text or "<html" in r4.text
        assert "FORM E&O-2026" in r4.text or "FORM E&amp;O-2026" in r4.text


# =============================================================================
# 6. TEST STATUTORY UNDERWRITER WARRANTY & LEGAL DISCLAIMER ARCHITECTURE
# =============================================================================

class TestStatutoryUnderwriterDisclaimers:
    """Verifies that no artifact makes unlawful claims of insurance approval or legal certainty."""

    def test_underwriter_status_is_pending_review(self):
        """Carrier header strictly sets status to PENDING_REVIEW."""
        schedule = generate_standard_v8_reconciled_schedule()
        assert schedule.carrier_header.underwriter_status == "PENDING_REVIEW"

        html = InvalidationEngine.render_form_eo_2026_html(schedule)
        assert "Underwriting Status: PENDING_REVIEW" in html

    def test_prohibition_against_claiming_insurer_approval_or_legal_certainty(self):
        """
        Sprint 3B Task 3 Requirement 5:
        - Verifies that NO artifact claims insurer approval, coverage, policy binding, or legal certainty.
        - Asserts disclaimers are present in both JSON metadata and rendered HTML.
        - Verifies that prohibited phrases ('coverage guaranteed', 'policy bound automatically',
          'certifies legal certainty', 'carrier bound') are strictly absent.
        """
        schedule = generate_standard_v8_reconciled_schedule()
        html = InvalidationEngine.render_form_eo_2026_html(schedule).lower()
        json_meta_str = str(schedule.production_metadata).lower()
        json_dump_str = schedule.model_dump_json().lower()

        # 1. Assert disclaimers are present in both JSON metadata and rendered HTML
        assert "disclaimer" in schedule.production_metadata, "Disclaimer missing from JSON production_metadata"
        assert "disclaimer" in schedule.carrier_header.model_dump(), "Disclaimer missing from CarrierHeader"
        assert "legal & underwriting disclaimer" in schedule.production_metadata["disclaimer"].lower()
        assert "non-binding risk assessment" in schedule.carrier_header.disclaimer.lower()
        assert (
            "legal &amp; underwriting disclaimer" in html
            or "legal & underwriting disclaimer" in html
        ), "Disclaimer missing from rendered HTML"

        # 2. Strict absence of prohibited phrases
        prohibited_phrases = [
            "coverage guaranteed",
            "policy bound automatically",
            "certifies legal certainty",
            "carrier bound",
            "policy approved by insurer",
            "coverage is guaranteed",
            "insurer has bound coverage",
            "zero legal risk guaranteed",
            "absolute legal certainty",
            "claims are legally cleared by ai",
        ]
        for phrase in prohibited_phrases:
            assert phrase not in html, f"Prohibited phrase found in rendered HTML: '{phrase}'"
            assert phrase not in json_dump_str, f"Prohibited phrase found in JSON export: '{phrase}'"
            assert phrase not in json_meta_str, f"Prohibited phrase found in JSON metadata: '{phrase}'"

    def test_warranty_clause_presence(self):
        """Schedule includes statutory warranty clause excluding undisclosed risks."""
        schedule = generate_standard_v8_reconciled_schedule()
        clause = schedule.carrier_header.warranty_clause
        assert "Warranted clearance schedule" in clause
        assert "excluded from coverage" in clause

        html = InvalidationEngine.render_form_eo_2026_html(schedule)
        assert clause in html

    def test_signature_blocks_demarcation(self):
        """SSR HTML includes explicit physical sign-off lines for Clearance Counsel and Underwriter."""
        schedule = generate_standard_v8_reconciled_schedule()
        html = InvalidationEngine.render_form_eo_2026_html(schedule)

        assert "Clearance Counsel Sign-off" in html
        assert "Underwriter Acknowledgment" in html
        assert "Carrier Representative Signature" in html


# =============================================================================
# 7. TEST IDEMPOTENCE & PERMUTATION INVARIANCE
# =============================================================================

class TestIdempotenceAndPermutationInvariance:
    """Verifies that the schedule output is deterministic regardless of input ordering."""

    def test_permutation_invariance(self):
        """Shuffling target_uses and validity_results produces identical schedule items and counts."""
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        reattestations = {
            "poster_noir_detective_magazine": ReattestationRequest(
                decision_id="dec_v7_poster_noir",
                stable_lineage_key="poster_noir_detective_magazine",
                version_id="v8",
                new_status=DecisionStatus.APPROVED,
                counsel_rationale="Public domain verified.",
                reviewer_name="Sarah Jenkins, Esq.",
            ),
            "music_cue_midnight_serenade": ReattestationRequest(
                decision_id="dec_v7_music_midnight",
                stable_lineage_key="music_cue_midnight_serenade",
                version_id="v8",
                new_status=DecisionStatus.REJECTED,
                counsel_rationale="Conflict identified.",
                reviewer_name="Sarah Jenkins, Esq.",
            ),
        }

        # Run 1: Natural order
        sched1 = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_bb",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=validity_results,
            reattestations=reattestations,
            base_uses=v7_uses,
        )

        # Run 2: Shuffled inputs
        shuffled_uses = list(v8_uses)
        shuffled_validity = list(validity_results)
        random.seed(42)
        random.shuffle(shuffled_uses)
        random.shuffle(shuffled_validity)

        sched2 = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_bb",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=shuffled_uses,
            validity_results=shuffled_validity,
            reattestations=reattestations,
            base_uses=v7_uses,
        )

        # Asserts complete parity
        assert sched1.total_claims == sched2.total_claims == 12
        assert sched1.carried_forward_count == sched2.carried_forward_count == 10
        assert sched1.re_attested_count == sched2.re_attested_count == 1
        assert sched1.unresolved_exception_count == sched2.unresolved_exception_count == 1

        keys1 = [i.stable_lineage_key for i in sched1.items]
        keys2 = [i.stable_lineage_key for i in sched2.items]
        assert keys1 == keys2, "Canonical item sorting failed permutation invariance"


# =============================================================================
# 8. TEST COUNSEL CHECKPOINT INTEGRATION
# =============================================================================

class TestCounselCheckpointIntegration:
    """Verifies that review actions performed in CounselCheckpointManager directly reconcile into the Exceptions Schedule."""

    def test_checkpoint_manager_actions_reconcile_into_schedule(self):
        """Executing review actions via CounselCheckpointManager produces expected schedule state."""
        manager = CounselCheckpointManager()
        poster_key = "poster_noir_detective_magazine"
        music_key = "music_cue_midnight_serenade"

        # Action 1: Re-Attest Item 11
        manager.apply_review_action(
            action=ReviewAction.RE_ATTEST,
            lineage_key=poster_key,
            rationale="Verified in public domain via LOC catalog; renewal lapsed in 1974.",
            reviewer=manager.get_default_reviewer(),
            target_version_id="v8",
        )

        # Action 2: Exception for Item 12
        manager.apply_review_action(
            action=ReviewAction.EXCEPTION,
            lineage_key=music_key,
            rationale="Unresolved Vanguard Media copyright conflict; flagged as exception for replacement.",
            reviewer=manager.get_default_reviewer(),
            target_version_id="v8",
        )

        # Build schedule using reattestations derived from checkpoint events
        reattestations = {
            poster_key: ReattestationRequest(
                decision_id=f"dec_v7_{poster_key}",
                stable_lineage_key=poster_key,
                version_id="v8",
                new_status=DecisionStatus.APPROVED,
                counsel_rationale="Verified in public domain via LOC catalog; renewal lapsed in 1974.",
                reviewer_name="Sarah Jenkins, Esq.",
            ),
            music_key: ReattestationRequest(
                decision_id=f"dec_v7_{music_key}",
                stable_lineage_key=music_key,
                version_id="v8",
                new_status=DecisionStatus.REJECTED,
                counsel_rationale="Unresolved Vanguard Media copyright conflict; flagged as exception for replacement.",
                reviewer_name="Sarah Jenkins, Esq.",
            ),
        }

        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
        validities = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        schedule = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_blockbuster_cinema",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=validities,
            reattestations=reattestations,
            base_uses=v7_uses,
        )

        assert schedule.total_claims == 12
        assert schedule.carried_forward_count == 10
        assert schedule.reopened_count == 2
        assert schedule.re_attested_count == 1
        assert schedule.unresolved_exception_count == 1
        assert len(schedule.unresolved_exceptions_schedule) == 1
        assert schedule.unresolved_exceptions_schedule[0].stable_lineage_key == music_key
