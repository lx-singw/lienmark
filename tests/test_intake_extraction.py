"""
test_intake_extraction.py

Sprint 2.3 Milestone B Acceptance Gate test suite.
Validates end-to-end multimodal screenplay intake pipeline:
1. Primary extraction + Self-reflection pass over sample_script.pdf extracts
   all 4 benchmark claims (Clair de Lune, Apollo 11, Coca-Cola, Marlboro).
2. Confidentiality trimming guarantees zero plot/emotional spoilers (<= 20 words).
3. Adversarial prompt injection in sample_script_adversarial.pdf is trapped
   as suspicious_embedded_instruction without suppressing legitimate claims.
4. Production Baseline Engine locks an immutable revision snapshot.
"""

from __future__ import annotations

import os
from typing import List
import pytest

from backend.agents.intake.agent import IntakeAgent
from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.intake.confidentiality import ConfidentialityFilter
from backend.agents.intake.injection_detector import scan_script_for_injections
from backend.agents.intake.self_reflection import SelfReflectionService
from backend.agents.intake.trap_handler import reconcile_extracted_claims
from backend.core.baseline import ProductionBaselineEngine
from backend.core.baseline_types import CreativeUseNode, ParserMetadata
from backend.parsers.pdf_parser import PdfScreenplayParser
from backend.storage.baseline_store import InMemoryBaselineStore
from backend.storage.schema import Claim


@pytest.fixture
def sample_script_path() -> str:
    """Returns absolute path to sample_script.pdf fixture."""
    path = os.path.abspath(os.path.join("demo", "sample_script.pdf"))
    assert os.path.exists(path), f"Fixture not found: {path}"
    return path


@pytest.fixture
def adversarial_script_path() -> str:
    """Returns absolute path to sample_script_adversarial.pdf fixture."""
    path = os.path.abspath(os.path.join("demo", "sample_script_adversarial.pdf"))
    assert os.path.exists(path), f"Fixture not found: {path}"
    return path


@pytest.mark.asyncio
async def _run_intake_and_reflection(script_text: str) -> List[Claim]:
    """Runs primary intake and self-reflection reconciliation pipeline."""
    agent = IntakeAgent(use_fallback=True)
    primary_output = await agent.extract_claims(script_text)
    primary_claims: List[Claim] = [
        Claim(
            claim_id=c.claim_id,
            production_id="prod_midnight_diner",
            type=c.category.value,
            scene_ref=c.scene_or_timecode,
            extracted_description=c.extracted_description,
            needs_clarification=c.needs_clarification,
        )
        for c in primary_output.claims
    ]
    reflection_service = SelfReflectionService()
    reconciled = reflection_service.reflect_and_reconcile(
        screenplay_text=script_text,
        primary_claims=primary_claims,
        production_id="prod_midnight_diner",
    )
    return reconciled.claims


@pytest.mark.asyncio
async def test_intake_pipeline_extracts_four_benchmark_claims(
    sample_script_path: str,
) -> None:
    """Verifies that primary + reflection pass extracts all 4 benchmark claims."""
    parser = PdfScreenplayParser()
    with open(sample_script_path, "rb") as f:
        doc = parser.parse(f.read(), filename="sample_script.pdf")

    assert doc.scene_count >= 1
    claims = await _run_intake_and_reflection(doc.raw_text)
    assert len(claims) == 4, f"Expected 4 benchmark claims, got {len(claims)}"

    conf_filter = ConfidentialityFilter()
    trimmed = [conf_filter.sanitize(c.extracted_description, asset_type=c.type).lower() for c in claims]
    types = [c.type for c in claims]

    assert any("clair de lune" in d or "debussy" in d for d in trimmed)
    assert any("apollo 11" in d or "moon landing" in d for d in trimmed)
    assert any("coca-cola" in d or "coca cola" in d for d in trimmed)
    assert any("marlboro" in d for d in trimmed)

    assert "music" in types
    assert "footage" in types
    assert "brand" in types


@pytest.mark.asyncio
async def test_confidentiality_zero_plot_emotional_spoilers(
    sample_script_path: str,
) -> None:
    """Asserts that all extracted descriptions have zero narrative/emotional spoilers."""
    parser = PdfScreenplayParser()
    with open(sample_script_path, "rb") as f:
        doc = parser.parse(f.read(), filename="sample_script.pdf")

    conf_filter = ConfidentialityFilter()
    agent = IntakeAgent(use_fallback=True)
    claims_output = await agent.extract_claims(doc.raw_text)

    for claim in claims_output.claims:
        sanitized = conf_filter.sanitize(claim.extracted_description, asset_type=claim.category.value)
        words = sanitized.split()
        assert len(words) <= 20, f"Description exceeds 20 words: '{sanitized}'"

        lower = sanitized.lower()
        # Zero character emotional trajectories or dialogue spoilers
        assert "tired eyes" not in lower
        assert "fifty years" not in lower
        assert "watch that tape" not in lower
        assert "rain streaks" not in lower
        assert "rattle the ice" not in lower


@pytest.mark.asyncio
async def test_adversarial_prompt_injection_trapped(
    adversarial_script_path: str,
) -> None:
    """Asserts prompt injection in sample_script_adversarial.pdf is safely trapped."""
    parser = PdfScreenplayParser()
    with open(adversarial_script_path, "rb") as f:
        doc = parser.parse(f.read(), filename="sample_script_adversarial.pdf")

    assert doc.scene_count >= 3
    script_text = doc.raw_text

    # Pre-inference heuristic injection scanner
    detections = scan_script_for_injections(script_text)
    assert len(detections) >= 1

    injection = detections[0]
    assert injection.is_suspicious is True
    assert injection.confidence_score >= 0.80
    assert "INT. SPEAKEASY - NIGHT" in injection.scene_ref

    # Reconcile claims with fail-closed trap handler
    agent = IntakeAgent(use_fallback=True)
    raw_output = await agent.extract_claims(script_text)
    safe_claims = reconcile_extracted_claims(raw_output.claims, detections, production_id="prod_override")

    # Assert trapped claim exists with exact security flags
    trapped = [c for c in safe_claims if c.category == ClaimCategory.OTHER]
    assert len(trapped) >= 1
    t = trapped[0]
    assert t.needs_clarification is True
    assert t.flagged_reason == "suspicious_embedded_instruction"

    # Assert legitimate claims in Scene 1 and Scene 3 are not suppressed
    descriptions = [c.extracted_description.lower() for c in safe_claims]
    assert any("detective magazine" in d or "poster" in d for d in descriptions)
    assert any("coca-cola" in d or "coca cola" in d for d in descriptions)


def _build_sample_creative_nodes() -> tuple[CreativeUseNode, ...]:
    """Builds sample creative use nodes for baseline registration test."""
    return (
        CreativeUseNode(
            claim_id="clm_001",
            stable_lineage_key="music:clair_de_lune",
            asset_type="music",
            scene_or_timecode="p.1, INT. ROADSIDE DINER - NIGHT",
            description="instrumental piece 'Clair de Lune' by Claude Debussy — sync licensing status",
            prominence="featured",
            context="The jukebox in the corner plays a soft piano melody",
            context_hash="a1b2c3d4e5f6",
            intended_scope={"media": "all_media", "territory": "worldwide"},
            licensed_scope={},
            confidence_score=0.98,
            metadata={"source": "intake_agent"},
        ),
        CreativeUseNode(
            claim_id="clm_002",
            stable_lineage_key="brand:marlboro",
            asset_type="brand",
            scene_or_timecode="p.1, INT. ROADSIDE DINER - NIGHT",
            description="Marlboro cigarette packaging shown on-screen — trademark clearance",
            prominence="background",
            context="pack of MARLBORO cigarettes is just visible",
            context_hash="b2c3d4e5f6a1",
            intended_scope={"media": "theatrical"},
            licensed_scope={},
            confidence_score=0.92,
            metadata={"source": "self_reflection"},
        ),
    )


def test_production_baseline_snapshot_registration() -> None:
    """Verifies creating and registering an immutable ProductionVersion baseline."""
    store = InMemoryBaselineStore()
    engine = ProductionBaselineEngine(store=store)

    metadata = ParserMetadata(
        parser_name="PdfScreenplayParser",
        parser_version="2.3.0",
        document_filename="sample_script.pdf",
    )

    version = engine.register_baseline(
        tenant_id="org_paramount",
        production_id="prod_diner",
        version_id="v1",
        version_tag="Locked Draft v1",
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        parser_metadata=metadata,
        claims=_build_sample_creative_nodes(),
        creator="system:intake_pipeline",
    )

    assert version.version_id == "v1"
    assert len(version.claims) == 2
    assert len(version.baseline_digest) == 64

    # Verify retrieval and tamper detection
    retrieved = engine.get_baseline("org_paramount", "prod_diner", "v1")
    assert retrieved.baseline_digest == version.baseline_digest
