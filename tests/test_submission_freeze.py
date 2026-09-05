"""
tests/test_submission_freeze.py

Sprint 7C Task 2: Submission Freeze Automated Test Suite
In accordance with Sprint 7C in docs/winning/04-build-roadmap.md (§12, Sprint 7C)
and §18 (September 8 Submission-Freeze Gate):
  "September 8 submission-freeze gate:
   - All artifacts are consistent, accessible logged out, pinned to the demonstrated
     commit/deployment, and frozen by 18:00."

Exhaustive verification suite:
1. Test Gate 1: Devpost Form Fields Completeness (13 mandatory sections)
2. Test Gate 2: Parallel Track Eligibility & Selection (Parallel Search API runtime integration & $15K track)
3. Test Gate 3: Complete 27-Point Devpost Submission Checklist (all 27 items from playbook §10 satisfied)
4. Test Gate 4: Release Candidate Pin & Zero P0 Defects (RC-1, E&O-2026.1-DEVPOST, commit SHA, 0 P0 defects)
5. Test Gate 5: Final Video Timing & Subtitle Synchronization (165s within [150s, 170s], WebVTT & SRT)
6. Test Gate 6: License & Zero Secret Invariants (100% OSI-approved permissive, zero unmasked secrets)
7. Test Gate 7: Multi-Tier Verification Audit Reports Validation (Quality Gate, Rehearsal, Consistency, Cold Judge)
8. Test Gate 8: Roadmap Retrospective & Final Regression Baseline (Phases 0-7 complete, 27 compliance docs)
9. Test Persistent Artifacts (submission_freeze_manifest.json and submission_freeze_report.json)
10. Test Master Freeze Runner CLI execution

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.verify_submission_freeze import (
    audit_gate_1_devpost_form_fields,
    audit_gate_2_parallel_track_eligibility,
    audit_gate_3_27_point_checklist,
    audit_gate_4_release_candidate_and_zero_p0,
    audit_gate_5_video_timing_and_subtitles,
    audit_gate_6_license_and_zero_secrets,
    audit_gate_7_multi_tier_verification_reports,
    audit_gate_8_roadmap_and_final_regression,
    CANONICAL_TITLE,
    CANONICAL_TAGLINE,
    CANONICAL_TRACK,
    CANONICAL_HOSTED_URL,
    CANONICAL_REPO_URL,
    RELEASE_CANDIDATE,
    FROZEN_POLICY_VERSION,
    BASE_RC_COMMIT_SHA,
)


class TestSubmissionFreeze:
    """Test suite for Sprint 7C Submission Freeze verification."""

    def test_gate_1_devpost_form_fields(self):
        """Verify all 13 mandatory Devpost submission sections are present and non-empty."""
        result = audit_gate_1_devpost_form_fields()
        assert result["status"] == "PASSED", f"Gate 1 failed: {result['discrepancies']}"
        assert result["total_sections"] == 13
        assert result["passed_sections"] == 13
        assert len(result["discrepancies"]) == 0

    def test_gate_2_parallel_track_eligibility(self):
        """Verify Parallel Track ($15,000 Prize Pool) and Parallel Search API integration."""
        result = audit_gate_2_parallel_track_eligibility()
        assert result["status"] == "PASSED", f"Gate 2 failed: {result['discrepancies']}"
        assert len(result["discrepancies"]) == 0

    def test_gate_3_27_point_checklist(self):
        """Verify the complete 27-point Devpost submission checklist from playbook §10."""
        result = audit_gate_3_27_point_checklist()
        assert result["status"] == "PASSED", f"Gate 3 failed: {result['discrepancies']}"
        assert result["total_items"] == 27, f"Expected 27 items, got {result['total_items']}"
        assert result["passed_items"] == 27, f"Expected 27 passed items, got {result['passed_items']}"
        assert len(result["discrepancies"]) == 0

        # Verify specific critical checklist items
        item_names = {item["id"]: item["name"] for item in result["items"]}
        assert 1 in item_names
        assert 2 in item_names
        assert 11 in item_names  # Parallel Search API
        assert 13 in item_names  # <= 3:00 window
        assert 20 in item_names  # Pinned commit & deployment
        assert 27 in item_names  # Statutory Underwriting Notice

    def test_gate_4_release_candidate_and_zero_p0(self):
        """Verify Release Candidate RC-1, policy version, and zero open P0 defects."""
        result = audit_gate_4_release_candidate_and_zero_p0()
        assert result["status"] == "PASSED", f"Gate 4 failed: {result['discrepancies']}"
        assert result["release_candidate"] == RELEASE_CANDIDATE
        assert result["policy_version"] == FROZEN_POLICY_VERSION
        assert result["base_rc_commit"] == BASE_RC_COMMIT_SHA
        assert result["open_p0_defects"] == 0
        assert len(result["discrepancies"]) == 0

    def test_gate_5_video_timing_and_subtitles(self):
        """Verify pitch script target duration (165s within [150s, 170s]) and subtitle tracks."""
        result = audit_gate_5_video_timing_and_subtitles()
        assert result["status"] == "PASSED", f"Gate 5 failed: {result['discrepancies']}"
        assert result["target_duration_seconds"] == 165.0
        assert len(result["discrepancies"]) == 0

    def test_gate_6_license_and_zero_secrets(self):
        """Verify OSI-approved MIT license and zero unmasked secrets across the repo."""
        result = audit_gate_6_license_and_zero_secrets()
        assert result["status"] == "PASSED", f"Gate 6 failed: {result['discrepancies']}"
        assert len(result["discrepancies"]) == 0

    def test_gate_7_multi_tier_verification_reports(self):
        """Verify all multi-tier verification reports exist with passing statuses."""
        result = audit_gate_7_multi_tier_verification_reports()
        assert result["status"] == "PASSED", f"Gate 7 failed: {result['discrepancies']}"
        reports = result["reports"]
        assert "quality_gate" in reports
        assert reports["quality_gate"]["status"] == "PASSED"
        assert "rehearsal" in reports
        assert reports["rehearsal"]["conservation_equation_satisfied"] is True
        assert "submission_consistency" in reports
        assert reports["submission_consistency"]["status"] == "CONSISTENT"
        assert "cold_judge" in reports
        assert reports["cold_judge"]["status"] == "COLD_JUDGE_PASSED"
        assert len(result["discrepancies"]) == 0

    def test_gate_8_roadmap_and_final_regression(self):
        """Verify all Phases 0-7 are certified, 27 compliance docs exist, and regression checks pass."""
        result = audit_gate_8_roadmap_and_final_regression()
        assert result["status"] == "PASSED", f"Gate 8 failed: {result['discrepancies']}"
        assert result["phases_certified"] == 8  # Phase 0 through Phase 7
        assert result["compliance_docs_count"] >= 27  # All compliance docs present
        assert len(result["discrepancies"]) == 0

    def test_submission_freeze_report_artifacts(self):
        """Verify output/submission_freeze_manifest.json and report.json exist and are valid."""
        manifest_path = REPO_ROOT / "output" / "submission_freeze_manifest.json"
        report_path = REPO_ROOT / "output" / "submission_freeze_report.json"
        assert manifest_path.exists(), "submission_freeze_manifest.json missing"
        assert report_path.exists(), "submission_freeze_report.json missing"

        m_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert m_data["status"] == "SUBMISSION_FROZEN_READY"
        assert m_data["release_candidate"] == RELEASE_CANDIDATE
        assert m_data["frozen_policy_version"] == FROZEN_POLICY_VERSION
        assert m_data["total_checklist_items"] == 27
        assert m_data["passed_checklist_items"] == 27
        assert m_data["open_p0_defects"] == 0
        assert m_data["discrepancies"] == 0
        assert "Linda Singwane" in m_data["certified_by"]

        r_data = json.loads(report_path.read_text(encoding="utf-8"))
        assert r_data["status"] == "SUBMISSION_FROZEN"
        assert r_data["release_candidate"] == RELEASE_CANDIDATE
        assert r_data["frozen_policy_version"] == FROZEN_POLICY_VERSION
        assert r_data["total_checklist_items"] == 27
        assert r_data["passed_checklist_items"] == 27
        assert r_data["discrepancies"] == 0

    def test_verify_submission_freeze_script_execution(self):
        """Verify python scripts/verify_submission_freeze.py executes with exit code 0."""
        script_path = REPO_ROOT / "scripts" / "verify_submission_freeze.py"
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, f"Script failed with exit {proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
        assert "SUBMISSION_FROZEN_READY" in proc.stdout
        assert "27/27 Satisfied" in proc.stdout
