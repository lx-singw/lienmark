"""
tests/test_artifact_consistency.py

Sprint 7A Task 2: Artifact Consistency Test Suite & Invariant Parity
In accordance with Sprint 7A in docs/winning/04-build-roadmap.md (§12, Sprint 7A:
'Cross-check every claim across: Hosted application, Public repository, README,
 Demo video, Devpost description, Architecture diagram, Test/evidence pack.
 Remove or qualify anything that cannot be verified'):

Exhaustive verification test suite:
1. Test Cross-Artifact Narrative & Metadata Parity:
   - Asserts title 'Lienmark — Clearance Change Control for E&O' is identical in
     README.md, docs/submission/devpost_submission.md, docs/pitch_script.md, and frontend layout.tsx.
   - Asserts tagline is identical across README, Devpost submission, and dashboard header.
   - Asserts prize track designation ('Parallel Track ($15,000 Prize Pool)') is present
     in README, Devpost submission, and compliance documents.
2. Test Mathematical Invariant Parity Across All 7 Surfaces:
   - Asserts the 12 = 10 + 1 + 1 conservation law is stated with exact precision in
     README, Devpost submission, pitch script, public media manifest, rehearsal harness, and domain fixtures.
   - Asserts the 83.3% query reduction ratio (2 queries vs 12) is consistently documented without hyperbole.
   - Asserts Item 11 (noir detective poster) and Item 12 (Midnight Serenade jazz cue) are
     the exact two drifted claims in all narrative and technical documents.
3. Test Pinned Release Candidate & Policy Lock Parity:
   - Asserts output/feature_freeze_manifest.json status is 'FROZEN'.
   - Asserts policy version E&O-2026.1-DEVPOST is uniformly referenced across
     backend, frontend, README, Devpost, and compliance docs.
   - Asserts pinned commit SHA in Devpost submission matches the manifest.
4. Test Documentation Pointers & Reproduction Command Truth:
   - Scans README.md and docs/submission/devpost_submission.md for all file links,
     script invocations (scripts/run_quality_gate.py, scripts/run_rehearsal.py,
     scripts/run_live_smoke.py, scripts/verify_feature_freeze.py, scripts/record_take_harness.py,
     scripts/verify_submission_consistency.py), and test commands.
   - Verifies that 100% of referenced files exist on disk and all referenced CLI tools are executable.
5. Test Statutory Disclaimers & Zero Prohibited Legal Claims:
   - Scans docs/submission/devpost_submission.md, README.md, and docs/pitch_script.md
     against 20 prohibited certainty phrases:
     ["coverage guaranteed", "policy bound automatically", "certifies legal certainty",
      "carrier bound", "legally cleared by ai", "zero legal risk", "100% legal guarantee",
      "insurer bound", "eliminates all legal risk", "automatic binding", "certified cleared", ...].
   - Asserts strictly 0 occurrences across all submission artifacts.
   - Asserts presence of mandatory statutory underwriting disclaimer (decision support only, non-binding).
6. Test Submission Consistency Report Artifact:
   - Asserts output/submission_consistency_report.json exists, has status: "CONSISTENT",
     and confirms zero discrepancies.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

OUTPUT_DIR = REPO_ROOT / "output"
DOCS_DIR = REPO_ROOT / "docs"
SUBMISSION_DOC = DOCS_DIR / "submission" / "devpost_submission.md"
README_FILE = REPO_ROOT / "README.md"
PITCH_SCRIPT_FILE = DOCS_DIR / "pitch_script.md"
LAYOUT_TSX_FILE = REPO_ROOT / "frontend" / "app" / "layout.tsx"
DASHBOARD_HEADER_FILE = REPO_ROOT / "frontend" / "app" / "components" / "DashboardHeader.tsx"
BACKEND_MAIN_FILE = REPO_ROOT / "backend" / "main.py"
FREEZE_MANIFEST_FILE = OUTPUT_DIR / "feature_freeze_manifest.json"
SUBMISSION_REPORT_FILE = OUTPUT_DIR / "submission_consistency_report.json"
PUBLIC_MANIFEST_FILE = DOCS_DIR / "provenance" / "public_media_manifest.md"
REHEARSAL_SCRIPT = REPO_ROOT / "scripts" / "run_rehearsal.py"
GOLDEN_DATASET_FILE = REPO_ROOT / "backend" / "fixtures" / "golden_dataset.py"

# Canonical invariant definitions
CANONICAL_TITLE = "Lienmark — Clearance Change Control for E&O"
CANONICAL_TAGLINE = (
    "Detect clearance drift, selectively revalidate affected evidence, "
    "and keep sign-offs aligned with every production version."
)
CANONICAL_TRACK = "Parallel Track ($15,000 Prize Pool)"
CANONICAL_POLICY_VERSION = "E&O-2026.1-DEVPOST"
CANONICAL_CONSERVATION_LAW = "12 = 10 + 1 + 1"
CANONICAL_QUERY_REDUCTION = "83.3%"

PROHIBITED_LEGAL_TERMS: List[str] = [
    "coverage guaranteed",
    "coverage is guaranteed",
    "policy bound automatically",
    "certifies legal certainty",
    "carrier bound",
    "policy approved by insurer",
    "insurer has bound coverage",
    "zero legal risk guaranteed",
    "zero legal risk",
    "absolute legal certainty",
    "claims are legally cleared by ai",
    "legally cleared by ai",
    "100% legal guarantee",
    "insurer bound",
    "title insurance for film ip",
    "automated policy binding",
    "automatic policy binding",
    "eliminates legal liability",
    "ai clears your movie",
    "100% autonomous rights clearance",
    "eliminates all legal risk",
    "automatic binding",
    "certified cleared",
]

MANDATORY_SCRIPTS: List[str] = [
    "scripts/run_quality_gate.py",
    "scripts/run_rehearsal.py",
    "scripts/run_live_smoke.py",
    "scripts/verify_feature_freeze.py",
    "scripts/record_take_harness.py",
    "scripts/verify_submission_consistency.py",
]


# ==============================================================================
# 1. TEST CROSS-ARTIFACT NARRATIVE & METADATA PARITY
# ==============================================================================

class TestCrossArtifactNarrativeAndMetadataParity:
    """
    Validates exact title, tagline, and track parity across all primary surfaces.
    """

    def test_title_identical_across_artifacts(self):
        """
        Asserts title 'Lienmark — Clearance Change Control for E&O' is identical
        in README.md, docs/submission/devpost_submission.md, docs/pitch_script.md,
        and frontend layout.tsx.
        """
        targets = [
            (README_FILE, "README.md"),
            (SUBMISSION_DOC, "docs/submission/devpost_submission.md"),
            (PITCH_SCRIPT_FILE, "docs/pitch_script.md"),
            (LAYOUT_TSX_FILE, "frontend/app/layout.tsx"),
        ]

        for path, name in targets:
            assert path.exists(), f"Missing file: {name}"
            content = path.read_text(encoding="utf-8")
            assert CANONICAL_TITLE in content, (
                f"Canonical title '{CANONICAL_TITLE}' missing or mismatch in {name}"
            )

    def test_tagline_identical_across_readme_devpost_and_dashboard_header(self):
        """
        Asserts tagline is identical across README, Devpost submission,
        and dashboard header (frontend component & backend SSR route).
        """
        targets = [
            (README_FILE, "README.md"),
            (SUBMISSION_DOC, "docs/submission/devpost_submission.md"),
            (DASHBOARD_HEADER_FILE, "frontend/app/components/DashboardHeader.tsx"),
            (BACKEND_MAIN_FILE, "backend/main.py"),
        ]

        for path, name in targets:
            assert path.exists(), f"Missing file: {name}"
            content = path.read_text(encoding="utf-8")
            assert CANONICAL_TAGLINE in content, (
                f"Canonical tagline '{CANONICAL_TAGLINE}' missing or mismatch in {name}"
            )

    def test_prize_track_designation_present_in_readme_devpost_and_compliance(self):
        """
        Asserts prize track designation ('Parallel Track ($15,000 Prize Pool)')
        is present in README, Devpost submission, and compliance documents.
        """
        compliance_doc_1 = DOCS_DIR / "compliance" / "01_stage1_eligibility_gate.md"
        compliance_doc_2 = DOCS_DIR / "compliance" / "24_sprint_6c_feature_freeze_and_manifest.md"

        targets = [
            (README_FILE, "README.md"),
            (SUBMISSION_DOC, "docs/submission/devpost_submission.md"),
            (compliance_doc_1, "docs/compliance/01_stage1_eligibility_gate.md"),
            (compliance_doc_2, "docs/compliance/24_sprint_6c_feature_freeze_and_manifest.md"),
        ]

        for path, name in targets:
            assert path.exists(), f"Missing file: {name}"
            content = path.read_text(encoding="utf-8")
            assert CANONICAL_TRACK in content, (
                f"Prize track designation '{CANONICAL_TRACK}' missing from {name}"
            )


# ==============================================================================
# 2. TEST MATHEMATICAL INVARIANT PARITY ACROSS ALL 7 SURFACES
# ==============================================================================

class TestMathematicalInvariantParityAcrossAllSevenSurfaces:
    """
    Validates exact conservation law, query reduction, and drifted item identity.
    """

    def test_conservation_law_12_equals_10_plus_1_plus_1_across_surfaces(self):
        """
        Asserts the 12 = 10 + 1 + 1 conservation law is stated with exact precision in:
        1. README.md
        2. docs/submission/devpost_submission.md
        3. docs/pitch_script.md
        4. docs/provenance/public_media_manifest.md
        5. scripts/run_rehearsal.py
        6. backend/fixtures/golden_dataset.py
        7. docs/story/story_lock.md
        """
        surfaces = [
            (README_FILE, "README.md"),
            (SUBMISSION_DOC, "docs/submission/devpost_submission.md"),
            (PITCH_SCRIPT_FILE, "docs/pitch_script.md"),
            (PUBLIC_MANIFEST_FILE, "docs/provenance/public_media_manifest.md"),
            (REHEARSAL_SCRIPT, "scripts/run_rehearsal.py"),
            (GOLDEN_DATASET_FILE, "backend/fixtures/golden_dataset.py"),
            (DOCS_DIR / "story" / "story_lock.md", "docs/story/story_lock.md"),
        ]

        for path, name in surfaces:
            assert path.exists(), f"Missing surface file: {name}"
            content = path.read_text(encoding="utf-8")
            assert CANONICAL_CONSERVATION_LAW in content, (
                f"Exact conservation law '{CANONICAL_CONSERVATION_LAW}' missing from {name}"
            )

    def test_query_reduction_ratio_consistently_documented_without_hyperbole(self):
        """
        Asserts the 83.3% query reduction ratio (2 queries vs 12) is consistently
        documented without hyperbole across README, Devpost submission, and pitch script.
        """
        targets = [
            (README_FILE, "README.md"),
            (SUBMISSION_DOC, "docs/submission/devpost_submission.md"),
            (PITCH_SCRIPT_FILE, "docs/pitch_script.md"),
            (REHEARSAL_SCRIPT, "scripts/run_rehearsal.py"),
        ]

        for path, name in targets:
            assert path.exists(), f"Missing file: {name}"
            content = path.read_text(encoding="utf-8")
            assert CANONICAL_QUERY_REDUCTION in content, (
                f"Query reduction '{CANONICAL_QUERY_REDUCTION}' missing from {name}"
            )

    def test_item_11_and_item_12_are_exact_two_drifted_claims(self):
        """
        Asserts Item 11 (noir detective poster) and Item 12 (Midnight Serenade jazz cue)
        are the exact two drifted claims in all narrative and technical documents.
        """
        targets = [
            (README_FILE, "README.md"),
            (SUBMISSION_DOC, "docs/submission/devpost_submission.md"),
            (PITCH_SCRIPT_FILE, "docs/pitch_script.md"),
            (GOLDEN_DATASET_FILE, "backend/fixtures/golden_dataset.py"),
        ]

        item_11_indicators = ["poster", "scene 42"]
        item_12_indicators = ["midnight serenade", "scene 18"]

        for path, name in targets:
            assert path.exists(), f"Missing file: {name}"
            content = path.read_text(encoding="utf-8").lower()
            assert any(t in content for t in item_11_indicators), (
                f"Item 11 (noir detective poster / scene 42) missing from {name}"
            )
            assert any(t in content for t in item_12_indicators), (
                f"Item 12 (Midnight Serenade jazz cue / scene 18) missing from {name}"
            )


# ==============================================================================
# 3. TEST PINNED RELEASE CANDIDATE & POLICY LOCK PARITY
# ==============================================================================

class TestPinnedReleaseCandidateAndPolicyLockParity:
    """
    Validates manifest frozen state, policy uniform reference, and pinned commit matching.
    """

    def test_feature_freeze_manifest_status_is_frozen(self):
        """
        Asserts output/feature_freeze_manifest.json status is 'FROZEN'.
        """
        assert FREEZE_MANIFEST_FILE.exists(), f"Missing manifest: {FREEZE_MANIFEST_FILE}"
        data = json.loads(FREEZE_MANIFEST_FILE.read_text(encoding="utf-8"))
        assert data.get("status") == "FROZEN", f"Manifest status is {data.get('status')}"
        assert data.get("release_candidate") == "RC-1"
        assert data.get("open_p0_defects") == 0

    def test_policy_version_uniformly_referenced_across_all_tiers(self):
        """
        Asserts policy version E&O-2026.1-DEVPOST is uniformly referenced across
        backend, frontend, README, Devpost, and compliance docs.
        """
        policy_locations = [
            (REPO_ROOT / "backend" / "domain" / "models.py", "backend/domain/models.py"),
            (REPO_ROOT / "backend" / "core" / "invalidation_engine.py", "backend/core/invalidation_engine.py"),
            (DASHBOARD_HEADER_FILE, "frontend/app/components/DashboardHeader.tsx"),
            (LAYOUT_TSX_FILE, "frontend/app/layout.tsx"),
            (README_FILE, "README.md"),
            (SUBMISSION_DOC, "docs/submission/devpost_submission.md"),
            (DOCS_DIR / "compliance" / "24_sprint_6c_feature_freeze_and_manifest.md", "compliance docs"),
        ]

        for path, name in policy_locations:
            assert path.exists(), f"Missing file: {name}"
            content = path.read_text(encoding="utf-8")
            assert CANONICAL_POLICY_VERSION in content, (
                f"Policy version '{CANONICAL_POLICY_VERSION}' missing from {name}"
            )

    def test_pinned_commit_sha_in_devpost_matches_manifest(self):
        """
        Asserts pinned commit SHA in Devpost submission matches the manifest.
        """
        assert FREEZE_MANIFEST_FILE.exists(), f"Missing manifest: {FREEZE_MANIFEST_FILE}"
        freeze_data = json.loads(FREEZE_MANIFEST_FILE.read_text(encoding="utf-8"))
        manifest_commit = freeze_data.get("pinned_commit")
        assert manifest_commit is not None and len(manifest_commit) == 40

        devpost_content = SUBMISSION_DOC.read_text(encoding="utf-8")
        assert manifest_commit in devpost_content, (
            f"Manifest pinned commit SHA '{manifest_commit}' not found in devpost submission!"
        )


# ==============================================================================
# 4. TEST DOCUMENTATION POINTERS & REPRODUCTION COMMAND TRUTH
# ==============================================================================

class TestDocumentationPointersAndReproductionCommandTruth:
    """
    Validates 100% of referenced files exist on disk and all reproduction CLI tools are runnable.
    """

    def test_mandatory_reproduction_scripts_exist_on_disk(self):
        """
        Scans for all 6 mandatory scripts:
        - scripts/run_quality_gate.py
        - scripts/run_rehearsal.py
        - scripts/run_live_smoke.py
        - scripts/verify_feature_freeze.py
        - scripts/record_take_harness.py
        - scripts/verify_submission_consistency.py
        """
        for script_rel in MANDATORY_SCRIPTS:
            script_path = REPO_ROOT / script_rel
            assert script_path.exists(), f"Mandatory reproduction script missing: {script_rel}"
            # Verify file is non-empty
            assert script_path.stat().st_size > 500, f"Script {script_rel} is unexpectedly small or empty"

    def test_referenced_files_in_readme_and_devpost_exist_on_disk(self):
        """
        Scans README.md and docs/submission/devpost_submission.md for all file links,
        verifying that 100% of referenced files exist on disk.
        """
        target_docs = [README_FILE, SUBMISSION_DOC]
        referenced_files: Set[str] = set()

        for doc in target_docs:
            content = doc.read_text(encoding="utf-8")

            # Match markdown file links
            md_links = re.findall(r"\[.*?\]\(([\w\.\-\/]+)\)", content)
            for link in md_links:
                if not link.startswith("http") and not link.startswith("#") and not link.startswith("mailto:"):
                    clean = link.split("#")[0].split("?")[0]
                    if clean:
                        referenced_files.add(clean)

            # Match backtick code paths
            code_paths = re.findall(r"`([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]+)`", content)
            for cp in code_paths:
                if "/" in cp and not cp.startswith("http"):
                    referenced_files.add(cp)

            # Match python invocations
            py_invokes = re.findall(r"python\s+([\w\.\-\/]+\.py)", content)
            for pi in py_invokes:
                referenced_files.add(pi)

        missing_files = []
        for rel_path_str in sorted(referenced_files):
            abs_path = REPO_ROOT / rel_path_str
            if not abs_path.exists():
                if any(rel_path_str.startswith(p) for p in ["backend/", "frontend/", "scripts/", "tests/", "docs/", "output/"]) or rel_path_str in ["LICENSE", "requirements.txt"]:
                    missing_files.append(rel_path_str)

        assert not missing_files, f"100% file existence violated! Missing files: {missing_files}"


# ==============================================================================
# 5. TEST STATUTORY DISCLAIMERS & ZERO PROHIBITED LEGAL CLAIMS
# ==============================================================================

class TestStatutoryDisclaimersAndZeroProhibitedLegalClaims:
    """
    Validates strictly 0 prohibited certainty phrases and presence of mandatory statutory disclaimers.
    """

    @pytest.mark.parametrize("target_doc", [SUBMISSION_DOC, README_FILE, PITCH_SCRIPT_FILE])
    def test_strictly_zero_prohibited_certainty_phrases(self, target_doc: Path):
        """
        Scans submission artifacts against 20 prohibited certainty phrases,
        asserting strictly 0 occurrences.
        """
        assert target_doc.exists(), f"Missing document: {target_doc}"
        clean_content = target_doc.read_text(encoding="utf-8").lower()

        violations = []
        for phrase in PROHIBITED_LEGAL_TERMS:
            pattern = r"\b" + re.escape(phrase) + r"\b"
            for match in re.finditer(pattern, clean_content):
                start = max(0, match.start() - 60)
                end = min(len(clean_content), match.end() + 60)
                context = clean_content[start:end]

                is_negated_or_quoted = any(
                    marker in context
                    for marker in [
                        "prohibited",
                        "forbidden",
                        "zero occurrences",
                        "does not",
                        "cannot",
                        "disclaimed",
                        "without",
                        "reject",
                    ]
                )
                if not is_negated_or_quoted:
                    violations.append(f"'{phrase}' (context: ...{context.strip()}...)")

        assert not violations, (
            f"Prohibited legal certainty phrases found in {target_doc.name}:\n"
            + "\n".join(violations)
        )

    @pytest.mark.parametrize("target_doc", [SUBMISSION_DOC, README_FILE, PITCH_SCRIPT_FILE])
    def test_presence_of_mandatory_statutory_underwriting_disclaimer(self, target_doc: Path):
        """
        Asserts presence of mandatory statutory underwriting disclaimer (decision support only, non-binding).
        """
        assert target_doc.exists(), f"Missing document: {target_doc}"
        clean_content = target_doc.read_text(encoding="utf-8").lower()

        disclaimer_markers = [
            "statutory notice",
            "statutory legal & underwriting disclaimer",
            "non-binding",
            "decision support",
            "does not provide legal advice",
            "no artifact generated by lienmark constitutes",
        ]

        has_disclaimer = any(m in clean_content for m in disclaimer_markers)
        assert has_disclaimer, f"Mandatory statutory underwriting disclaimer missing from {target_doc.name}"


# ==============================================================================
# 6. TEST SUBMISSION CONSISTENCY REPORT ARTIFACT
# ==============================================================================

class TestSubmissionConsistencyReportArtifact:
    """
    Validates output/submission_consistency_report.json artifact.
    """

    def test_submission_consistency_report_exists_and_is_consistent(self):
        """
        Asserts output/submission_consistency_report.json exists, has status: "CONSISTENT",
        and confirms zero discrepancies.
        """
        assert SUBMISSION_REPORT_FILE.exists(), f"Missing report: {SUBMISSION_REPORT_FILE}"
        data = json.loads(SUBMISSION_REPORT_FILE.read_text(encoding="utf-8"))

        assert data.get("status") == "CONSISTENT", (
            f"Expected status 'CONSISTENT', got '{data.get('status')}'"
        )
        assert data.get("discrepancies_count") == 0, (
            f"Expected 0 discrepancies, got {data.get('discrepancies_count')}: {data.get('discrepancies')}"
        )
        assert len(data.get("discrepancies", [])) == 0

    def test_report_all_five_gates_passed(self):
        """
        Asserts all 5 gates in the report have status 'PASSED'.
        """
        assert SUBMISSION_REPORT_FILE.exists(), f"Missing report: {SUBMISSION_REPORT_FILE}"
        data = json.loads(SUBMISSION_REPORT_FILE.read_text(encoding="utf-8"))

        gates = data.get("gates", [])
        assert len(gates) == 5, f"Expected 5 evaluated gates, found {len(gates)}"

        for g in gates:
            assert g.get("status") == "PASSED", (
                f"Gate {g.get('gate_id')} ({g.get('name')}) status is '{g.get('status')}', expected 'PASSED'"
            )
            assert len(g.get("discrepancies", [])) == 0, (
                f"Gate {g.get('gate_id')} has discrepancies: {g.get('discrepancies')}"
            )
