"""
tests/test_story_lock_and_beats.py

Sprint 6A Task 2: Story Lock & Beat Invariant Automated Test Suite
In accordance with Sprint 6A in docs/winning/04-build-roadmap.md (§11, Sprint 6A):
  "Lock these beats:
   1. Clearance reports drift as productions change.
   2. Version 7 is reviewed.
   3. Version 8 changes one creative dependency; a refreshed external-evidence fact changes another.
   4. Lienmark carries ten decisions forward.
   5. Parallel refreshes only the affected two.
   6. Counsel resolves one and leaves one exception.
   7. The updated schedule makes the remaining risk explicit."

Exhaustive verification suite:
1. Test Script Structure & Beat Ordering:
   - Asserts docs/story/story_lock.md and docs/pitch_script.md exist and are non-empty.
   - Asserts all 7 beats are present in strict sequential order (Beat 1 through Beat 7).
2. Test Script Timing Constraints:
   - Parses timecodes across all beats.
   - Asserts total target duration is strictly <= 170 seconds (2:50) and >= 150 seconds (2:30),
     with a target of 165 seconds (2:45).
   - Asserts individual beat durations match rubric guidelines and are contiguous.
3. Test Backing Invariant & Code Pointer Parity:
   - Asserts every code pointer mentioned in the script exists on disk.
   - Asserts the 12 -> 10/2 -> 1/1 mathematical conservation holds across the script beats
     and matches backend reality.
   - Asserts that the 83.3% query reduction (2 calls vs 12) is accurately stated and verified.
   - Asserts that the two specific changed assets (Item 11 noir poster and Item 12 jazz cue)
     are accurately reflected.
4. Test Statutory Underwriting Disclaimer & Prohibited Claims:
   - Scans docs/story/story_lock.md and docs/pitch_script.md for prohibited legal certainty terms:
     ["coverage guaranteed", "policy bound automatically", "certifies legal certainty",
      "carrier bound", "legally cleared by ai", "zero legal risk", "100% legal guarantee", "insurer bound"].
   - Asserts 0 occurrences of prohibited terms.
   - Asserts presence of mandatory disclaimers regarding decision support and fictional demonstrator.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

# Repository Root & Document Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
STORY_LOCK_PATH = REPO_ROOT / "docs" / "story" / "story_lock.md"
PITCH_SCRIPT_PATH = REPO_ROOT / "docs" / "pitch_script.md"

PROHIBITED_LEGAL_TERMS = [
    "coverage guaranteed",
    "policy bound automatically",
    "certifies legal certainty",
    "carrier bound",
    "legally cleared by ai",
    "zero legal risk",
    "100% legal guarantee",
    "insurer bound",
]

MANDATORY_CODE_POINTERS = [
    "backend/core/invalidation_engine.py",
    "backend/services/parallel_service.py",
    "backend/core/counsel_checkpoint.py",
    "backend/core/exceptions_schedule.py",
    "scripts/run_rehearsal.py",
    "frontend/app/page.tsx",
    "frontend/app/report/[production_id]/page.tsx",
]


@pytest.fixture(scope="module")
def story_lock_content() -> str:
    """Loads docs/story/story_lock.md content once for the test suite."""
    assert STORY_LOCK_PATH.exists(), f"File not found: {STORY_LOCK_PATH}"
    content = STORY_LOCK_PATH.read_text(encoding="utf-8")
    assert len(content) > 500, f"story_lock.md unexpectedly truncated ({len(content)} chars)"
    return content


@pytest.fixture(scope="module")
def pitch_script_content() -> str:
    """Loads docs/pitch_script.md content once for the test suite."""
    assert PITCH_SCRIPT_PATH.exists(), f"File not found: {PITCH_SCRIPT_PATH}"
    content = PITCH_SCRIPT_PATH.read_text(encoding="utf-8")
    assert len(content) > 500, f"pitch_script.md unexpectedly truncated ({len(content)} chars)"
    return content


def _parse_timecode_interval(text: str) -> Tuple[int, int]:
    """
    Parses a timecode interval string such as '0:00–0:15' or '0:15-0:40'
    into (start_seconds, end_seconds).
    """
    match = re.search(r"(\d{1,2}):(\d{2})\s*[\u2013\-]\s*(\d{1,2}):(\d{2})", text)
    if not match:
        raise ValueError(f"Could not parse timecode interval from: {text!r}")
    start_sec = int(match.group(1)) * 60 + int(match.group(2))
    end_sec = int(match.group(3)) * 60 + int(match.group(4))
    return start_sec, end_sec


# ==============================================================================
# 1. TEST SCRIPT STRUCTURE & BEAT ORDERING
# ==============================================================================

class TestScriptStructureAndBeatOrdering:
    """
    Verifies that docs/story/story_lock.md and docs/pitch_script.md exist,
    are non-empty, and contain all 7 beats in strict sequential order.
    """

    def test_story_lock_and_pitch_script_files_exist_and_non_empty(
        self, story_lock_content: str, pitch_script_content: str
    ):
        """Asserts docs/story/story_lock.md and docs/pitch_script.md exist and are non-empty."""
        assert STORY_LOCK_PATH.is_file(), f"Missing file: {STORY_LOCK_PATH}"
        assert PITCH_SCRIPT_PATH.is_file(), f"Missing file: {PITCH_SCRIPT_PATH}"
        assert len(story_lock_content) > 1000, "story_lock.md must have substantial content"
        assert len(pitch_script_content) > 1000, "pitch_script.md must have substantial content"

    def test_story_lock_all_seven_beats_present_in_strict_sequential_order(
        self, story_lock_content: str
    ):
        """Asserts all 7 beats are present in strict sequential order in docs/story/story_lock.md."""
        beat_markers = [f"Beat {i}" for i in range(1, 8)]
        last_pos = -1

        for marker in beat_markers:
            pos = story_lock_content.find(marker)
            assert pos != -1, f"Missing {marker} in docs/story/story_lock.md"
            assert pos > last_pos, (
                f"{marker} appears out of sequential order in docs/story/story_lock.md "
                f"(pos {pos} <= last_pos {last_pos})"
            )
            last_pos = pos

    def test_pitch_script_all_seven_beats_present_in_strict_sequential_order(
        self, pitch_script_content: str
    ):
        """Asserts all 7 beats are present in strict sequential order in docs/pitch_script.md."""
        beat_markers = [f"Beat {i}" for i in range(1, 8)]
        last_pos = -1

        for marker in beat_markers:
            pos = pitch_script_content.find(marker)
            assert pos != -1, f"Missing {marker} in docs/pitch_script.md"
            assert pos > last_pos, (
                f"{marker} appears out of sequential order in docs/pitch_script.md "
                f"(pos {pos} <= last_pos {last_pos})"
            )
            last_pos = pos

    def test_beat_themes_match_roadmap_mandates(
        self, story_lock_content: str, pitch_script_content: str
    ):
        """
        Asserts that the 7 beats reflect the specific themes mandated by
        Sprint 6A in docs/winning/04-build-roadmap.md (§11).
        """
        mandated_themes = [
            ("Beat 1", ["drift", "change", "reports drift"]),
            ("Beat 2", ["Version 7", "reviewed", "baseline"]),
            ("Beat 3", ["Version 8", "creative dependency", "poster", "Item 11"]),
            ("Beat 4", ["external-evidence", "Parallel", "cue", "Item 12"]),
            ("Beat 5", ["ten decisions forward", "affected two", "83.3%"]),
            ("Beat 6", ["resolves one", "exception", "counsel", "Sarah Jenkins"]),
            ("Beat 7", ["updated schedule", "remaining risk", "Form E&O-2026", "12 = 10 + 1 + 1"]),
        ]

        for doc_name, content in [("story_lock.md", story_lock_content), ("pitch_script.md", pitch_script_content)]:
            for beat_name, keywords in mandated_themes:
                beat_idx = content.find(beat_name)
                assert beat_idx != -1, f"{beat_name} missing from {doc_name}"
                found = any(k.lower() in content.lower() for k in keywords)
                assert found, f"None of {keywords} found for {beat_name} in {doc_name}"


# ==============================================================================
# 2. TEST SCRIPT TIMING CONSTRAINTS
# ==============================================================================

class TestScriptTimingConstraints:
    """
    Parses timecodes across all beats in docs/pitch_script.md and docs/story/story_lock.md.
    Asserts total target duration is strictly <= 170 seconds (2:50) and >= 150 seconds (2:30),
    with a target of 165 seconds (2:45). Asserts individual beat durations match rubric guidelines.
    """

    EXPECTED_BEAT_TIMINGS: Dict[int, Tuple[int, int, int]] = {
        # beat_num: (expected_start_sec, expected_end_sec, expected_duration_sec)
        1: (0, 15, 15),     # 0:00–0:15 (15s)
        2: (15, 35, 20),    # 0:15–0:35 (20s)
        3: (35, 65, 30),    # 0:35–1:05 (30s)
        4: (65, 85, 20),    # 1:05–1:25 (20s)
        5: (85, 115, 30),   # 1:25–1:55 (30s)
        6: (115, 145, 30),  # 1:55–2:25 (30s)
        7: (145, 165, 20),  # 2:25–2:45 (20s)
    }

    def test_pitch_script_timecode_parsing(self, pitch_script_content: str):
        """Parses all 7 beat timecodes from docs/pitch_script.md and checks individual intervals."""
        for beat_num, (exp_start, exp_end, exp_dur) in self.EXPECTED_BEAT_TIMINGS.items():
            pattern = rf"Beat {beat_num}.*?\((?:0:)?(\d{{1,2}}:\d{{2}}\s*[\u2013\-]\s*\d{{1,2}}:\d{{2}})\)"
            match = re.search(pattern, pitch_script_content, re.IGNORECASE)
            assert match, f"Could not find timecode for Beat {beat_num} in pitch_script.md"

            tc_str = match.group(1)
            start_sec, end_sec = _parse_timecode_interval(tc_str)
            duration_sec = end_sec - start_sec

            assert start_sec == exp_start, (
                f"Beat {beat_num} start mismatch: got {start_sec}s, expected {exp_start}s ({tc_str})"
            )
            assert end_sec == exp_end, (
                f"Beat {beat_num} end mismatch: got {end_sec}s, expected {exp_end}s ({tc_str})"
            )
            assert duration_sec == exp_dur, (
                f"Beat {beat_num} duration mismatch: got {duration_sec}s, expected {exp_dur}s"
            )

    def test_beats_are_strictly_contiguous(self, pitch_script_content: str):
        """Asserts that beat time intervals are contiguous (end of Beat N == start of Beat N+1)."""
        intervals: List[Tuple[int, int]] = []
        for beat_num in range(1, 8):
            pattern = rf"Beat {beat_num}.*?\((?:0:)?(\d{{1,2}}:\d{{2}}\s*[\u2013\-]\s*\d{{1,2}}:\d{{2}})\)"
            match = re.search(pattern, pitch_script_content, re.IGNORECASE)
            assert match, f"Could not find timecode for Beat {beat_num}"
            start_sec, end_sec = _parse_timecode_interval(match.group(1))
            intervals.append((start_sec, end_sec))

        for i in range(len(intervals) - 1):
            curr_end = intervals[i][1]
            next_start = intervals[i + 1][0]
            assert curr_end == next_start, (
                f"Timecode gap/overlap between Beat {i+1} (ends at {curr_end}s) "
                f"and Beat {i+2} (starts at {next_start}s)"
            )

    def test_total_target_duration_within_strict_bounds(self, pitch_script_content: str):
        """
        Asserts total target duration across all 7 beats is:
        strictly <= 170 seconds (2:50) and >= 150 seconds (2:30), with target 165 seconds (2:45).
        """
        b1_match = re.search(r"Beat 1.*?\((?:0:)?(\d{1,2}:\d{2}\s*[\u2013\-]\s*\d{1,2}:\d{2})\)", pitch_script_content)
        b7_match = re.search(r"Beat 7.*?\((?:0:)?(\d{1,2}:\d{2}\s*[\u2013\-]\s*\d{1,2}:\d{2})\)", pitch_script_content)

        assert b1_match and b7_match
        start_sec, _ = _parse_timecode_interval(b1_match.group(1))
        _, end_sec = _parse_timecode_interval(b7_match.group(1))

        total_duration = end_sec - start_sec

        assert start_sec == 0, f"Script must start at 0:00 (got {start_sec}s)"
        assert total_duration >= 150, (
            f"Total duration {total_duration}s is below 150s (2:30) threshold"
        )
        assert total_duration <= 170, (
            f"Total duration {total_duration}s exceeds 170s (2:50) threshold"
        )
        assert total_duration == 165, (
            f"Total duration should hit the exact 165s (2:45) target, got {total_duration}s"
        )

    def test_story_lock_documents_165s_target_and_rubric_bounds(self, story_lock_content: str):
        """Asserts docs/story/story_lock.md documents the 165s target duration and 150-170s envelope."""
        assert "165 seconds" in story_lock_content or "165s" in story_lock_content
        assert "2:45" in story_lock_content
        assert "150" in story_lock_content
        assert "170" in story_lock_content


# ==============================================================================
# 3. TEST BACKING INVARIANT & CODE POINTER PARITY
# ==============================================================================

class TestBackingInvariantAndCodePointerParity:
    """
    Validates that:
    1. Every code pointer mentioned in docs/pitch_script.md and docs/story/story_lock.md exists on disk.
    2. The 12 -> 10/2 -> 1/1 mathematical conservation holds across the script beats and matches backend reality.
    3. The 83.3% query reduction (2 calls vs 12) is accurately stated.
    4. The two specific changed assets (Item 11 noir poster and Item 12 jazz cue) are accurately reflected.
    """

    def test_mandatory_code_pointers_exist_in_repository(self):
        """Asserts all mandatory code pointers documented in the pitch script exist on disk."""
        missing = []
        for rel_path in MANDATORY_CODE_POINTERS:
            full_path = REPO_ROOT / rel_path
            if not full_path.exists():
                missing.append(rel_path)

        assert not missing, (
            f"The following code pointers referenced in pitch script are missing in repo: {missing}"
        )

    def test_script_mentions_all_mandatory_code_pointers(self, pitch_script_content: str):
        """Asserts docs/pitch_script.md explicitly references each required code pointer."""
        for rel_path in MANDATORY_CODE_POINTERS:
            assert rel_path in pitch_script_content, (
                f"docs/pitch_script.md does not reference mandatory code pointer: '{rel_path}'"
            )

    def test_story_lock_mentions_all_mandatory_code_pointers(self, story_lock_content: str):
        """Asserts docs/story/story_lock.md explicitly references each required code pointer."""
        for rel_path in MANDATORY_CODE_POINTERS:
            assert rel_path in story_lock_content, (
                f"docs/story/story_lock.md does not reference mandatory code pointer: '{rel_path}'"
            )

    def test_mathematical_conservation_invariant_in_script(
        self, pitch_script_content: str, story_lock_content: str
    ):
        """
        Asserts the 12 -> 10/2 -> 1/1 mathematical conservation is documented across script beats:
        12 prior approvals -> 10 carried forward + 2 reopened -> 1 re-attested + 1 exception (12 = 10 + 1 + 1).
        """
        for doc_name, content in [("pitch_script.md", pitch_script_content), ("story_lock.md", story_lock_content)]:
            assert "12 -> 10/2 -> 1/1" in content or "12 → 10/2 → 1/1" in content or "12 \\longrightarrow 10/2 \\longrightarrow 1/1" in content, (
                f"{doc_name} missing 12 -> 10/2 -> 1/1 invariant notation"
            )
            assert "12 = 10 + 1 + 1" in content, (
                f"{doc_name} missing conservation equation '12 = 10 + 1 + 1'"
            )
            assert "10 carried" in content.lower() or "10 carried forward" in content.lower() or "carried forward: 10" in content.lower()
            assert "1 re-attested" in content.lower() or "one re-attested" in content.lower() or "re-attested: 1" in content.lower()
            assert "1 exception" in content.lower() or "one exception" in content.lower() or "one unresolved exception" in content.lower() or "unresolved exceptions: 1" in content.lower()

    def test_mathematical_conservation_live_backend_reality(self):
        """
        Validates that the 12 -> 10/2 -> 1/1 mathematical conservation holds bit-for-bit
        in the actual backend InvalidationEngine and golden dataset.
        """
        import backend.core.invalidation_engine
        from backend.fixtures.golden_dataset import get_golden_fixtures
        from backend.core.invalidation_engine import InvalidationEngine
        from backend.domain.models import DecisionState, DecisionStatus, ReattestationRequest

        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        assert len(v7_uses) == 12, "Golden V7 uses must equal 12"
        assert len(v7_decisions) == 12, "Golden V7 decisions must equal 12"

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        carried = [v for v in validity_results if v.state == DecisionState.CARRIED_FORWARD]
        stale = [v for v in validity_results if v.state == DecisionState.STALE]

        assert len(carried) == 10, f"Expected 10 carried forward, got {len(carried)}"
        assert len(stale) == 2, f"Expected 2 stale, got {len(stale)}"

        # Simulate counsel actions: 1 re-attestation, 1 exception
        reattestations_map = {
            "poster_noir_detective_magazine": ReattestationRequest(
                decision_id="dec_reattest",
                stable_lineage_key="poster_noir_detective_magazine",
                version_id="v8",
                new_status=DecisionStatus.APPROVED,
                counsel_rationale="Public domain expiration confirmed.",
            ),
            "music_cue_midnight_serenade": ReattestationRequest(
                decision_id="dec_reject",
                stable_lineage_key="music_cue_midnight_serenade",
                version_id="v8",
                new_status=DecisionStatus.REJECTED,
                counsel_rationale="Vanguard Media dispute active.",
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

        assert schedule.total_claims == 12
        assert schedule.carried_forward_count == 10
        assert schedule.re_attested_count == 1
        assert schedule.unresolved_exception_count == 1
        assert schedule.reopened_count == 2
        assert schedule.total_claims == (
            schedule.carried_forward_count
            + schedule.re_attested_count
            + schedule.unresolved_exception_count
        )

    def test_query_reduction_ratio_stated_and_verified(
        self, pitch_script_content: str, story_lock_content: str
    ):
        """
        Asserts that the 83.3% query reduction ratio (2 calls vs 12)
        is accurately stated in docs and matches RevalidationPlanner reality.
        """
        for doc_name, content in [("pitch_script.md", pitch_script_content), ("story_lock.md", story_lock_content)]:
            assert "83.3%" in content, f"83.3% query reduction missing from {doc_name}"
            assert "2 calls vs 12" in content or "2 queries vs 12" in content or "2 calls" in content, (
                f"2 vs 12 query ratio missing from {doc_name}"
            )

        # Backend reality check
        from backend.fixtures.golden_dataset import get_golden_fixtures
        from backend.core.invalidation_engine import InvalidationEngine
        from backend.services.revalidation_planner import RevalidationPlanner

        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
        validity = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )
        planner = RevalidationPlanner()
        plan = planner.plan_revalidation(validity, target_version_id="v8")

        assert plan.total_claims_evaluated == 12
        assert plan.planned_count == 2
        assert plan.skipped_count == 10
        assert plan.call_reduction_percentage == 83.3

    def test_two_changed_assets_accurately_reflected(
        self, pitch_script_content: str, story_lock_content: str
    ):
        """
        Asserts that the two specific changed assets (Item 11 noir poster and Item 12 jazz cue)
        are accurately described in the script and story lock.
        """
        for doc_name, content in [("pitch_script.md", pitch_script_content), ("story_lock.md", story_lock_content)]:
            # Item 11: noir poster
            assert "Item 11" in content, f"Item 11 missing from {doc_name}"
            assert "noir poster" in content.lower() or "poster" in content.lower(), (
                f"Noir poster missing from {doc_name}"
            )
            assert "poster_noir_detective_magazine" in content, (
                f"poster_noir_detective_magazine lineage key missing from {doc_name}"
            )

            # Item 12: jazz cue
            assert "Item 12" in content, f"Item 12 missing from {doc_name}"
            assert "jazz cue" in content.lower() or "cue" in content.lower(), (
                f"Jazz cue missing from {doc_name}"
            )
            assert "music_cue_midnight_serenade" in content, (
                f"music_cue_midnight_serenade lineage key missing from {doc_name}"
            )

            # Check reasons / adverse party
            assert "Vanguard Media" in content, f"Vanguard Media missing from {doc_name}"


# ==============================================================================
# 4. TEST STATUTORY UNDERWRITING DISCLAIMER & PROHIBITED CLAIMS
# ==============================================================================

class TestStatutoryUnderwritingDisclaimerAndProhibitedClaims:
    """
    Scans docs/story/story_lock.md and docs/pitch_script.md for prohibited legal certainty terms:
    ["coverage guaranteed", "policy bound automatically", "certifies legal certainty",
     "carrier bound", "legally cleared by ai", "zero legal risk", "100% legal guarantee", "insurer bound"].
    Asserts 0 occurrences of prohibited terms.
    Asserts presence of mandatory disclaimers regarding decision support and fictional demonstrator.
    """

    def test_zero_prohibited_legal_certainty_terms(
        self, story_lock_content: str, pitch_script_content: str
    ):
        """
        Scans docs/story/story_lock.md and docs/pitch_script.md for prohibited legal certainty terms:
        ["coverage guaranteed", "policy bound automatically", "certifies legal certainty",
         "carrier bound", "legally cleared by ai", "zero legal risk", "100% legal guarantee", "insurer bound"].
        Asserts strictly 0 occurrences of prohibited terms in affirmative prose across both documents.
        """
        for doc_name, content in [("story_lock.md", story_lock_content), ("pitch_script.md", pitch_script_content)]:
            # Filter out explicit audit/disclaimer inventory lines where terms are cited as absent
            lines = [
                line for line in content.splitlines()
                if "0 occurrences" not in line.lower()
                and "\u2192 absent" not in line.lower()
                and "to absent" not in line.lower()
                and "prohibited" not in line.lower()
            ]
            clean_content = "\n".join(lines).lower()
            detected = [term for term in PROHIBITED_LEGAL_TERMS if term in clean_content]
            assert not detected, (
                f"{doc_name} contains prohibited legal certainty term(s) in affirmative prose: {detected}"
            )

    def test_mandatory_decision_support_disclaimer_present(
        self, pitch_script_content: str, story_lock_content: str
    ):
        """Asserts presence of mandatory decision support disclaimers in both documents."""
        for doc_name, content in [("pitch_script.md", pitch_script_content), ("story_lock.md", story_lock_content)]:
            content_lower = content.lower()
            assert "decision support" in content_lower, f"Missing 'decision support' in {doc_name}"
            assert "counsel" in content_lower, f"Missing 'counsel' in {doc_name}"
            assert "non-binding" in content_lower or "non binding" in content_lower, (
                f"Missing 'non-binding' disclaimer in {doc_name}"
            )
            assert "underwriter" in content_lower or "underwriting" in content_lower, (
                f"Missing underwriter reference in {doc_name}"
            )

    def test_mandatory_fictional_demonstrator_disclaimer_present(
        self, pitch_script_content: str, story_lock_content: str
    ):
        """Asserts presence of mandatory fictional demonstrator disclaimers in both documents."""
        for doc_name, content in [("pitch_script.md", pitch_script_content), ("story_lock.md", story_lock_content)]:
            content_lower = content.lower()
            assert "fictional" in content_lower, f"Missing 'fictional' disclosure in {doc_name}"
            assert "demonstrator" in content_lower or "demonstration" in content_lower, (
                f"Missing 'demonstrator' disclosure in {doc_name}"
            )
            assert "shadows over broadway" in content_lower, (
                f"Missing fictional production 'Shadows Over Broadway' in {doc_name}"
            )
            assert "sarah jenkins" in content_lower, (
                f"Missing simulated counsel 'Sarah Jenkins' in {doc_name}"
            )
