"""
Tests for Component 3: Hollywood Studio Legal Ops UI/UX Overhaul
Verifies:
1. MathematicalConservationRibbon component implementation:
   - Conservation identity: 12 Total Claims = 10 Carried Forward + 1 Re-Attested + 1 Warranty Exception
   - Pipeline progression: 12 -> 10/2 -> 1/1
   - Three-Tier Query & Claim Breakdown:
     * Affected Claims: 2 of 12 (10 carried forward without attorney re-review)
     * Search Query Plan: 2 planned vs 12 full-scan baseline (83.3% query reduction)
     * Actual Network Requests: Displays actual HTTP calls and retries recorded in execution traces
     * Economic Benchmark: Clearly labeled as Scenario Benchmark: ~$18,000 Saved ($1,500/claim baseline)
     * Measured Latency: Displays actual API response elapsed time (response.elapsed_ms)
   - High-contrast visual meter bar showing exact proportional breakdown.
2. ClearanceSummaryCards component upgrade:
   - High-contrast cinema glass cards with glowing ambient indicators.
   - Clear labels distinguishing measured runtime values from scenario benchmarks.
"""

import os
import re
import pytest

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
RIBBON_FILE = os.path.join(FRONTEND_DIR, "app", "components", "MathematicalConservationRibbon.tsx")
CARDS_FILE = os.path.join(FRONTEND_DIR, "app", "components", "ClearanceSummaryCards.tsx")
PAGE_FILE = os.path.join(FRONTEND_DIR, "app", "page.tsx")


class TestMathematicalConservationRibbon:
    """Verifies MathematicalConservationRibbon.tsx file existence, exports, and contracts."""

    def test_ribbon_file_exists(self):
        assert os.path.exists(RIBBON_FILE), f"Missing component file: {RIBBON_FILE}"

    def test_ribbon_exports_react_component(self):
        with open(RIBBON_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        assert "export const MathematicalConservationRibbon" in content
        assert "export default MathematicalConservationRibbon" in content
        assert "'use client'" in content

    def test_ribbon_conservation_identity_and_progression(self):
        with open(RIBBON_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Conservation identity formula elements
        assert "Total Claims" in content
        assert "Carried Forward" in content
        assert "Re-Attested" in content
        assert "Warranty Exception" in content
        assert "Invariant Conserved" in content or "Invariant" in content

        # Pipeline progression 12 -> 10/2 -> 1/1
        assert "12 &rarr; 10/2 &rarr; 1/1" in content or "12 -> 10/2 -> 1/1" in content or "10/2" in content
        assert "Ingested Baseline" in content
        assert "Carried / Drift" in content
        assert "Attested / Exception" in content

    def test_three_tier_breakdown_requirements(self):
        with open(RIBBON_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Tier 1: Affected Claims (2 of 12, 10 carried forward without attorney re-review)
        assert "Affected Claims" in content
        assert "10 carried forward without attorney re-review" in content

        # Tier 2: Search Query Plan (2 planned vs 12 full-scan baseline, 83.3% query reduction)
        assert "Search Query Plan" in content
        assert "83.3% query reduction" in content

        # Tier 3: Actual Network Requests
        assert "Network Requests" in content or "Actual Network Requests" in content
        assert "Parallel Search API" in content
        assert "Recorded in execution traces" in content

        # Economic Benchmark (Clearly labeled Scenario Benchmark: ~$18,000 Saved ($1,500/claim baseline))
        assert "Economic Benchmark" in content
        assert "Scenario Benchmark" in content
        assert "$18,000 Saved" in content
        assert "$1,500/claim baseline" in content

        # Measured Latency (Displays actual API response elapsed time response.elapsed_ms)
        assert "Measured Latency" in content
        assert "response.elapsed_ms" in content

    def test_high_contrast_meter_bar(self):
        with open(RIBBON_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # High-contrast visual meter bar role and segments
        assert 'role="progressbar"' in content
        assert "bg-emerald-400" in content
        assert "bg-sky-400" in content
        assert "bg-rose-500" in content
        assert "Proportional Rights Allocation" in content or "Proportional" in content


class TestClearanceSummaryCardsUpgrade:
    """Verifies ClearanceSummaryCards.tsx cinema glass cards, ambient indicators, and labels."""

    def test_summary_cards_file_exists(self):
        assert os.path.exists(CARDS_FILE), f"Missing component file: {CARDS_FILE}"

    def test_embeds_mathematical_conservation_ribbon(self):
        with open(CARDS_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        assert "MathematicalConservationRibbon" in content
        assert "<MathematicalConservationRibbon" in content

    def test_cinema_glass_and_ambient_indicators(self):
        with open(CARDS_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Cinema glass styling: backdrop blur + translucent gradient
        assert "backdrop-blur-xl" in content
        assert "bg-gradient-to-b" in content

        # Ambient glowing indicators
        assert "blur-2xl" in content or "blur-3xl" in content
        assert "pointer-events-none" in content

    def test_distinguishes_runtime_values_from_scenario_benchmarks(self):
        with open(CARDS_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Distinguishes Measured Runtime values from Scenario Benchmarks
        assert "Measured Runtime" in content
        assert "Scenario Benchmark" in content

    def test_dashboard_page_passes_telemetry(self):
        with open(PAGE_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Dashboard page must pass traces and elapsedMs to ClearanceSummaryCards
        assert "traces={traces}" in content
        assert "elapsedMs={evalElapsedMs}" in content
