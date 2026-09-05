"""
tests/test_evidence_pack_and_reproduction.py

Sprint 5C Task 2: Evidence Pack & Reproduction Test Engineer Suite
In accordance with Sprint 5C in docs/winning/04-build-roadmap.md (§10, Sprint 5C):
  "Deliverables:
   - Architecture diagram.
   - Runtime trace screenshots.
   - Test summary.
   - Integration code pointers.
   - Before/after workflow visual.
   - Known-limitations list.
   - Exact reproduction steps.
   The README must only name commands and files that actually work."

Exhaustive automated verification suite:
1. Test README Code Pointers: Asserts every file and module path referenced in README.md
   exists on disk and exports the documented classes, functions, and models.
2. Test README Reproduction Commands: Asserts that all CLI commands
   (scripts/run_quality_gate.py, scripts/run_rehearsal.py, scripts/run_live_smoke.py,
   scripts/run_license_audit.py) exist, compile, and are executable.
3. Test Architecture Invariant Verification: Asserts that the 12 -> 10/2 -> 1/1 invariant
   and 83.3% query reduction ratio documented in README.md match backend reality bit-for-bit.
4. Test Absence of Prohibited Legal Certainty Claims: Asserts README.md contains proper
   underwriter disclaimers and zero prohibited phrases ('coverage guaranteed',
   'policy bound automatically', 'certifies legal certainty').
5. Test Known Limitations Disclosures: Asserts presence of fictional dataset disclosure
   and non-binding decision support language.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import ast
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pytest

# Workspace Root
REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"


@pytest.fixture(scope="module")
def readme_content() -> str:
    """Loads README.md content once for the test suite."""
    assert README_PATH.exists(), f"README.md not found at {README_PATH}"
    content = README_PATH.read_text(encoding="utf-8")
    assert len(content) > 500, "README.md is unexpectedly empty or truncated"
    return content


# ==============================================================================
# 1. TEST README CODE POINTERS & FILESYSTEM INTEGRITY
# ==============================================================================

class TestReadmeCodePointers:
    """
    Validates that every file, directory, and Python symbol documented
    in README.md exists and is exported as documented.
    """

    def test_readme_file_exists(self, readme_content: str):
        """Asserts README.md exists and is non-empty."""
        assert len(readme_content) > 1000, "README.md content should be substantial (>1000 chars)"

    def test_documented_files_exist_on_disk(self, readme_content: str):
        """Asserts all core files and directories referenced in README.md exist on disk."""
        documented_paths = [
            "LICENSE",
            "requirements.txt",
            "backend/requirements.txt",
            "backend/main.py",
            "backend/domain/models.py",
            "backend/core/invalidation_engine.py",
            "backend/core/security.py",
            "backend/fixtures/golden_dataset.py",
            "backend/services/parallel_service.py",
            "backend/services/gemini_service.py",
            "backend/orchestration/workflow.py",
            "backend/orchestration/__init__.py",
            "frontend/package.json",
            "scripts/run_quality_gate.py",
            "scripts/run_rehearsal.py",
            "scripts/run_live_smoke.py",
            "scripts/run_license_audit.py",
            "scripts/verify_integrations.py",
            "tests/test_invalidation_engine.py",
            "tests/test_e2e_pipeline.py",
            "tests/test_api_endpoints.py",
            "tests/test_export_reconciliation.py",
            "tests/test_first_complete_rehearsal.py",
            "tests/test_security_and_reliability.py",
            "docs/winning",
            "docs/compliance",
        ]

        missing_paths = []
        for rel_path in documented_paths:
            full_path = REPO_ROOT / rel_path
            if not full_path.exists():
                missing_paths.append(rel_path)

        assert not missing_paths, (
            f"The following paths documented in README.md are missing on disk: {missing_paths}"
        )

    def test_documented_domain_models_exported(self):
        """Asserts backend.domain.models exports all symbols documented in README.md."""
        import backend.domain.models as domain_models

        expected_symbols = [
            "ProductionVersion",
            "CreativeUse",
            "CreativeDelta",
            "ExceptionsSchedule",
            "CounselDecision",
            "CarrierHeader",
            "PublicEvidenceSnapshot",
            "ChangeKind",
            "DecisionState",
            "DecisionStatus",
            "EvidenceStance",
        ]

        missing_symbols = [sym for sym in expected_symbols if not hasattr(domain_models, sym)]
        assert not missing_symbols, (
            f"backend.domain.models is missing documented symbols: {missing_symbols}"
        )

    def test_documented_invalidation_engine_exported(self):
        """Asserts backend.core.invalidation_engine exports InvalidationEngine and evaluate_version_delta."""
        import backend.core.invalidation_engine as inval_mod

        assert hasattr(inval_mod, "InvalidationEngine"), "InvalidationEngine missing from invalidation_engine.py"
        assert hasattr(inval_mod, "evaluate_version_delta"), "evaluate_version_delta missing from invalidation_engine.py"
        assert callable(inval_mod.evaluate_version_delta), "evaluate_version_delta must be a callable function"

        # Verify class methods exist
        assert hasattr(inval_mod.InvalidationEngine, "evaluate_invalidation")
        assert hasattr(inval_mod.InvalidationEngine, "generate_exceptions_schedule")
        assert hasattr(inval_mod.InvalidationEngine, "render_form_eo_2026_html")

    def test_documented_security_middleware_exported(self):
        """Asserts backend.core.security exports documented security and reliability abstractions."""
        import backend.core.security as sec_mod

        expected_symbols = [
            "SecretRedactingFilter",
            "CorrelationIdFilter",
            "IdempotencyKeyManager",
            "verify_counsel_token",
            "redact_secrets",
            "mask_credential",
            "CorrelationLoggingMiddleware",
            "PayloadSizeLimitMiddleware",
            "IdempotencyMiddleware",
        ]

        missing_symbols = [sym for sym in expected_symbols if not hasattr(sec_mod, sym)]
        assert not missing_symbols, (
            f"backend.core.security is missing documented symbols: {missing_symbols}"
        )

    def test_documented_golden_dataset_fixtures_exported(self):
        """Asserts backend.fixtures.golden_dataset exports golden fixture functions."""
        import backend.fixtures.golden_dataset as fixtures_mod

        expected_functions = [
            "get_golden_fixtures",
            "get_golden_expected_deltas",
            "get_v7_version",
            "get_v8_version",
        ]

        missing = [fn for fn in expected_functions if not hasattr(fixtures_mod, fn) or not callable(getattr(fixtures_mod, fn))]
        assert not missing, f"backend.fixtures.golden_dataset is missing functions: {missing}"

    def test_documented_services_exported(self):
        """Asserts backend.services exports ParallelSearchService and GeminiService."""
        import backend.services.parallel_service as p_mod
        import backend.services.gemini_service as g_mod

        assert hasattr(p_mod, "ParallelSearchService"), "ParallelSearchService missing"
        assert hasattr(g_mod, "GeminiService"), "GeminiService missing"
        assert hasattr(g_mod, "ClearanceBriefing"), "ClearanceBriefing missing"

    def test_documented_orchestration_workflow_exported(self):
        """Asserts backend.orchestration exports LienmarkWorkflow and WorkflowRunResult."""
        import backend.orchestration.workflow as wf_mod
        import backend.orchestration as orch_pkg

        assert hasattr(wf_mod, "LienmarkWorkflow"), "LienmarkWorkflow missing from workflow.py"
        assert hasattr(wf_mod, "WorkflowRunResult"), "WorkflowRunResult missing from workflow.py"
        assert hasattr(wf_mod, "WorkflowStepTrace"), "WorkflowStepTrace missing from workflow.py"

        # Package-level export
        assert hasattr(orch_pkg, "LienmarkWorkflow"), "LienmarkWorkflow missing from backend.orchestration package"
        assert hasattr(orch_pkg, "WorkflowRunResult"), "WorkflowRunResult missing from backend.orchestration package"

    def test_documented_fastapi_app_exported(self):
        """Asserts backend.main exports app instance."""
        import backend.main as main_mod

        assert hasattr(main_mod, "app"), "FastAPI app missing from backend/main.py"
        from fastapi import FastAPI
        assert isinstance(main_mod.app, FastAPI), "main.app must be a FastAPI instance"


# ==============================================================================
# 2. TEST README REPRODUCTION COMMANDS
# ==============================================================================

class TestReadmeReproductionCommands:
    """
    Validates that all CLI reproduction commands documented in README.md
    exist, are documented accurately, compile cleanly, and are executable.
    """

    REPRODUCTION_SCRIPTS = [
        "scripts/run_quality_gate.py",
        "scripts/run_rehearsal.py",
        "scripts/run_live_smoke.py",
        "scripts/run_license_audit.py",
    ]

    def test_reproduction_commands_present_in_readme(self, readme_content: str):
        """Asserts README.md explicitly documents the exact CLI command strings."""
        for script_rel in self.REPRODUCTION_SCRIPTS:
            assert script_rel in readme_content, (
                f"README.md does not document CLI reproduction command for '{script_rel}'"
            )

        # Also check additional helper commands
        assert "scripts/verify_integrations.py" in readme_content
        assert "python -m pytest tests/" in readme_content
        assert "backend.main:app" in readme_content

    def test_reproduction_scripts_exist_and_non_empty(self):
        """Asserts each reproduction script exists on disk with substantial code."""
        for script_rel in self.REPRODUCTION_SCRIPTS:
            script_path = REPO_ROOT / script_rel
            assert script_path.is_file(), f"Script '{script_rel}' does not exist on disk"
            assert script_path.stat().st_size > 1000, f"Script '{script_rel}' is unexpectedly small"

    def test_reproduction_scripts_compile_cleanly(self):
        """Asserts each reproduction script parses cleanly into valid Python AST without syntax errors."""
        for script_rel in self.REPRODUCTION_SCRIPTS:
            script_path = REPO_ROOT / script_rel
            source = script_path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(script_path))
                assert isinstance(tree, ast.Module), f"Parsed AST for {script_rel} is not a Module"
            except SyntaxError as e:
                pytest.fail(f"Syntax error in CLI script '{script_rel}': {e}")

    def test_reproduction_scripts_have_executable_entrypoints(self):
        """Asserts each reproduction script has an if __name__ == '__main__': entrypoint."""
        for script_rel in self.REPRODUCTION_SCRIPTS:
            script_path = REPO_ROOT / script_rel
            source = script_path.read_text(encoding="utf-8")
            assert '__name__' in source and '__main__' in source, (
                f"Script '{script_rel}' does not contain an if __name__ == '__main__': entrypoint"
            )

    def test_run_license_audit_script_execution(self):
        """
        Executes scripts/run_license_audit.py directly to verify reproduction
        and assert 100% OSI-approved permissive licenses.
        """
        cmd = [sys.executable, str(REPO_ROOT / "scripts" / "run_license_audit.py")]
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, f"run_license_audit.py failed with returncode {proc.returncode}:\n{proc.stderr}"
        assert "Audit Status:          PASSED" in proc.stdout or "PASSED" in proc.stdout

        # Verify emitted JSON report
        report_path = REPO_ROOT / "output" / "dependency_license_audit.json"
        assert report_path.exists(), "dependency_license_audit.json not generated"
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("compliance_status") == "PASSED"
        assert data.get("summary", {}).get("copyleft_count") == 0
        assert data.get("summary", {}).get("permissive_count") == 20


# ==============================================================================
# 3. TEST ARCHITECTURE INVARIANT VERIFICATION (12 -> 10/2 -> 1/1 & 83.3% RATIO)
# ==============================================================================

class TestArchitectureInvariantVerification:
    """
    Validates that the 12 -> 10/2 -> 1/1 mathematical conservation invariant
    and the 83.3% query reduction ratio documented in README.md match
    backend reality bit-for-bit.
    """

    def test_invariant_documented_in_readme(self, readme_content: str):
        """Asserts README.md explicitly documents 12 -> 10/2 -> 1/1 and 12 = 10 + 1 + 1."""
        assert "12 → 10/2 → 1/1" in readme_content or "12 -> 10/2 -> 1/1" in readme_content
        assert "12 = 10 + 1 + 1" in readme_content or "12 = 10 carried" in readme_content
        assert "83.3%" in readme_content, "README.md must document the 83.3% query reduction ratio"

    def test_12_prior_approvals_baseline_reality(self):
        """Verifies baseline golden fixtures contain exactly 12 items, 12 decisions, all approved in V7."""
        from backend.fixtures.golden_dataset import get_golden_fixtures

        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        assert len(v7_uses) == 12, f"Expected exactly 12 V7 creative uses, got {len(v7_uses)}"
        assert len(v8_uses) == 12, f"Expected exactly 12 V8 creative uses, got {len(v8_uses)}"
        assert len(v7_decisions) == 12, f"Expected exactly 12 V7 counsel decisions, got {len(v7_decisions)}"

        # Verify all 12 prior decisions in V7 were APPROVED
        for dec in v7_decisions:
            assert dec.status.value.lower() == "approved", f"Decision {dec.decision_id} not approved in V7"
            assert dec.applicable_version_id == "v7"

    def test_10_carried_forward_and_2_stale_reopened_reality(self):
        """Verifies InvalidationEngine evaluates exactly 10 CARRIED_FORWARD and 2 STALE claims."""
        from backend.core.invalidation_engine import InvalidationEngine
        from backend.fixtures.golden_dataset import get_golden_fixtures
        from backend.domain.models import DecisionState

        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        assert len(validity_results) == 12, f"Expected 12 validity results, got {len(validity_results)}"

        carried = [v for v in validity_results if v.state == DecisionState.CARRIED_FORWARD]
        stale = [v for v in validity_results if v.state == DecisionState.STALE]

        assert len(carried) == 10, f"Expected exactly 10 CARRIED_FORWARD claims, got {len(carried)}"
        assert len(stale) == 2, f"Expected exactly 2 STALE claims, got {len(stale)}"

        # Verify reason codes for the 2 stale claims
        stale_map = {s.stable_lineage_key: s for s in stale}
        assert "poster_noir_detective_magazine" in stale_map
        assert stale_map["poster_noir_detective_magazine"].reason_code == "CREATIVE_CONTEXT_ALTERED"

        assert "music_cue_midnight_serenade" in stale_map
        assert stale_map["music_cue_midnight_serenade"].reason_code == "EXTERNAL_EVIDENCE_SHIFT"

    def test_counsel_adjudication_1_reattested_1_exception_reality(self):
        """Verifies counsel adjudication yields 1 RE_ATTESTED and 1 EXCEPTION, conserving 12 = 10 + 1 + 1."""
        from backend.core.invalidation_engine import InvalidationEngine
        from backend.fixtures.golden_dataset import get_golden_fixtures
        from backend.domain.models import (
            CounselDecision,
            DecisionState,
            DecisionStatus,
            ReattestationRequest,
        )

        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        # Adjudicate Item 11: re-attest under public domain
        item_11_reattest = ReattestationRequest(
            decision_id="dec_v8_poster_reattest",
            stable_lineage_key="poster_noir_detective_magazine",
            version_id="v8",
            new_status=DecisionStatus.APPROVED,
            counsel_rationale="Public domain expiration confirmed via US Copyright Office Catalog (Reg. No. A-1946-992).",
            reviewer_name="Sarah Jenkins, Esq.",
        )

        # Adjudicate Item 12: leave as unresolved exception
        item_12_exception = ReattestationRequest(
            decision_id="dec_v8_music_exception",
            stable_lineage_key="music_cue_midnight_serenade",
            version_id="v8",
            new_status=DecisionStatus.REJECTED,
            counsel_rationale="Vanguard Media assignment creates sync rights dispute; cue must be replaced or licensed.",
            reviewer_name="Sarah Jenkins, Esq.",
        )

        reattestations_map = {
            "poster_noir_detective_magazine": item_11_reattest,
            "music_cue_midnight_serenade": item_12_exception,
        }

        schedule = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_blockbuster_cinema",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=validity_results,
            reattestations=reattestations_map,
            base_uses=v7_uses,
        )

        # Assert Mathematical Conservation: 12 == 10 carried + 1 re-attested + 1 exception
        assert schedule.total_claims == 12
        assert schedule.carried_forward_count == 10
        assert schedule.re_attested_count == 1
        assert schedule.unresolved_exception_count == 1
        assert schedule.reopened_count == 2

        # Conservation equation bit-for-bit check
        assert schedule.total_claims == (
            schedule.carried_forward_count
            + schedule.re_attested_count
            + schedule.unresolved_exception_count
        ), "Mathematical conservation equation 12 = 10 + 1 + 1 violated!"

    def test_83_point_3_percent_query_reduction_calculation(self):
        """Verifies mathematical query reduction ratio is exactly 83.3%."""
        total_claims = 12
        stale_claims_reinvestigated = 2
        carried_forward_claims_saved = 10

        saved_ratio = (carried_forward_claims_saved / total_claims) * 100.0
        rounded_ratio = round(saved_ratio, 1)

        assert rounded_ratio == 83.3, f"Expected 83.3% query reduction ratio, got {rounded_ratio}%"

        # Verify against RevalidationPlanner
        from backend.services.revalidation_planner import RevalidationPlanner
        from backend.core.invalidation_engine import InvalidationEngine
        from backend.fixtures.golden_dataset import get_golden_fixtures

        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        planner = RevalidationPlanner()
        plan = planner.plan_revalidation(
            validity_results=validity_results,
            target_version_id="v8",
        )

        assert plan.total_claims_evaluated == 12
        assert plan.planned_count == 2
        assert plan.skipped_count == 10
        assert len(plan.planned_requests) == 2, "Targeted queries must equal exactly 2"
        assert plan.call_reduction_percentage == 83.3


# ==============================================================================
# 4. TEST ABSENCE OF PROHIBITED LEGAL CERTAINTY CLAIMS
# ==============================================================================

class TestAbsenceOfProhibitedLegalCertaintyClaims:
    """
    Validates that README.md strictly avoids prohibited legal certainty phrases
    and contains required statutory underwriting disclaimers.
    """

    PROHIBITED_PHRASES = [
        "coverage guaranteed",
        "policy bound automatically",
        "certifies legal certainty",
        "carrier bound",
        "policy approved by insurer",
        "zero legal risk guaranteed",
        "absolute legal certainty",
    ]

    def test_readme_contains_zero_prohibited_phrases(self, readme_content: str):
        """Asserts zero occurrences of any prohibited legal certainty phrase in README.md."""
        content_lower = readme_content.lower()

        detected_phrases = []
        for phrase in self.PROHIBITED_PHRASES:
            if phrase in content_lower:
                detected_phrases.append(phrase)

        assert not detected_phrases, (
            f"README.md contains prohibited legal certainty phrase(s): {detected_phrases}"
        )

    def test_readme_contains_underwriter_disclaimer(self, readme_content: str):
        """Asserts README.md includes formal statutory underwriting disclaimers."""
        assert "LEGAL & UNDERWRITING DISCLAIMER" in readme_content, (
            "README.md missing formal LEGAL & UNDERWRITING DISCLAIMER heading"
        )
        assert "NON-BINDING" in readme_content.upper() or "NON BINDING" in readme_content.upper()
        assert "PENDING_REVIEW" in readme_content
        assert "SEPARATELY EXECUTED POLICY BINDER" in readme_content or "SURPLUS LINES CARRIER" in readme_content

    def test_codebase_outputs_contain_zero_prohibited_phrases(self):
        """Verifies Form E&O-2026 SSR HTML output contains zero prohibited phrases."""
        from backend.core.invalidation_engine import InvalidationEngine
        from backend.fixtures.golden_dataset import get_golden_fixtures
        from backend.domain.models import ReattestationRequest, DecisionStatus

        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        reattestations_map = {
            "poster_noir_detective_magazine": ReattestationRequest(
                decision_id="dec_1",
                stable_lineage_key="poster_noir_detective_magazine",
                version_id="v8",
                new_status=DecisionStatus.APPROVED,
                counsel_rationale="Public domain verified.",
            ),
            "music_cue_midnight_serenade": ReattestationRequest(
                decision_id="dec_2",
                stable_lineage_key="music_cue_midnight_serenade",
                version_id="v8",
                new_status=DecisionStatus.REJECTED,
                counsel_rationale="Rights conflict.",
            ),
        }

        schedule = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_blockbuster_cinema",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=validity_results,
            reattestations=reattestations_map,
            base_uses=v7_uses,
        )

        html = InvalidationEngine.render_form_eo_2026_html(schedule)
        html_lower = html.lower()

        for phrase in self.PROHIBITED_PHRASES:
            assert phrase not in html_lower, (
                f"Generated HTML contains prohibited legal certainty phrase: '{phrase}'"
            )


# ==============================================================================
# 5. TEST KNOWN LIMITATIONS & RESPONSIBLE AI DISCLOSURES
# ==============================================================================

class TestKnownLimitationsDisclosures:
    """
    Validates presence of fictional dataset disclosures, non-binding
    decision support language, and model containment guardrails in README.md.
    """

    def test_readme_contains_known_limitations_section(self, readme_content: str):
        """Asserts README.md has a dedicated Known Limitations section."""
        assert "Known Limitations" in readme_content, "README.md missing Known Limitations section"

    def test_fictional_dataset_disclosure_present(self, readme_content: str):
        """Asserts README.md explicitly discloses the synthetic/fictional nature of the demonstration fixtures."""
        assert "fictional" in readme_content.lower() or "synthetic" in readme_content.lower()
        assert "Shadows Over Broadway" in readme_content
        assert "Crime Detective Magazine" in readme_content or "Vanguard Media Holdings" in readme_content

    def test_non_binding_decision_support_language_present(self, readme_content: str):
        """Asserts README.md explicitly frames the system as non-binding decision support for counsel."""
        content_lower = readme_content.lower()
        assert "non-binding" in content_lower or "non binding" in content_lower
        assert "decision support" in content_lower
        assert "counsel" in content_lower

    def test_model_containment_guardrail_disclosure_present(self, readme_content: str):
        """Asserts README.md explicitly discloses model containment guardrails."""
        content_lower = readme_content.lower()
        assert "model containment" in content_lower or "containment guardrails" in content_lower
        assert "advisory" in content_lower


# ==============================================================================
# 6. TEST ARTIFACT PARITY & REPRODUCTION REPORT INTEGRITY
# ==============================================================================

class TestArtifactParityAndReproductionReportIntegrity:
    """
    Validates that reproduction output artifacts conform to required schemas,
    contain valid timestamps, and exhibit zero credential leakage.
    """

    def test_live_smoke_result_artifact_integrity(self):
        """Asserts output/live_smoke_result.json contains ISO 8601 timestamp and masked credentials."""
        result_path = REPO_ROOT / "output" / "live_smoke_result.json"
        if not result_path.exists():
            # Run live smoke runner once to generate artifact if missing
            cmd = [sys.executable, str(REPO_ROOT / "scripts" / "run_live_smoke.py")]
            subprocess.run(cmd, cwd=REPO_ROOT, check=True)

        assert result_path.exists(), "live_smoke_result.json must exist"
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("status") == "PASS"
        timestamp = data.get("last_success_timestamp")
        assert timestamp and isinstance(timestamp, str)
        # Verify ISO 8601 formatting
        assert "T" in timestamp and ("Z" in timestamp or "+" in timestamp)

        # Verify credentials masking
        audit = data.get("credentials_audit", {})
        assert audit.get("GEMINI_API_KEY") in ("CONFIGURED_MASKED", "SANDBOX_MASKED", "ABSENT_OR_SANDBOX_MASKED")
        assert audit.get("PARALLEL_API_KEY") in ("CONFIGURED_MASKED", "SANDBOX_MASKED", "ABSENT_OR_SANDBOX_MASKED")

    def test_rehearsal_report_artifact_integrity(self):
        """Asserts output/rehearsal_report.json satisfies the 12 = 10 + 1 + 1 equation and has intact ledger."""
        report_path = REPO_ROOT / "output" / "rehearsal_report.json"
        if not report_path.exists():
            cmd = [sys.executable, str(REPO_ROOT / "scripts" / "run_rehearsal.py")]
            subprocess.run(cmd, cwd=REPO_ROOT, check=True)

        assert report_path.exists(), "rehearsal_report.json must exist"
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("status") == "SUCCESS"
        recon = data.get("mathematical_reconciliation", {})
        assert recon.get("conservation_equation_satisfied") is True
        assert recon.get("total_claims") == 12
        assert recon.get("carried_forward_count") == 10
        assert recon.get("re_attested_count") == 1
        assert recon.get("unresolved_exception_count") == 1
        assert recon.get("reopened_count") == 2

        ledger = data.get("counsel_audit_trail", {})
        assert ledger.get("is_ledger_valid") is True
