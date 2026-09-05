#!/usr/bin/env python3
"""
scripts/verify_submission_consistency.py

Sprint 7A Task 2: Submission Consistency & Artifact Parity Validator
In accordance with Sprint 7A in docs/winning/04-build-roadmap.md (§12, Sprint 7A):
  "Cross-check every claim across: Hosted application, Public repository, README,
   Demo video, Devpost description, Architecture diagram, Test/evidence pack.
   Remove or qualify anything that cannot be verified."

Five Authoritative Verification Gates:
  1. GATE_1: Cross-Artifact Narrative & Metadata Parity (Title, Tagline, Track Category)
  2. GATE_2: Mathematical Invariant Parity Across All 7 Surfaces (12 = 10 + 1 + 1, 83.3%, Items 11 & 12)
  3. GATE_3: Pinned Release Candidate & Policy Lock Parity (RC-1, FROZEN, E&O-2026.1-DEVPOST, SHA match)
  4. GATE_4: Documentation Pointers & Reproduction Command Truth (100% file existence, script availability)
  5. GATE_5: Statutory Disclaimers & Prohibited Legal Certainty Audit (Zero forbidden claims, mandatory disclaimer)

Emits: `output/submission_consistency_report.json` with status 'CONSISTENT'.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Windows console encoding
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
DOCS_DIR = REPO_ROOT / "docs"

# Exact Invariant Constants
CANONICAL_TITLE = "Lienmark — Clearance Change Control for E&O"
CANONICAL_TAGLINE = (
    "Detect clearance drift, selectively revalidate affected evidence, "
    "and keep sign-offs aligned with every production version."
)
CANONICAL_TRACK = "Parallel Track ($15,000 Prize Pool)"
CANONICAL_POLICY_VERSION = "E&O-2026.1-DEVPOST"
CANONICAL_CONSERVATION_LAW = "12 = 10 + 1 + 1"
CANONICAL_QUERY_REDUCTION = "83.3%"
CANONICAL_RC_COMMIT = "e022a4c8042c9552a307357cc138acfdd8552522"

ITEM_11_TOKENS = ["poster", "scene 42"]
ITEM_12_TOKENS = ["midnight serenade", "scene 18"]

# 20 Prohibited Legal Certainty Clauses
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


def render_box(title: str, lines: List[str], width: int = 86) -> str:
    """Renders a formatted ASCII box with a title and content lines."""
    border_top = "┌" + "─" * (width - 2) + "┐"
    border_bot = "└" + "─" * (width - 2) + "┘"
    title_line = f"│  {title}" + " " * max(0, width - 5 - len(title)) + "│"
    sep = "├" + "─" * (width - 2) + "┤"

    body_lines = []
    for line in lines:
        if len(line) > width - 6:
            line = line[: width - 9] + "..."
        body_lines.append(f"│  {line}" + " " * max(0, width - 5 - len(line)) + "│")

    return "\n".join([border_top, title_line, sep] + body_lines + [border_bot])


# ==============================================================================
# GATE 1: CROSS-ARTIFACT NARRATIVE & METADATA PARITY
# ==============================================================================

def audit_gate_1_metadata_parity() -> Dict[str, Any]:
    discrepancies: List[str] = []
    details: List[str] = []

    # 1. Title parity
    readme_path = REPO_ROOT / "README.md"
    devpost_path = REPO_ROOT / "docs" / "submission" / "devpost_submission.md"
    pitch_path = REPO_ROOT / "docs" / "pitch_script.md"
    layout_path = REPO_ROOT / "frontend" / "app" / "layout.tsx"

    for path, name in [
        (readme_path, "README.md"),
        (devpost_path, "docs/submission/devpost_submission.md"),
        (pitch_path, "docs/pitch_script.md"),
        (layout_path, "frontend/app/layout.tsx"),
    ]:
        if not path.exists():
            discrepancies.append(f"File missing for title check: {name}")
            continue
        content = path.read_text(encoding="utf-8")
        if CANONICAL_TITLE not in content:
            discrepancies.append(f"Title '{CANONICAL_TITLE}' missing from {name}")
        else:
            details.append(f"Title verified in {name}")

    # 2. Tagline parity
    header_component = REPO_ROOT / "frontend" / "app" / "components" / "DashboardHeader.tsx"
    backend_main = REPO_ROOT / "backend" / "main.py"

    for path, name in [
        (readme_path, "README.md"),
        (devpost_path, "docs/submission/devpost_submission.md"),
        (header_component, "frontend/app/components/DashboardHeader.tsx"),
        (backend_main, "backend/main.py (dashboard header)"),
    ]:
        if not path.exists():
            discrepancies.append(f"File missing for tagline check: {name}")
            continue
        content = path.read_text(encoding="utf-8")
        if CANONICAL_TAGLINE not in content:
            discrepancies.append(f"Tagline missing from {name}")
        else:
            details.append(f"Tagline verified in {name}")

    # 3. Prize track designation parity
    compliance_doc = REPO_ROOT / "docs" / "compliance" / "01_stage1_eligibility_gate.md"
    freeze_compliance_doc = REPO_ROOT / "docs" / "compliance" / "24_sprint_6c_feature_freeze_and_manifest.md"

    for path, name in [
        (readme_path, "README.md"),
        (devpost_path, "docs/submission/devpost_submission.md"),
        (compliance_doc, "docs/compliance/01_stage1_eligibility_gate.md"),
        (freeze_compliance_doc, "docs/compliance/24_sprint_6c_feature_freeze_and_manifest.md"),
    ]:
        if not path.exists():
            discrepancies.append(f"File missing for track check: {name}")
            continue
        content = path.read_text(encoding="utf-8")
        if CANONICAL_TRACK not in content:
            discrepancies.append(f"Prize track '{CANONICAL_TRACK}' missing from {name}")
        else:
            details.append(f"Prize track verified in {name}")

    status = "PASSED" if not discrepancies else "FAILED"
    return {
        "gate_id": "GATE_1_METADATA_PARITY",
        "name": "Cross-Artifact Narrative & Metadata Parity",
        "status": status,
        "discrepancies": discrepancies,
        "details": details,
    }


# ==============================================================================
# GATE 2: MATHEMATICAL INVARIANT PARITY ACROSS ALL 7 SURFACES
# ==============================================================================

def audit_gate_2_invariants() -> Dict[str, Any]:
    discrepancies: List[str] = []
    details: List[str] = []

    # 7 Surfaces for 12 = 10 + 1 + 1 conservation law
    surfaces: List[Tuple[Path, str]] = [
        (REPO_ROOT / "README.md", "Surface 1: README.md"),
        (REPO_ROOT / "docs" / "submission" / "devpost_submission.md", "Surface 2: Devpost Submission"),
        (REPO_ROOT / "docs" / "pitch_script.md", "Surface 3: Pitch Script"),
        (REPO_ROOT / "docs" / "provenance" / "public_media_manifest.md", "Surface 4: Public Media Manifest"),
        (REPO_ROOT / "scripts" / "run_rehearsal.py", "Surface 5: Rehearsal Harness"),
        (REPO_ROOT / "backend" / "fixtures" / "golden_dataset.py", "Surface 6: Domain Fixtures"),
        (REPO_ROOT / "docs" / "story" / "story_lock.md", "Surface 7: Story Lock"),
    ]

    for path, name in surfaces:
        if not path.exists():
            discrepancies.append(f"Surface missing for conservation check: {name}")
            continue
        content = path.read_text(encoding="utf-8")
        if CANONICAL_CONSERVATION_LAW not in content:
            discrepancies.append(f"Conservation law '{CANONICAL_CONSERVATION_LAW}' missing from {name}")
        else:
            details.append(f"Conservation law '{CANONICAL_CONSERVATION_LAW}' verified in {name}")

    # 83.3% query reduction ratio consistency
    query_docs = [
        (REPO_ROOT / "README.md", "README.md"),
        (REPO_ROOT / "docs" / "submission" / "devpost_submission.md", "Devpost Submission"),
        (REPO_ROOT / "docs" / "pitch_script.md", "Pitch Script"),
        (REPO_ROOT / "scripts" / "run_rehearsal.py", "Rehearsal Harness"),
    ]

    for path, name in query_docs:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        if CANONICAL_QUERY_REDUCTION not in content:
            discrepancies.append(f"Query reduction '{CANONICAL_QUERY_REDUCTION}' missing from {name}")
        else:
            details.append(f"Query reduction '{CANONICAL_QUERY_REDUCTION}' verified in {name}")

    # Item 11 & Item 12 drift parity
    drift_docs = [
        (REPO_ROOT / "README.md", "README.md"),
        (REPO_ROOT / "docs" / "submission" / "devpost_submission.md", "Devpost Submission"),
        (REPO_ROOT / "docs" / "pitch_script.md", "Pitch Script"),
        (REPO_ROOT / "backend" / "fixtures" / "golden_dataset.py", "Domain Fixtures"),
    ]

    for path, name in drift_docs:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8").lower()
        has_item_11 = any(t in content for t in ITEM_11_TOKENS)
        has_item_12 = any(t in content for t in ITEM_12_TOKENS)

        if not has_item_11:
            discrepancies.append(f"Item 11 drifted claim missing or misidentified in {name}")
        if not has_item_12:
            discrepancies.append(f"Item 12 drifted claim missing or misidentified in {name}")
        if has_item_11 and has_item_12:
            details.append(f"Drifted claims (Item 11 & Item 12) accurately identified in {name}")

    status = "PASSED" if not discrepancies else "FAILED"
    return {
        "gate_id": "GATE_2_MATHEMATICAL_INVARIANTS",
        "name": "Mathematical Invariant Parity Across All 7 Surfaces",
        "status": status,
        "discrepancies": discrepancies,
        "details": details,
    }


# ==============================================================================
# GATE 3: PINNED RELEASE CANDIDATE & POLICY LOCK PARITY
# ==============================================================================

def audit_gate_3_release_and_policy() -> Dict[str, Any]:
    discrepancies: List[str] = []
    details: List[str] = []

    freeze_file = OUTPUT_DIR / "feature_freeze_manifest.json"
    if not freeze_file.exists():
        discrepancies.append(f"Missing feature freeze manifest: {freeze_file}")
        return {
            "gate_id": "GATE_3_POLICY_AND_RELEASE_LOCK",
            "name": "Pinned Release Candidate & Policy Lock Parity",
            "status": "FAILED",
            "discrepancies": discrepancies,
            "details": details,
        }

    freeze_data = json.loads(freeze_file.read_text(encoding="utf-8"))

    # Status check
    if freeze_data.get("status") != "FROZEN":
        discrepancies.append(f"Feature freeze status is '{freeze_data.get('status')}', expected 'FROZEN'")
    else:
        details.append("Feature freeze manifest status is 'FROZEN'")

    # Pinned commit SHA
    manifest_commit = freeze_data.get("pinned_commit")
    if not manifest_commit or len(manifest_commit) != 40:
        discrepancies.append(f"Invalid or missing pinned commit in manifest: {manifest_commit}")
    else:
        details.append(f"Pinned commit SHA verified in manifest: {manifest_commit}")

    # Devpost submission commit SHA match
    devpost_path = REPO_ROOT / "docs" / "submission" / "devpost_submission.md"
    devpost_content = devpost_path.read_text(encoding="utf-8")
    if manifest_commit not in devpost_content:
        discrepancies.append(f"Pinned commit SHA '{manifest_commit}' not referenced in devpost submission")
    else:
        details.append(f"Pinned commit SHA in devpost submission matches manifest exactly ({manifest_commit})")

    # Policy version uniform reference
    policy_check_locations: List[Tuple[Path, str]] = [
        (REPO_ROOT / "backend" / "domain" / "models.py", "backend/domain/models.py"),
        (REPO_ROOT / "backend" / "core" / "invalidation_engine.py", "backend/core/invalidation_engine.py"),
        (REPO_ROOT / "frontend" / "app" / "components" / "DashboardHeader.tsx", "frontend/app/components/DashboardHeader.tsx"),
        (REPO_ROOT / "frontend" / "app" / "layout.tsx", "frontend/app/layout.tsx"),
        (REPO_ROOT / "README.md", "README.md"),
        (devpost_path, "docs/submission/devpost_submission.md"),
        (REPO_ROOT / "docs" / "compliance" / "24_sprint_6c_feature_freeze_and_manifest.md", "docs/compliance/24_sprint_6c_feature_freeze_and_manifest.md"),
    ]

    for path, name in policy_check_locations:
        if not path.exists():
            discrepancies.append(f"File missing for policy check: {name}")
            continue
        content = path.read_text(encoding="utf-8")
        if CANONICAL_POLICY_VERSION not in content:
            discrepancies.append(f"Policy version '{CANONICAL_POLICY_VERSION}' missing from {name}")
        else:
            details.append(f"Policy version '{CANONICAL_POLICY_VERSION}' verified in {name}")

    status = "PASSED" if not discrepancies else "FAILED"
    return {
        "gate_id": "GATE_3_POLICY_AND_RELEASE_LOCK",
        "name": "Pinned Release Candidate & Policy Lock Parity",
        "status": status,
        "discrepancies": discrepancies,
        "details": details,
    }


# ==============================================================================
# GATE 4: DOCUMENTATION POINTERS & REPRODUCTION COMMAND TRUTH
# ==============================================================================

def audit_gate_4_pointers_and_commands() -> Dict[str, Any]:
    discrepancies: List[str] = []
    details: List[str] = []

    # Check mandatory reproduction scripts exist
    for script_rel in MANDATORY_SCRIPTS:
        script_path = REPO_ROOT / script_rel
        if not script_path.exists():
            discrepancies.append(f"Mandatory reproduction script does not exist: {script_rel}")
        else:
            details.append(f"Verified executable script exists: {script_rel}")

    # Scan README and Devpost submission for referenced files
    target_docs = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "submission" / "devpost_submission.md",
    ]

    referenced_files: Set[str] = set()

    for doc in target_docs:
        if not doc.exists():
            continue
        content = doc.read_text(encoding="utf-8")

        # Match markdown file links: [label](path)
        md_links = re.findall(r"\[.*?\]\(([\w\.\-\/]+)\)", content)
        for link in md_links:
            if not link.startswith("http") and not link.startswith("#") and not link.startswith("mailto:"):
                clean_link = link.split("#")[0].split("?")[0]
                if clean_link:
                    referenced_files.add(clean_link)

        # Match backtick paths: `path/to/file.ext`
        code_paths = re.findall(r"`([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]+)`", content)
        for cp in code_paths:
            if "/" in cp and not cp.startswith("http"):
                referenced_files.add(cp)

        # Match python script invocations: python scripts/xxx.py
        py_invokes = re.findall(r"python\s+([\w\.\-\/]+\.py)", content)
        for pi in py_invokes:
            referenced_files.add(pi)

    # Check all collected files exist on disk
    for rel_path_str in sorted(referenced_files):
        rel_path = Path(rel_path_str)
        abs_path = REPO_ROOT / rel_path

        if not abs_path.exists():
            # Only flag actual project code and doc paths
            if any(rel_path_str.startswith(prefix) for prefix in ["backend/", "frontend/", "scripts/", "tests/", "docs/", "output/"]) or rel_path_str in ["LICENSE", "requirements.txt"]:
                discrepancies.append(f"Referenced file does not exist on disk: {rel_path_str}")
        else:
            details.append(f"Referenced path exists: {rel_path_str}")

    status = "PASSED" if not discrepancies else "FAILED"
    return {
        "gate_id": "GATE_4_DOCUMENTATION_POINTERS",
        "name": "Documentation Pointers & Reproduction Command Truth",
        "status": status,
        "discrepancies": discrepancies,
        "details": details,
        "total_paths_verified": len(referenced_files),
    }


# ==============================================================================
# GATE 5: STATUTORY DISCLAIMERS & ZERO PROHIBITED LEGAL CLAIMS
# ==============================================================================

def audit_gate_5_disclaimers_and_phrases() -> Dict[str, Any]:
    discrepancies: List[str] = []
    details: List[str] = []

    target_artifacts = [
        (REPO_ROOT / "docs" / "submission" / "devpost_submission.md", "docs/submission/devpost_submission.md"),
        (REPO_ROOT / "README.md", "README.md"),
        (REPO_ROOT / "docs" / "pitch_script.md", "docs/pitch_script.md"),
    ]

    for path, name in target_artifacts:
        if not path.exists():
            discrepancies.append(f"File missing for disclaimer/prohibited phrase audit: {name}")
            continue

        raw_content = path.read_text(encoding="utf-8")
        clean_content = raw_content.lower()

        # 1. Prohibited phrases check
        detected_phrases = []
        for phrase in PROHIBITED_LEGAL_TERMS:
            pattern = r"\b" + re.escape(phrase) + r"\b"
            matches = list(re.finditer(pattern, clean_content))

            for match in matches:
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
                    detected_phrases.append(f"'{phrase}' (context: ...{context.strip()}...)")

        if detected_phrases:
            for dp in detected_phrases:
                discrepancies.append(f"Prohibited legal certainty phrase found in {name}: {dp}")
        else:
            details.append(f"Zero prohibited phrases detected in {name} (0/{len(PROHIBITED_LEGAL_TERMS)} matched)")

        # 2. Mandatory statutory underwriting disclaimer check
        disclaimer_markers = [
            "statutory notice",
            "statutory legal & underwriting disclaimer",
            "non-binding",
            "decision support",
            "does not provide legal advice",
            "no artifact generated by lienmark constitutes",
        ]

        has_disclaimer = any(marker in clean_content for marker in disclaimer_markers)
        if not has_disclaimer:
            discrepancies.append(f"Mandatory statutory underwriting disclaimer missing from {name}")
        else:
            details.append(f"Mandatory statutory underwriting disclaimer confirmed present in {name}")

    status = "PASSED" if not discrepancies else "FAILED"
    return {
        "gate_id": "GATE_5_STATUTORY_DISCLAIMERS",
        "name": "Statutory Disclaimers & Prohibited Legal Certainty Audit",
        "status": status,
        "discrepancies": discrepancies,
        "details": details,
        "prohibited_phrases_checked": len(PROHIBITED_LEGAL_TERMS),
    }


# ==============================================================================
# MASTER RUNNER & REPORT GENERATOR
# ==============================================================================

def run_submission_consistency_audit() -> Dict[str, Any]:
    t0 = time.perf_counter()

    gate_1 = audit_gate_1_metadata_parity()
    gate_2 = audit_gate_2_invariants()
    gate_3 = audit_gate_3_release_and_policy()
    gate_4 = audit_gate_4_pointers_and_commands()
    gate_5 = audit_gate_5_disclaimers_and_phrases()

    elapsed = round(time.perf_counter() - t0, 3)

    gates = [gate_1, gate_2, gate_3, gate_4, gate_5]
    all_discrepancies: List[str] = []
    for g in gates:
        all_discrepancies.extend(g["discrepancies"])

    overall_status = "CONSISTENT" if len(all_discrepancies) == 0 else "INCONSISTENT"

    manifest_commit = CANONICAL_RC_COMMIT
    freeze_file = OUTPUT_DIR / "feature_freeze_manifest.json"
    if freeze_file.exists():
        try:
            freeze_data = json.loads(freeze_file.read_text(encoding="utf-8"))
            manifest_commit = freeze_data.get("pinned_commit", manifest_commit)
        except Exception:
            pass

    report = {
        "status": overall_status,
        "discrepancies_count": len(all_discrepancies),
        "discrepancies": all_discrepancies,
        "canonical_invariants": {
            "title": CANONICAL_TITLE,
            "tagline": CANONICAL_TAGLINE,
            "track": CANONICAL_TRACK,
            "policy_version": CANONICAL_POLICY_VERSION,
            "conservation_law": CANONICAL_CONSERVATION_LAW,
            "query_reduction_ratio": CANONICAL_QUERY_REDUCTION,
            "pinned_rc_commit": manifest_commit,
        },
        "gates": gates,
        "elapsed_seconds": elapsed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verified_by": "Linda Singwane (lx-singw), Lead Systems Architect & Verification Suite",
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = OUTPUT_DIR / "submission_consistency_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def main() -> int:
    print("\n" + "=" * 86)
    print("  LIENMARK SUBMISSION CONSISTENCY & ARTIFACT PARITY AUDITOR")
    print("  Sprint 7A Task 2: Automated Cross-Check Across All 7 Surfaces")
    print("=" * 86 + "\n")

    report = run_submission_consistency_audit()

    for g in report["gates"]:
        icon = "✓" if g["status"] == "PASSED" else "✗"
        print(f"  [{icon}] {g['gate_id']}: {g['name']} ({g['status']})")
        if g["discrepancies"]:
            for d in g["discrepancies"]:
                print(f"      - DISCREPANCY: {d}")

    summary_lines = [
        f"Overall Submission Status : {report['status']}",
        f"Total Gates Evaluated     : {len(report['gates'])}",
        f"Discrepancies Detected    : {report['discrepancies_count']}",
        f"Execution Time            : {report['elapsed_seconds']}s",
        f"Report Written To         : output/submission_consistency_report.json",
    ]

    print("\n" + render_box("SUBMISSION CONSISTENCY AUDIT SUMMARY", summary_lines) + "\n")

    return 0 if report["status"] == "CONSISTENT" else 1


if __name__ == "__main__":
    sys.exit(main())
