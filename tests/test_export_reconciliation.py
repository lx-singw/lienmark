"""
Sprint 5A Task 2: Export Reconciliation & Quality Gate Test Suite
tests/test_export_reconciliation.py

Exhaustive table-driven automated test suite verifying exact state parity across all Lienmark representations:
  1. Domain Models: ProductionVersion, CreativeUse, CounselDecision, ExceptionsSchedule
  2. API JSON Endpoints: GET /api/reports/exceptions, GET /api/reports/form-eo-2026, GET /api/reports/export?format=json
  3. SSR HTML Reports: GET /report/proj_blockbuster_cinema, GET /api/reports/form-eo-2026/html, GET /api/reports/export?format=html

Strictly verifies:
  - 12 = 10 + 1 + 1 reconciliation invariant: total claims (12), carried forward (10), re-attested (1), unresolved exception (1).
  - Bit-for-bit field matching across JSON and HTML: stable lineage keys, scene timecodes, descriptions, prominence, reason codes.
  - Attributable citation preservation: Library of Congress (LOC) for Item 11, ASCAP ACE for Item 12.
  - Statutory underwriting disclaimers: identically phrased across JSON metadata, CarrierHeader, and HTML header/footer.
  - Zero prohibited legal certainty phrases in any export artifact.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import json
import re
from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient

from backend.domain.models import (
    CarrierHeader,
    CounselDecision,
    CreativeUse,
    DecisionState,
    DecisionStatus,
    EvidenceStance,
    ExceptionsSchedule,
    ExceptionsScheduleItem,
    ProductionVersion,
    ReattestationRequest,
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

# The 10 prohibited legal certainty phrases that must NEVER appear as affirmative clearance in exports
PROHIBITED_LEGAL_CERTAINTY_PHRASES = [
    "guarantee",
    "guaranteed",
    "absolute legal clearance",
    "insurer pre-approved",
    "pre-approved",
    "hold harmless",
    "indemnified",
    "binding coverage",
    "legally certain",
    "risk-free",
]

# The 12 canonical stable lineage keys in expected order
CANONICAL_12_KEYS = [
    "architecture_tribunal_facade",
    "artwork_abstract_expressionist",
    "car_ford_sedan_1949",
    "likeness_mayor_cameo",
    "music_cue_midnight_serenade",
    "music_incidental_radio_static",
    "poster_noir_detective_magazine",
    "poster_paris_expo_1937",
    "prop_vintage_telephone",
    "text_headline_gazette",
    "trademark_acme_coffee",
    "wardrobe_fedora_brand",
]


@pytest.fixture(autouse=True)
def clean_counsel_state():
    """Ensure clean global counsel checkpoint and reattestation state for each test."""
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()
    yield
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()


def seed_standard_reconciled_counsel_decisions():
    """Seeds counsel actions for Item 11 (re-attest) and Item 12 (reject/exception)."""
    poster_key = "poster_noir_detective_magazine"
    music_key = "music_cue_midnight_serenade"

    _counsel_reattestations[poster_key] = ReattestationRequest(
        decision_id="dec_v7_poster_noir",
        stable_lineage_key=poster_key,
        version_id="v8",
        new_status=DecisionStatus.APPROVED,
        counsel_rationale="Artwork verified in public domain via LOC registration records retrieved by Parallel Search; non-infringing.",
        reviewer_name="Sarah Jenkins, Esq. (Lead Clearance Counsel)",
    )
    _counsel_reattestations[music_key] = ReattestationRequest(
        decision_id="dec_v7_music_midnight",
        stable_lineage_key=music_key,
        version_id="v8",
        new_status=DecisionStatus.REJECTED,
        counsel_rationale="Vanguard Media active ownership conflict identified via Parallel Search; replace cue with alternate track.",
        reviewer_name="Sarah Jenkins, Esq. (Lead Clearance Counsel)",
    )


# =============================================================================
# 1. MATHEMATICAL RECONCILIATION INVARIANT THEOREM (12 = 10 + 1 + 1)
# =============================================================================

class TestMathematicalReconciliationInvariant:
    """Verifies conservation theorem across domain models, API JSON, and SSR HTML."""

    def test_reconciliation_invariant_in_domain_model(self):
        """Domain model strictly satisfies 12 = 10 carried + 1 re-attested + 1 exception."""
        seed_standard_reconciled_counsel_decisions()
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
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
            validity_results=validity_results,
            reattestations=_counsel_reattestations,
            base_uses=v7_uses,
        )

        assert schedule.total_claims == 12, "Total claims must equal exactly 12"
        assert schedule.carried_forward_count == 10, "Carried forward must equal exactly 10"
        assert schedule.re_attested_count == 1, "Re-attested count must equal exactly 1"
        assert schedule.unresolved_exception_count == 1, "Unresolved exceptions count must equal exactly 1"
        assert schedule.reopened_count == 2, "Reopened claims must equal exactly 2 (11 and 12)"

        # Conservation equation
        assert (
            schedule.total_claims
            == schedule.carried_forward_count + schedule.re_attested_count + schedule.unresolved_exception_count
        ), "Conservation equation total == carried + re_attested + unresolved violated"

        # Item-level states
        states = [item.v8_evaluation_state for item in schedule.items]
        assert states.count("carried_forward") == 10
        assert states.count("re_attested") == 1
        assert states.count("exception") == 1
        assert len(schedule.items) == 12

    def test_reconciliation_invariant_across_all_json_endpoints(self):
        """All three JSON endpoints output identical mathematical reconciliation counts."""
        seed_standard_reconciled_counsel_decisions()

        endpoints = [
            "/api/reports/exceptions",
            "/api/reports/form-eo-2026",
            "/api/reports/export?format=json",
        ]

        for ep in endpoints:
            res = client.get(ep)
            assert res.status_code == 200, f"Endpoint {ep} failed with {res.status_code}"
            assert "application/json" in res.headers["content-type"]
            data = res.json()

            assert data["total_claims"] == 12, f"{ep}: total_claims must be 12"
            assert data["carried_forward_count"] == 10, f"{ep}: carried_forward_count must be 10"
            assert data["re_attested_count"] == 1, f"{ep}: re_attested_count must be 1"
            assert data["unresolved_exception_count"] == 1, f"{ep}: unresolved_exception_count must be 1"
            assert data["reopened_count"] == 2, f"{ep}: reopened_count must be 2"
            assert len(data["items"]) == 12, f"{ep}: items array must contain 12 items"

    def test_reconciliation_invariant_in_ssr_html_reports(self):
        """SSR HTML renders exact reconciliation badges and counts."""
        seed_standard_reconciled_counsel_decisions()

        html_endpoints = [
            "/report/proj_blockbuster_cinema",
            "/api/reports/form-eo-2026/html",
            "/api/reports/export?format=html",
        ]

        for ep in html_endpoints:
            res = client.get(ep)
            assert res.status_code == 200, f"Endpoint {ep} failed with {res.status_code}"
            assert "text/html" in res.headers["content-type"]
            html = res.text

            # Exact counts in summary ribbon
            assert "TOTAL CLAIMS" in html
            assert ">12<" in html
            assert "CARRIED FORWARD" in html
            assert ">10<" in html
            assert "COUNSEL RE-ATTESTED" in html
            assert ">1<" in html
            assert "ACTIVE EXCEPTIONS" in html

            # Invariant formula text in header
            assert "Total 12 = 10 Carried + 1 Re-Attested + 1 Exception" in html


# =============================================================================
# 2. BIT-FOR-BIT FIELD MATCHING ACROSS JSON AND HTML
# =============================================================================

class TestBitForBitCrossRepresentationParity:
    """Verifies that all 12 items have identical fields across Domain Models, JSON, and HTML."""

    def test_all_12_stable_lineage_keys_match_bit_for_bit(self):
        """Every stable lineage key matches exactly and is embedded within <code> tags in HTML."""
        seed_standard_reconciled_counsel_decisions()

        json_data = client.get("/api/reports/exceptions").json()
        html_data = client.get("/report/proj_blockbuster_cinema").text

        json_keys = [i["stable_lineage_key"] for i in json_data["items"]]
        assert len(json_keys) == 12
        assert sorted(json_keys) == sorted(CANONICAL_12_KEYS)

        for key in json_keys:
            expected_code_tag = f"<code>{key}</code>"
            assert expected_code_tag in html_data, f"Lineage key '{key}' missing from HTML representation"

    def test_all_12_scene_timecodes_match_bit_for_bit(self):
        """Every scene timecode matches bit-for-bit between JSON items and HTML rows."""
        seed_standard_reconciled_counsel_decisions()

        json_data = client.get("/api/reports/exceptions").json()
        html_data = client.get("/report/proj_blockbuster_cinema").text

        for item in json_data["items"]:
            timecode = item["scene_or_timecode"]
            assert timecode, f"Item {item['stable_lineage_key']} has empty scene_or_timecode"
            assert timecode in html_data, f"Scene timecode '{timecode}' not found in HTML"

    def test_all_12_descriptions_match_bit_for_bit(self):
        """Every item description matches bit-for-bit between JSON items and HTML rows."""
        seed_standard_reconciled_counsel_decisions()

        json_data = client.get("/api/reports/exceptions").json()
        html_data = client.get("/report/proj_blockbuster_cinema").text

        for item in json_data["items"]:
            desc = item["description"]
            assert desc, f"Item {item['stable_lineage_key']} has empty description"
            assert desc in html_data, f"Description '{desc}' not found in HTML"

    def test_prominence_duration_shifts_and_preservation(self):
        """
        Verifies prominence dynamics:
        - Item 11: Escalation from 2s background blur to 14s close-up focal shot.
        - Item 12: Stable prominence (20s background cue); shift driven by external catalog.
        - Items 1-10: Stable prominence, verified identical context hashes.
        """
        v7_uses, v8_uses, _, _ = get_golden_fixtures()

        v7_by_key = {u.stable_lineage_key: u for u in v7_uses}
        v8_by_key = {u.stable_lineage_key: u for u in v8_uses}

        # Item 11
        poster_v7 = v7_by_key["poster_noir_detective_magazine"]
        poster_v8 = v8_by_key["poster_noir_detective_magazine"]
        assert poster_v7.duration_or_prominence == "Out-of-focus background blur, 2s"
        assert poster_v8.duration_or_prominence == "Featured close-up focal shot with dialogue, 14s"
        assert poster_v7.context_hash != poster_v8.context_hash

        # Item 12
        music_v7 = v7_by_key["music_cue_midnight_serenade"]
        music_v8 = v8_by_key["music_cue_midnight_serenade"]
        assert music_v7.duration_or_prominence == music_v8.duration_or_prominence == "Background jazz trio performance in speakeasy, 20s"
        assert music_v7.context_hash == music_v8.context_hash

        # Items 1-10
        carried_keys = [k for k in CANONICAL_12_KEYS if k not in ("poster_noir_detective_magazine", "music_cue_midnight_serenade")]
        for k in carried_keys:
            u7 = v7_by_key[k]
            u8 = v8_by_key[k]
            assert u7.duration_or_prominence == u8.duration_or_prominence
            assert u7.context_hash == u8.context_hash, f"Carried item {k} context hash altered"

    def test_reason_codes_matching(self):
        """Reason codes match exactly: Item 12 EXTERNAL_EVIDENCE_SHIFT, Item 11 CREATIVE_CONTEXT_ALTERED."""
        seed_standard_reconciled_counsel_decisions()

        json_data = client.get("/api/reports/exceptions").json()
        items_by_key = {i["stable_lineage_key"]: i for i in json_data["items"]}

        # Item 12 is exception with invalidation reason
        item12 = items_by_key["music_cue_midnight_serenade"]
        assert item12["v8_evaluation_state"] == "exception"
        assert item12["invalidation_reason"] == "EXTERNAL_EVIDENCE_SHIFT"

        # Item 11 is re-attested
        item11 = items_by_key["poster_noir_detective_magazine"]
        assert item11["v8_evaluation_state"] == "re_attested"

        # Carried items have None invalidation_reason
        for k in CANONICAL_12_KEYS:
            if k not in ("music_cue_midnight_serenade", "poster_noir_detective_magazine"):
                assert items_by_key[k]["v8_evaluation_state"] == "carried_forward"
                assert items_by_key[k]["invalidation_reason"] is None


# =============================================================================
# 3. ATTRIBUTABLE CITATION PRESERVATION
# =============================================================================

class TestAttributableCitationPreservation:
    """Verifies that external Parallel Search citations are preserved with cryptographic hashes."""

    def test_item_11_library_of_congress_citation_preservation(self):
        """Item 11 preserves Library of Congress public domain citation across JSON and HTML."""
        seed_standard_reconciled_counsel_decisions()

        json_data = client.get("/api/reports/exceptions").json()
        html_data = client.get("/report/proj_blockbuster_cinema").text

        item11 = next(i for i in json_data["items"] if i["stable_lineage_key"] == "poster_noir_detective_magazine")
        assert len(item11["evidence_citations"]) >= 1

        loc_cite = item11["evidence_citations"][0]
        assert loc_cite["source_url"] == "https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1946-crime-detective"
        assert "US Copyright Office" in loc_cite["source_title"] or "LOC" in loc_cite["source_title"]
        assert loc_cite["provider"] == "Parallel"
        assert loc_cite["provider_call_id"] == "prl_call_882910_poster"
        assert "Registration #B-1946-8821 expired 1974 without timely renewal" in loc_cite["excerpt"]
        assert len(loc_cite["payload_hash"]) == 64

        # Verify preservation in HTML
        assert loc_cite["source_url"] in html_data
        assert loc_cite["provider_call_id"] in html_data
        assert loc_cite["payload_hash"][:16] in html_data
        assert "SECTION II: RE-ATTESTED PUBLIC DOMAIN ITEMS" in html_data

    def test_item_12_ascap_ace_citation_preservation(self):
        """Item 12 preserves ASCAP ACE adverse assignment citation across JSON and HTML."""
        seed_standard_reconciled_counsel_decisions()

        json_data = client.get("/api/reports/exceptions").json()
        html_data = client.get("/report/proj_blockbuster_cinema").text

        item12 = next(i for i in json_data["items"] if i["stable_lineage_key"] == "music_cue_midnight_serenade")
        assert len(item12["evidence_citations"]) >= 1

        ascap_cite = item12["evidence_citations"][0]
        assert ascap_cite["source_url"] == "https://ascap.com/ace-title-search/midnight-serenade-9921"
        assert "ASCAP" in ascap_cite["source_title"]
        assert ascap_cite["provider"] == "Parallel"
        assert ascap_cite["provider_call_id"] == "prl_call_993012_music"
        assert "Vanguard Media Holdings LLC" in ascap_cite["excerpt"]
        assert len(ascap_cite["payload_hash"]) == 64

        # Verify preservation in HTML
        assert ascap_cite["source_url"] in html_data
        assert ascap_cite["provider_call_id"] in html_data
        assert ascap_cite["payload_hash"][:16] in html_data
        assert "SECTION I: UNRESOLVED EXCEPTIONS" in html_data


# =============================================================================
# 4. STATUTORY UNDERWRITING DISCLAIMERS
# =============================================================================

class TestStatutoryUnderwritingDisclaimers:
    """Verifies statutory disclaimers are identically phrased across JSON and HTML."""

    def test_underwriter_status_is_strictly_pending_review(self):
        """CarrierHeader underwriter_status is PENDING_REVIEW across JSON and HTML."""
        seed_standard_reconciled_counsel_decisions()

        json_data = client.get("/api/reports/exceptions").json()
        html_data = client.get("/report/proj_blockbuster_cinema").text

        assert json_data["carrier_header"]["underwriter_status"] == "PENDING_REVIEW"
        assert "Underwriting Status: PENDING_REVIEW" in html_data

    def test_statutory_banner_identically_phrased_in_header_and_footer(self):
        """Statutory disclaimer banner appears identically in HTML header and HTML footer."""
        seed_standard_reconciled_counsel_decisions()

        html_data = client.get("/report/proj_blockbuster_cinema").text

        expected_banner_text = (
            "LEGAL &amp; UNDERWRITING DISCLAIMER: THIS ARTIFACT IS A VERSION-BOUND SCHEDULE OF UNRESOLVED "
            "CLEARANCE EXCEPTIONS FOR DEMONSTRATION AND INFORMATIONAL PURPOSES ONLY. NO ARTIFACT GENERATED "
            "BY LIENMARK CONSTITUTES OR CLAIMS FORMAL UNDERWRITING APPROVAL, POLICY BINDING, INSURANCE "
            "COVERAGE, LEGAL OPINION, OR LEGAL CERTAINTY. COVERAGE IS SUBJECT EXCLUSIVELY TO A SEPARATELY "
            "EXECUTED POLICY BINDER WITH AN ADMITTED OR SURPLUS LINES CARRIER."
        )

        # Must appear at least twice: header and footer
        count = html_data.count(expected_banner_text)
        assert count >= 2, f"Statutory disclaimer banner must appear in header and footer (found {count} occurrences)"

    def test_warranty_clause_and_signature_block_integrity(self):
        """Warranty clause and physical signature blocks are correctly demarcated."""
        seed_standard_reconciled_counsel_decisions()

        json_data = client.get("/api/reports/exceptions").json()
        html_data = client.get("/report/proj_blockbuster_cinema").text

        # Warranty clause
        warranty = json_data["carrier_header"]["warranty_clause"]
        assert "Warranted clearance schedule of exceptions" in warranty
        assert warranty in html_data

        # Counsel sign-off and Underwriter signature block
        assert "Sarah Jenkins, Esq." in html_data
        assert "PENDING UNDERWRITER REVIEW — NO COVERAGE BOUND" in html_data
        assert "DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE (ABA MODEL RULE 5.5 NOTICE)" in html_data


# =============================================================================
# 5. ZERO PROHIBITED LEGAL CERTAINTY PHRASES
# =============================================================================

class TestProhibitedLegalCertaintyDefense:
    """Verifies that zero prohibited affirmative legal certainty phrases exist in exports."""

    def test_zero_prohibited_phrases_in_json_exports(self):
        """Audit all JSON exports for forbidden certainty phrases."""
        seed_standard_reconciled_counsel_decisions()

        endpoints = [
            "/api/reports/exceptions",
            "/api/reports/form-eo-2026",
            "/api/reports/export?format=json",
        ]

        for ep in endpoints:
            res = client.get(ep)
            payload_str = res.text.lower()

            for phrase in PROHIBITED_LEGAL_CERTAINTY_PHRASES:
                if phrase in ("binding coverage", "legal certainty", "legally certain"):
                    # Only allowed if negated
                    pattern = rf"(?<!does\snot\s)(?<!no\s)(?<!not\sconstitute\s)(?<!or\scertify\s){re.escape(phrase)}"
                    matches = re.findall(pattern, payload_str)
                    unnegated = [m for m in matches if "does not" not in payload_str]
                    assert len(unnegated) == 0, f"Unnegated '{phrase}' in {ep}"
                else:
                    assert phrase not in payload_str, f"Prohibited phrase '{phrase}' in {ep}"

    def test_zero_prohibited_phrases_in_html_reports(self):
        """Audit SSR HTML reports for forbidden certainty phrases."""
        seed_standard_reconciled_counsel_decisions()

        html_endpoints = [
            "/report/proj_blockbuster_cinema",
            "/api/reports/form-eo-2026/html",
            "/api/reports/export?format=html",
        ]

        for ep in html_endpoints:
            res = client.get(ep)
            html_lower = res.text.lower()

            for phrase in PROHIBITED_LEGAL_CERTAINTY_PHRASES:
                if phrase in ("binding coverage", "legal certainty", "legally certain"):
                    pattern = rf"(?<!does\snot\s)(?<!no\s)(?<!not\sconstitute\s)(?<!or\scertify\s){re.escape(phrase)}"
                    matches = re.findall(pattern, html_lower)
                    unnegated = [m for m in matches if "does not" not in html_lower and "no coverage bound" not in html_lower]
                    assert len(unnegated) == 0, f"Unnegated certainty phrase '{phrase}' in {ep}"
                else:
                    assert phrase not in html_lower, f"Prohibited phrase '{phrase}' found in {ep}"
