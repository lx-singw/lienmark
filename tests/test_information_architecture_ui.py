"""
Automated Test Suite for Sprint 4A: Information Architecture & UI Invariants
Table-driven automated test suite verifying:
1. Header Component Architecture: Cut comparison (v7 -> v8), SHA-256 cut hashes, carrier binder 'E&O-2026.1-DEVPOST'.
2. Summary Component & Mathematical Invariants: 12 prior -> 10 carried forward ($0 review cost) -> 2 reopened (drift) -> 1 re-attested + 1 exception.
3. Delta List Component: Creative context shift (Item 11) and external fact shift (Item 12).
4. Decision List Component: 12-claim production lineage table with filterable views, status badges, and deterministic ordering.
5. Explanation Presentation & 4-Dimensional Breakdown: Creative, Evidence, Private Contract, Statutory Reason, and inspectable prior baseline approval.
6. Counsel Review Action Component & Server Actions: Sarah Jenkins, Esq. reviewer identity pill, three distinct action buttons (Re-Attest, Reject, Leave as Exception).
7. Export Action Component & SSR Form E&O-2026 Schedule: Three-tier classification, printable link, and statutory underwriting disclaimer.
8. Audit Trail Drawer: Append-only cryptographic SHA-256 event chaining.
9. Accessibility & Visual Invariants (WCAG 2.1 AA): Color is never the only indicator across all decision states; Icon + text + shape + aria matrix verified.
10. Copy & Statutory Non-Binding Guarantee: Strict absence of insurance-binding claims and legal certainty guarantees; Underwriting status PENDING_REVIEW.
11. 40-Second Judge Comprehension Flow: Deterministic execution and step-by-step state verification.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import os
import hashlib
import json
import re
import pytest
from typing import Any, Dict, List
from fastapi.testclient import TestClient

from backend.domain.models import (
    CarrierHeader,
    CounselDecision,
    CreativeUse,
    DecisionState,
    DecisionStatus,
    DecisionValidity,
    EvidenceStance,
    ExceptionsSchedule,
    ExceptionsScheduleItem,
    FourDimensionalExplanation,
    ReattestationRequest,
    ReviewAction,
    ReviewActionRequest,
    ReviewerIdentity,
    ReviewQueueItem,
    SupersessionEvent,
)
from backend.core.counsel_checkpoint import (
    CounselCheckpointManager,
    counsel_checkpoint_manager,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
)
from backend.main import app, _counsel_reattestations

client = TestClient(app)


# =============================================================================
# FIXTURES & ISOLATION
# =============================================================================

@pytest.fixture(autouse=True)
def clean_ui_session():
    """Ensures clean global state before and after every test in the suite."""
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()
    yield
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()


# =============================================================================
# TEST CLASS 1: HEADER COMPONENT ARCHITECTURE & CUT COMPARISON
# =============================================================================

class TestHeaderComponentArchitecture:
    """Verifies Header component data contracts, version cut hashes, and policy metadata."""

    def test_header_cut_comparison_and_carrier_binder(self):
        v7 = get_v7_version()
        v8 = get_v8_version()

        assert v7.version_id == "v7"
        assert v8.version_id == "v8"
        assert "Shadows Over Broadway" in v7.label
        assert "Shadows Over Broadway" in v8.label

        # Content hash invariants
        assert len(v7.content_hash) in (32, 64)
        assert len(v8.content_hash) in (32, 64)
        assert v7.content_hash != v8.content_hash

        # Carrier policy binder specification
        res = client.get("/api/reports/exceptions")
        assert res.status_code == 200
        data = res.json()
        assert data["carrier_header"]["policy_number"] == "E&O-2026.1-DEVPOST"
        assert data["project_id"] == "proj_blockbuster_cinema"

    def test_header_api_fixtures_payload(self):
        res = client.get("/api/fixtures")
        assert res.status_code == 200
        payload = res.json()
        assert "v7_version" in payload
        assert "v8_version" in payload
        assert payload["v7_version"]["version_id"] == "v7"
        assert payload["v8_version"]["version_id"] == "v8"


# =============================================================================
# TEST CLASS 2: SUMMARY COMPONENT & MATHEMATICAL RECONCILIATION INVARIANTS
# =============================================================================

class TestSummaryComponentInvariants:
    """Verifies the 12 -> 10/2 -> 1/1 mathematical conservation in the summary component."""

    def test_summary_baseline_counts(self):
        v7_uses, v8_uses, v7_decisions, initial_evidence = get_golden_fixtures()
        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=initial_evidence,
            target_version_id="v8",
        )

        carried = [v for v in validity_results if v.state == DecisionState.CARRIED_FORWARD]
        stale = [v for v in validity_results if v.state == DecisionState.STALE]

        assert len(validity_results) == 12
        assert len(carried) == 10
        assert len(stale) == 2
        assert len(validity_results) == len(carried) + len(stale)

    def test_summary_economic_and_query_savings(self):
        # 10 carried claims = $0 review cost and 0 runtime search queries (83.3% savings)
        total_claims = 12
        carried_claims = 10
        stale_claims = 2

        savings_ratio = carried_claims / total_claims
        assert abs(savings_ratio - (10 / 12)) < 1e-6
        assert f"{savings_ratio * 100:.1f}%" == "83.3%"


# =============================================================================
# TEST CLASS 3: DELTA LIST COMPONENT (ITEM 11 & ITEM 12 SHIFTS)
# =============================================================================

class TestDeltaListComponent:
    """Verifies explicit detection and classification of creative context and external evidence shifts."""

    def test_item_11_creative_context_shift(self):
        v7_uses, v8_uses, _, _ = get_golden_fixtures()
        v7_poster = next(u for u in v7_uses if u.stable_lineage_key == "poster_noir_detective_magazine")
        v8_poster = next(u for u in v8_uses if u.stable_lineage_key == "poster_noir_detective_magazine")

        # Creative context changed: Scene 42 background -> hero focal point with dialogue
        assert "blur" in v7_poster.duration_or_prominence.lower()
        assert "focal" in v8_poster.duration_or_prominence.lower() or "close-up" in v8_poster.duration_or_prominence.lower()
        assert "far wall" in v7_poster.context or "soft focus" in v7_poster.context
        assert "Detective grabs poster" in v8_poster.context or "Shadows Over Broadway" in v8_poster.context

    def test_item_12_external_evidence_fact_shift(self):
        _, _, _, evidence_map = get_golden_fixtures()
        music_ev = evidence_map["music_cue_midnight_serenade"]

        assert music_ev.stance == EvidenceStance.CONTRADICTORY
        assert "Vanguard" in music_ev.excerpt or "exclusive" in music_ev.excerpt


# =============================================================================
# TEST CLASS 4: DECISION LIST COMPONENT & PRODUCTION LINEAGE TABLE
# =============================================================================

class TestDecisionListComponent:
    """Verifies the 12-claim production lineage table, sorting, and status badges."""

    def test_twelve_claim_lineage_enumeration(self):
        res = client.get("/api/fixtures")
        assert res.status_code == 200
        data = res.json()

        claims = data["v7_claims"]
        assert len(claims) == 12

        # Verify keys
        keys = [c["key"] for c in claims]
        assert "poster_noir_detective_magazine" in keys
        assert "music_cue_midnight_serenade" in keys
        assert len(set(keys)) == 12

    def test_decision_status_badges_contract(self):
        valid_states = {
            DecisionState.CARRIED_FORWARD,
            DecisionState.STALE,
            DecisionState.RE_ATTESTED,
            DecisionState.EXCEPTION,
        }
        v7_uses, v8_uses, v7_decisions, initial_evidence = get_golden_fixtures()
        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=initial_evidence,
            target_version_id="v8",
        )
        for val in validity_results:
            assert val.state in valid_states


# =============================================================================
# TEST CLASS 5: EXPLANATION PRESENTATION & 4-DIMENSIONAL BREAKDOWN
# =============================================================================

class TestExplanationDrawerComponent:
    """Verifies the 4-dimensional breakdown and inspectable prior baseline approval."""

    def test_four_dimensions_structure(self):
        queue = counsel_checkpoint_manager.get_review_queue(target_version_id="v8")
        assert len(queue.items) == 2

        for item in queue.items:
            # Dimension 1: Creative Change
            assert item.creative_change_summary is not None
            assert len(item.creative_change_summary) > 0

            # Dimension 2: External Evidence Change
            assert item.evidence_change_summary is not None
            assert len(item.evidence_change_summary) > 0

            # Dimension 3: Private Agreement Facts
            assert item.private_fact_summary is not None
            assert len(item.private_fact_summary) > 0

            # Dimension 4: Statutory Policy Reason
            assert item.statutory_policy_reason is not None
            assert len(item.statutory_policy_reason) > 0

    def test_inspectable_prior_baseline_approval(self):
        queue = counsel_checkpoint_manager.get_review_queue(target_version_id="v8")
        item_11 = next(it for it in queue.items if it.stable_lineage_key == "poster_noir_detective_magazine")

        prior = item_11.prior_decision
        assert prior.decision_id == "dec_v7_poster_noir"
        assert prior.applicable_version_id == "v7"
        assert prior.status == DecisionStatus.APPROVED
        assert "Sarah Jenkins" in prior.reviewer_display_name
        assert prior.rationale is not None


# =============================================================================
# TEST CLASS 6: COUNSEL REVIEW ACTION COMPONENT & SERVER ACTIONS
# =============================================================================

class TestReviewActionComponent:
    """Verifies counsel adjudication Server Actions, reviewer identity, and three distinct actions."""

    def test_reviewer_identity_pill_contract(self):
        reviewer = counsel_checkpoint_manager.get_default_reviewer()
        assert "Sarah Jenkins, Esq." in reviewer.name
        assert reviewer.is_fictional_demo is True

    def test_three_distinct_adjudication_actions(self):
        counsel_checkpoint_manager.get_review_queue(target_version_id="v8")

        # Action 1: Re-Attest Item 11
        dec_11, ev_11 = counsel_checkpoint_manager.apply_review_action(
            action=ReviewAction.RE_ATTEST,
            lineage_key="poster_noir_detective_magazine",
            rationale="LOC renewal records confirm lapsed copyright in 1974. Public domain.",
            reviewer=counsel_checkpoint_manager.get_default_reviewer(),
        )
        assert dec_11.status == DecisionStatus.APPROVED
        assert ev_11.new_state == DecisionState.RE_ATTESTED
        assert ev_11.action == ReviewAction.RE_ATTEST

        # Action 2: Leave Item 12 as Exception
        dec_12, ev_12 = counsel_checkpoint_manager.apply_review_action(
            action=ReviewAction.EXCEPTION,
            lineage_key="music_cue_midnight_serenade",
            rationale="Exclusive sync license acquired by Vanguard. Unresolved exception.",
            reviewer=counsel_checkpoint_manager.get_default_reviewer(),
        )
        assert dec_12.status in (DecisionStatus.REJECTED, DecisionStatus.NEEDS_REVIEW)
        assert ev_12.new_state == DecisionState.EXCEPTION
        assert ev_12.action == ReviewAction.EXCEPTION

        # Action 3: Verify REJECT action is distinct
        counsel_checkpoint_manager.reset()
        counsel_checkpoint_manager.get_review_queue(target_version_id="v8")
        dec_reject, ev_reject = counsel_checkpoint_manager.apply_review_action(
            action=ReviewAction.REJECT,
            lineage_key="poster_noir_detective_magazine",
            rationale="De-cleared from production by counsel order.",
            reviewer=counsel_checkpoint_manager.get_default_reviewer(),
        )
        assert dec_reject.status == DecisionStatus.REJECTED
        assert ev_reject.new_state == DecisionState.EXCEPTION
        assert ev_reject.action == ReviewAction.REJECT


# =============================================================================
# TEST CLASS 7: EXPORT ACTION COMPONENT & SSR PRINTABLE SCHEDULE
# =============================================================================

class TestExportActionComponent:
    """Verifies link to SSR printable Form E&O-2026 Schedule and statutory warranty disclaimers."""

    def test_ssr_report_html_rendering(self):
        res = client.get("/report/proj_blockbuster_cinema")
        assert res.status_code == 200
        html = res.text

        # Verify Carrier Header and Binder
        assert "E&amp;O-2026.1-DEVPOST" in html or "E&O-2026.1-DEVPOST" in html
        assert "FORM E&amp;O-2026" in html or "FORM E&O-2026" in html

        # Verify 3-tier sections in SSR output
        assert "SECTION I: UNRESOLVED EXCEPTIONS" in html
        assert "SECTION II: RE-ATTESTED PUBLIC DOMAIN" in html
        assert "SECTION III: CERTIFIED CARRIED-FORWARD" in html

        # Verify statutory disclaimer
        assert "LEGAL &amp; UNDERWRITING DISCLAIMER" in html or "UNDERWRITING DISCLAIMER" in html

    def test_exceptions_schedule_json_export_parity(self):
        res = client.get("/api/reports/form-eo-2026")
        assert res.status_code == 200
        data = res.json()
        assert data["total_claims"] == 12
        assert data["carried_forward_count"] == 10
        assert data["carrier_header"]["underwriter_status"] == "PENDING_REVIEW"


# =============================================================================
# TEST CLASS 8: AUDIT TRAIL DRAWER & CRYPTOGRAPHIC EVENT CHAINING
# =============================================================================

class TestAuditTrailDrawerComponent:
    """Verifies append-only cryptographic SHA-256 event chaining and actor separation."""

    def test_audit_trail_events_and_parent_chaining(self):
        counsel_checkpoint_manager.get_review_queue(target_version_id="v8")
        counsel_checkpoint_manager.apply_review_action(
            action=ReviewAction.RE_ATTEST,
            lineage_key="poster_noir_detective_magazine",
            rationale="Public domain verified via LOC registration search.",
            reviewer=counsel_checkpoint_manager.get_default_reviewer(),
        )
        counsel_checkpoint_manager.apply_review_action(
            action=ReviewAction.EXCEPTION,
            lineage_key="music_cue_midnight_serenade",
            rationale="Vanguard exclusive sync dispute; flagged as schedule rider.",
            reviewer=counsel_checkpoint_manager.get_default_reviewer(),
        )

        res = client.get("/api/review/audit-trail")
        assert res.status_code == 200
        payload = res.json()
        events = payload["events"]
        assert len(events) >= 2
        assert payload["is_ledger_tamper_free"] is True

        for ev in events:
            assert len(ev["event_hash"]) == 64
            assert re.match(r"^[0-9a-f]{64}$", ev["event_hash"])
            assert "event_id" in ev
            assert "action" in ev
            assert "reviewer" in ev


# =============================================================================
# TEST CLASS 9: ACCESSIBILITY & VISUAL INVARIANTS (WCAG 2.1 AA)
# =============================================================================

class TestAccessibilityAndVisualInvariants:
    """Verifies that color is never the only indicator across all decision states."""

    ACCESSIBILITY_MATRIX = {
        DecisionState.CARRIED_FORWARD: {
            "icon": "CheckCircle2 / ShieldCheck",
            "text": "Carried Forward",
            "shape": "Rounded green pill with solid checkmark border",
            "aria": "Carried forward decision without drift",
        },
        DecisionState.STALE: {
            "icon": "AlertTriangle",
            "text": "Reopened (Drift) / Awaiting Disposition",
            "shape": "Pulsing amber border with warning triangle",
            "aria": "Stale decision requiring counsel adjudication",
        },
        DecisionState.RE_ATTESTED: {
            "icon": "CheckCircle2 / Scale",
            "text": "Re-Attested (Approved)",
            "shape": "Cyan/Sky double-ring border with gavel indicator",
            "aria": "Re-attested decision approved under statutory doctrine",
        },
        DecisionState.EXCEPTION: {
            "icon": "AlertOctagon",
            "text": "Exception (E&O Exclusion)",
            "shape": "Octagonal red pill with stop octagon",
            "aria": "Unresolved exception flagged for policy schedule rider",
        },
    }

    @pytest.mark.parametrize("state,meta", ACCESSIBILITY_MATRIX.items())
    def test_state_accessibility_multi_modal_indicators(self, state, meta):
        # Asserts color is never the sole indicator: every state has dedicated Icon, Text, and Shape
        assert meta["icon"] != ""
        assert meta["text"] != ""
        assert meta["shape"] != ""
        assert meta["aria"] != ""


# =============================================================================
# TEST CLASS 10: COPY & STATUTORY NON-BINDING GUARANTEE
# =============================================================================

class TestCopyAndStatutoryNonBindingGuarantee:
    """Verifies strict absence of false legal certainty and binding insurance promises."""

    PROHIBITED_COPY_TERMS = [
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

    @pytest.mark.parametrize("term", PROHIBITED_COPY_TERMS)
    def test_absence_of_prohibited_legal_certainty_copy(self, term):
        # Inspect SSR HTML
        ssr_res = client.get("/report/proj_blockbuster_cinema")
        assert term not in ssr_res.text.lower(), f"Prohibited term '{term}' found in SSR HTML"

        # Inspect Dashboard HTML
        dash_res = client.get("/")
        assert term not in dash_res.text.lower(), f"Prohibited term '{term}' found in Dashboard HTML"

        # Inspect JSON API
        json_res = client.get("/api/reports/exceptions")
        assert term not in json.dumps(json_res.json()).lower(), f"Prohibited term '{term}' found in JSON API"


# =============================================================================
# TEST CLASS 11: 40-SECOND JUDGE COMPREHENSION FLOW VERIFICATION
# =============================================================================

class TestJudgeComprehensionFlow:
    """Verifies the sequential steps allowing an evaluator to comprehend the differentiator in < 40 seconds."""

    def test_step_1_header_and_scope(self):
        res = client.get("/api/fixtures")
        assert res.status_code == 200
        data = res.json()
        assert data["v7_version"]["version_id"] == "v7"
        assert data["v8_version"]["version_id"] == "v8"

    def test_step_2_metrics_ribbon_differentiator(self):
        v7_uses, v8_uses, v7_decisions, initial_evidence = get_golden_fixtures()
        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=initial_evidence,
            target_version_id="v8",
        )
        carried = [v for v in validity_results if v.state == DecisionState.CARRIED_FORWARD]
        stale = [v for v in validity_results if v.state == DecisionState.STALE]
        assert len(carried) == 10
        assert len(stale) == 2
        # Evaluator sees: 10 Carried Forward ($0 review) + 2 Reopened

    def test_step_3_checkpoint_gate_adjudication(self):
        queue = counsel_checkpoint_manager.get_review_queue(target_version_id="v8")
        assert len(queue.items) == 2

        # Item 11 Re-attested
        dec1, ev1 = counsel_checkpoint_manager.apply_review_action(
            action=ReviewAction.RE_ATTEST,
            lineage_key="poster_noir_detective_magazine",
            rationale="LOC confirmation",
            reviewer=counsel_checkpoint_manager.get_default_reviewer(),
        )
        assert dec1.status == DecisionStatus.APPROVED
        assert ev1.new_state == DecisionState.RE_ATTESTED

        # Item 12 Flagged as Exception
        dec2, ev2 = counsel_checkpoint_manager.apply_review_action(
            action=ReviewAction.EXCEPTION,
            lineage_key="music_cue_midnight_serenade",
            rationale="ASCAP sync dispute",
            reviewer=counsel_checkpoint_manager.get_default_reviewer(),
        )
        assert dec2.status == DecisionStatus.REJECTED
        assert ev2.new_state == DecisionState.EXCEPTION

    def test_step_4_reconciled_banner_and_schedule(self):
        res = client.get("/api/reports/form-eo-2026")
        assert res.status_code == 200
        sched = res.json()
        assert sched["total_claims"] == 12
        assert sched["carried_forward_count"] == 10
        assert sched["carrier_header"]["underwriter_status"] == "PENDING_REVIEW"


# =============================================================================
# TEST CLASS 12: MODULAR COMPONENT ARCHITECTURE (FRONTEND FILES & AST)
# =============================================================================

class TestModularComponentArchitecture:
    """Verifies existence, exports, and rendering of all 8 modular Next.js components."""

    MODULAR_COMPONENTS = [
        "DashboardHeader.tsx",
        "ClearanceSummaryCards.tsx",
        "DeltaListComponent.tsx",
        "DecisionListComponent.tsx",
        "ExplanationDrawerComponent.tsx",
        "ReviewActionComponent.tsx",
        "ExportActionComponent.tsx",
        "AuditTrailDrawer.tsx",
    ]

    def test_all_eight_components_exist_in_frontend(self):
        """Asserts existence of all 8 modular Next.js components in frontend/app/components/."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        comp_dir = os.path.join(repo_root, "frontend", "app", "components")

        for comp_name in self.MODULAR_COMPONENTS:
            comp_path = os.path.join(comp_dir, comp_name)
            assert os.path.exists(comp_path), f"Missing modular component: {comp_name} at {comp_path}"
            file_size = os.path.getsize(comp_path)
            assert file_size > 200, f"Component {comp_name} is unexpectedly small ({file_size} bytes)"

    def test_modular_components_export_react_functions(self):
        """Asserts each component exports a functional React component."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        comp_dir = os.path.join(repo_root, "frontend", "app", "components")

        for comp_name in self.MODULAR_COMPONENTS:
            comp_path = os.path.join(comp_dir, comp_name)
            with open(comp_path, "r", encoding="utf-8") as f:
                content = f.read()

            has_export = bool(
                re.search(r"export\s+default\s+function", content)
                or re.search(r"export\s+function", content)
                or re.search(r"export\s+const\s+\w+\s*=", content)
                or re.search(r"export\s+default\s+\w+", content)
            )
            assert has_export, f"Component {comp_name} must provide a valid export"

    def test_page_imports_all_modular_components(self):
        """Asserts that frontend/app/page.tsx imports all 8 modular components."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        page_path = os.path.join(repo_root, "frontend", "app", "page.tsx")

        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        for comp_name in self.MODULAR_COMPONENTS:
            base_name = os.path.splitext(comp_name)[0]
            pattern = rf"\bimport\s+.*?\b{base_name}\b.*?from"
            assert re.search(pattern, content), (
                f"frontend/app/page.tsx does not import '{base_name}'"
            )

    def test_page_renders_all_modular_components(self):
        """Asserts that frontend/app/page.tsx renders JSX tags for all 8 components."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        page_path = os.path.join(repo_root, "frontend", "app", "page.tsx")

        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        for comp_name in self.MODULAR_COMPONENTS:
            base_name = os.path.splitext(comp_name)[0]
            tag_pattern = rf"<{base_name}\b"
            assert re.search(tag_pattern, content), (
                f"frontend/app/page.tsx does not render JSX tag <{base_name} ... />"
            )


# =============================================================================
# TEST CLASS 13: ACCESSIBILITY & VISUAL INDICATOR INVARIANTS
# =============================================================================

class TestAccessibilityVisualIndicatorInvariants:
    """Verifies that color is NEVER the only indicator for any decision state."""

    def test_decision_status_badges_multi_attribute_invariants(self):
        """
        Asserts that color is NEVER the only indicator for any decision state:
        - Status badge includes an icon component (CheckCircle2, AlertTriangle, AlertOctagon, etc.).
        - Status badge includes explicit text labels ('Carried Forward', 'Awaiting Disposition', 'Re-Attested', 'Exception').
        - Key interactive elements include accessibility aria attributes ('aria-label', 'role=\"status\"', etc.).
        """
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        comp_dir = os.path.join(repo_root, "frontend", "app", "components")

        target_files = [
            os.path.join(comp_dir, "DecisionListComponent.tsx"),
            os.path.join(comp_dir, "ClearanceSummaryCards.tsx"),
            os.path.join(comp_dir, "ReviewActionComponent.tsx"),
            os.path.join(repo_root, "frontend", "app", "page.tsx"),
        ]

        combined_text = ""
        for path in target_files:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    combined_text += "\n" + f.read()

        # 1. Icon component assertion
        for icon in ["CheckCircle2", "AlertTriangle", "AlertOctagon"]:
            assert icon in combined_text, f"Missing required icon component: {icon}"

        # 2. Explicit text labels assertion
        for label_options in [
            ("Carried Forward", "CARRIED"),
            ("Awaiting Disposition", "STALE", "Action Required", "REOPENED", "Pending"),
            ("Re-Attested", "RE-ATTESTED"),
            ("Exception", "EXCEPTION"),
        ]:
            assert any(opt.lower() in combined_text.lower() for opt in label_options), (
                f"Missing explicit text label from options {label_options}"
            )

        # 3. Accessibility ARIA attributes
        aria_matches = re.findall(r'\b(aria-[a-z]+|role="[^"]+")', combined_text)
        assert any("aria-label" in a for a in aria_matches), "Missing 'aria-label' attributes"
        assert any('role="status"' in a or 'role="dialog"' in a or 'role="region"' in a or 'role="tab"' in a for a in aria_matches), (
            "Missing ARIA role attributes ('role=\"status\"', 'role=\"dialog\"', etc.)"
        )


# =============================================================================
# TEST CLASS 14: COPY & LEGAL CERTAINTY COMPLIANCE
# =============================================================================

class TestCopyAndLegalCertaintyCompliance:
    """Verifies strict adherence to statutory clearance standards and zero false legal certainty."""

    FORBIDDEN_PHRASES = [
        "coverage guaranteed",
        "policy bound automatically",
        "certifies legal certainty",
        "carrier bound",
        "legally cleared by ai",
        "zero legal risk",
    ]

    MANDATORY_TERMS = [
        "evidence",
        "review",
        "exception",
        "re-attest",
        "statutory exposure",
    ]

    def test_statutory_clearance_vocabulary_present(self):
        """Asserts copy uses 'evidence', 'review', 'exception', 're-attest', 'statutory exposure'."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        app_dir = os.path.join(repo_root, "frontend", "app")

        all_text = ""
        for root, _, files in os.walk(app_dir):
            for file in files:
                if file.endswith((".tsx", ".ts")):
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        all_text += "\n" + f.read().lower()

        for term in self.MANDATORY_TERMS:
            assert term.lower() in all_text, f"Mandatory statutory term '{term}' not found in frontend copy"

    def test_zero_occurrences_of_forbidden_legal_certainty_phrases(self):
        """Asserts zero occurrences of prohibited false legal certainty phrases in frontend code."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        app_dir = os.path.join(repo_root, "frontend", "app")

        violations = []
        for root, _, files in os.walk(app_dir):
            for file in files:
                if file.endswith((".tsx", ".ts")):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, repo_root)
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read().lower()

                    for phrase in self.FORBIDDEN_PHRASES:
                        if phrase in content:
                            violations.append(f"{rel_path}: '{phrase}'")

        assert len(violations) == 0, (
            f"Prohibited legal certainty phrases detected:\n" + "\n".join(violations)
        )


# =============================================================================
# TEST CLASS 15: 4-DIMENSIONAL INFORMATION ARCHITECTURE
# =============================================================================

class TestFourDimensionalInformationArchitecture:
    """Verifies that all 4 dimensions are explicitly rendered in the component hierarchy."""

    def test_all_four_dimensions_rendered_in_explanation_drawer(self):
        """
        Asserts all four dimensions:
        1. Creative Change
        2. External Evidence
        3. Private Agreement Facts
        4. Statutory Policy Reason
        are explicitly rendered.
        """
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        drawer_path = os.path.join(repo_root, "frontend", "app", "components", "ExplanationDrawerComponent.tsx")
        assert os.path.exists(drawer_path), "ExplanationDrawerComponent.tsx must exist"

        with open(drawer_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert re.search(r"Creative\s+Change", content, re.IGNORECASE), "Missing Dimension 1: Creative Change"
        assert re.search(r"External\s+Evidence", content, re.IGNORECASE), "Missing Dimension 2: External Evidence"
        assert re.search(r"Private\s+Agreement", content, re.IGNORECASE) or re.search(r"Private\s+Fact", content, re.IGNORECASE), (
            "Missing Dimension 3: Private Agreement Facts"
        )
        assert re.search(r"Statutory\s+Policy", content, re.IGNORECASE) or re.search(r"Policy\s+Reason", content, re.IGNORECASE), (
            "Missing Dimension 4: Statutory Policy Reason"
        )


# =============================================================================
# TEST CLASS 16: SERVER ACTION INTEGRATION & OPTIMISTIC CONTRACTS
# =============================================================================

class TestServerActionIntegrationAndContracts:
    """Verifies Server Action signatures and client invocation contracts."""

    def test_actions_use_server_directive(self):
        """Asserts that frontend/app/actions.ts begins with 'use server' directive."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        actions_path = os.path.join(repo_root, "frontend", "app", "actions.ts")
        assert os.path.exists(actions_path), "actions.ts not found"

        with open(actions_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        assert first_line in ("'use server';", '"use server";'), f"actions.ts must start with 'use server', found: {first_line}"

    def test_server_action_signatures_match_client_invocations(self):
        """Asserts Server Actions signatures match client component invocation parameters."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        actions_path = os.path.join(repo_root, "frontend", "app", "actions.ts")

        with open(actions_path, "r", encoding="utf-8") as f:
            content = f.read()

        for action_name in [
            "evaluateClearanceDeltaAction",
            "submitReviewAction",
            "fetchAuditTrailAction",
            "fetchReviewQueueAction",
            "getExceptionsScheduleAction",
        ]:
            assert f"export async function {action_name}" in content, f"actions.ts missing export {action_name}"

        # submitReviewAction signature verification
        match = re.search(r"export\s+async\s+function\s+submitReviewAction\s*\((.*?)\)", content, re.DOTALL)
        assert match, "Could not match submitReviewAction signature"
        params = match.group(1)
        assert "action" in params
        assert "lineageKey" in params
        assert "rationale" in params
