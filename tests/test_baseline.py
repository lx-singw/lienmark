"""
tests/test_baseline.py

Automated test suite for Production Baseline Engine (Sprint 2.3).
Focus: Pydantic v2 immutability, write-once registration, digest determinism,
and cryptographic store tamper rejection.
Authored strictly under Google AntiGravity architectural guidelines for Sprint 2.3.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.core.baseline import ProductionBaselineEngine
from backend.core.baseline_types import (
    BaselineAlreadyExistsError,
    BaselineIntegrityError,
    CreativeUseNode,
    ParserMetadata,
    ProductionVersion,
    compute_baseline_digest,
)
from backend.storage.baseline_store import InMemoryBaselineStore


def _build_test_metadata() -> ParserMetadata:
    """Builds valid parser metadata fixture for baseline testing."""
    return ParserMetadata(
        parser_name="gemini_screenplay_ast",
        parser_version="2.5.0",
        model_id="gemini-2.5-flash",
        document_id="doc_broadway_v7",
        document_filename="broadway_draft_v7.pdf",
        token_usage={"prompt_tokens": 1200, "completion_tokens": 400},
        execution_duration_ms=450.0,
    )


def _build_test_claims() -> list[CreativeUseNode]:
    """Builds sample creative use nodes for baseline snapshot."""
    return [
        CreativeUseNode(
            claim_id="clm_poster_noir",
            stable_lineage_key="poster_scene42_noir",
            asset_type="artwork",
            scene_or_timecode="Scene 42",
            description="Framed vintage film noir poster on office wall",
            prominence="background",
            context="MILLER sits behind the mahogany desk.",
            context_hash="a1b2c3d4e5f60718",
            intended_scope={"territory": ["US", "CA"], "media": ["theatrical"]},
            licensed_scope={"territory": ["US"], "media": ["theatrical"]},
            confidence_score=0.98,
        ),
        CreativeUseNode(
            claim_id="clm_radio_jazz",
            stable_lineage_key="radio_scene42_miles",
            asset_type="music",
            scene_or_timecode="Scene 42",
            description="Diegetic trumpet solo playing softly on table radio",
            prominence="incidental_audio",
            context="A mournful trumpet plays from the vintage radio.",
            context_hash="f6e5d4c3b2a10987",
            intended_scope={"territory": ["worldwide"], "media": ["all"]},
            confidence_score=0.95,
        ),
    ]


class TestBaselineImmutability:
    """Verifies strict frozen model guarantees for baseline structures."""

    def test_creative_use_node_is_frozen(self):
        claims = _build_test_claims()
        claim = claims[0]
        with pytest.raises(ValidationError):
            claim.description = "Tampered description"  # type: ignore

    def test_production_version_is_frozen(self):
        engine = ProductionBaselineEngine(store=InMemoryBaselineStore())
        baseline = engine.register_baseline(
            tenant_id="org_studio_alpha",
            production_id="prod_broadway_01",
            version_id="v1",
            content_hash="a" * 64,
            parser_metadata=_build_test_metadata(),
            claims=_build_test_claims(),
            version_tag="Picture Lock v1",
        )
        with pytest.raises(ValidationError):
            baseline.version_tag = "Tampered Tag"  # type: ignore

        with pytest.raises(ValidationError):
            baseline.claims = ()  # type: ignore


class TestBaselineCreationAndRegistration:
    """Verifies baseline registration, duplicate prevention, and retrieval contracts."""

    def test_successful_baseline_registration_and_retrieval(self):
        store = InMemoryBaselineStore()
        engine = ProductionBaselineEngine(store=store)

        baseline = engine.register_baseline(
            tenant_id="org_studio_alpha",
            production_id="prod_broadway_01",
            version_id="v1",
            content_hash="1" * 64,
            parser_metadata=_build_test_metadata(),
            claims=_build_test_claims(),
            version_tag="Draft v1",
        )

        assert baseline.version_id == "v1"
        assert baseline.tenant_id == "org_studio_alpha"
        assert baseline.production_id == "prod_broadway_01"
        assert len(baseline.claims) == 2
        assert len(baseline.baseline_digest) == 64

        fetched = engine.get_baseline("org_studio_alpha", "prod_broadway_01", "v1")
        assert fetched.baseline_digest == baseline.baseline_digest

    def test_duplicate_registration_rejected(self):
        engine = ProductionBaselineEngine(store=InMemoryBaselineStore())
        engine.register_baseline(
            tenant_id="org_studio_alpha",
            production_id="prod_broadway_01",
            version_id="v1",
            content_hash="1" * 64,
            parser_metadata=_build_test_metadata(),
            claims=_build_test_claims(),
        )

        with pytest.raises(BaselineAlreadyExistsError) as exc_info:
            engine.register_baseline(
                tenant_id="org_studio_alpha",
                production_id="prod_broadway_01",
                version_id="v1",
                content_hash="2" * 64,
                parser_metadata=_build_test_metadata(),
                claims=[],
            )
        assert "already registered" in str(exc_info.value)


class TestDigestDeterminismAndTampering:
    """Verifies deterministic SHA-256 digest calculation and tamper detection."""

    def test_claim_order_invariance(self):
        claims = _build_test_claims()
        meta = _build_test_metadata()

        digest_original = compute_baseline_digest(
            version_id="v1",
            production_id="prod_broadway_01",
            tenant_id="org_studio_alpha",
            version_tag="Picture Lock",
            content_hash="c" * 64,
            parser_metadata=meta,
            claims=claims,
            previous_version_id=None,
        )

        digest_reversed = compute_baseline_digest(
            version_id="v1",
            production_id="prod_broadway_01",
            tenant_id="org_studio_alpha",
            version_tag="Picture Lock",
            content_hash="c" * 64,
            parser_metadata=meta,
            claims=list(reversed(claims)),
            previous_version_id=None,
        )

        assert digest_original == digest_reversed

    def test_tamper_detection_in_store(self):
        store = InMemoryBaselineStore()
        engine = ProductionBaselineEngine(store=store)
        engine.register_baseline(
            tenant_id="org_studio_alpha",
            production_id="prod_broadway_01",
            version_id="v1",
            content_hash="4" * 64,
            parser_metadata=_build_test_metadata(),
            claims=_build_test_claims(),
        )

        # Intentionally tamper with underlying storage payload
        raw = store._baselines[("org_studio_alpha", "prod_broadway_01", "v1")]
        raw["version_tag"] = "TAMPERED_BY_ATTACKER"

        with pytest.raises(BaselineIntegrityError) as exc_info:
            engine.get_baseline("org_studio_alpha", "prod_broadway_01", "v1")
        assert "Tampering detected" in str(exc_info.value)
