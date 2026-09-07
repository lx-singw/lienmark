"""
tests/test_baseline_lineage.py

Automated test suite for Production Baseline Lineage & Multi-Tenant Isolation (Sprint 2.3).
Focus: Revision lineage progression (v1 -> v2 -> v3), broken ancestry rejection,
cross-tenant isolation, format boundary validation, and downstream claims adaptation.
Authored strictly under Google AntiGravity architectural guidelines for Sprint 2.3.
"""

from __future__ import annotations

import pytest

from backend.core.baseline import ProductionBaselineEngine
from backend.core.baseline_types import (
    BaselineLineageBrokenError,
    BaselineNotFoundError,
    BaselineTenantMismatchError,
    CreativeUseNode,
    ParserMetadata,
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


class TestRevisionLineage:
    """Verifies revision lineage progression, continuity, and broken lineage rejection."""

    def test_lineage_continuity_and_history_traversal(self):
        engine = ProductionBaselineEngine(store=InMemoryBaselineStore())
        claims = _build_test_claims()
        meta = _build_test_metadata()

        # v1 (root)
        engine.register_baseline(
            tenant_id="org_studio_alpha",
            production_id="prod_broadway_01",
            version_id="v1",
            content_hash="1" * 64,
            parser_metadata=meta,
            claims=[claims[0]],
            previous_version_id=None,
        )

        # v2 -> v1
        engine.register_baseline(
            tenant_id="org_studio_alpha",
            production_id="prod_broadway_01",
            version_id="v2",
            content_hash="2" * 64,
            parser_metadata=meta,
            claims=claims,
            previous_version_id="v1",
        )

        # v3 -> v2
        engine.register_baseline(
            tenant_id="org_studio_alpha",
            production_id="prod_broadway_01",
            version_id="v3",
            content_hash="3" * 64,
            parser_metadata=meta,
            claims=claims,
            previous_version_id="v2",
        )

        history = engine.get_lineage_history("org_studio_alpha", "prod_broadway_01", "v3")
        assert [v.version_id for v in history] == ["v1", "v2", "v3"]

    def test_broken_lineage_rejected(self):
        engine = ProductionBaselineEngine(store=InMemoryBaselineStore())
        with pytest.raises(BaselineLineageBrokenError) as exc_info:
            engine.register_baseline(
                tenant_id="org_studio_alpha",
                production_id="prod_broadway_01",
                version_id="v2",
                content_hash="2" * 64,
                parser_metadata=_build_test_metadata(),
                claims=[],
                previous_version_id="v_missing_99",
            )
        assert "predecessor baseline 'v_missing_99' does not exist" in str(exc_info.value)


class TestTenantIsolation:
    """Verifies tenant boundary format enforcement and cross-tenant data isolation."""

    def test_tenant_boundary_validation(self):
        engine = ProductionBaselineEngine(store=InMemoryBaselineStore())

        with pytest.raises(BaselineTenantMismatchError):
            engine.register_baseline(
                tenant_id="invalid_tenant_format",
                production_id="prod_01",
                version_id="v1",
                content_hash="5" * 64,
                parser_metadata=_build_test_metadata(),
                claims=[],
            )

        with pytest.raises(BaselineTenantMismatchError):
            engine.register_baseline(
                tenant_id="org_valid",
                production_id="invalid_prod",
                version_id="v1",
                content_hash="5" * 64,
                parser_metadata=_build_test_metadata(),
                claims=[],
            )

    def test_cross_tenant_isolation(self):
        engine = ProductionBaselineEngine(store=InMemoryBaselineStore())
        engine.register_baseline(
            tenant_id="org_studio_alpha",
            production_id="prod_broadway_01",
            version_id="v1",
            content_hash="6" * 64,
            parser_metadata=_build_test_metadata(),
            claims=_build_test_claims(),
        )

        with pytest.raises(BaselineNotFoundError):
            engine.get_baseline("org_indie_pictures", "prod_broadway_01", "v1")


class TestDownstreamAdaptation:
    """Verifies adaptation of baseline claims for downstream delta engine usage."""

    def test_extract_baseline_claims_adaptation(self):
        engine = ProductionBaselineEngine(store=InMemoryBaselineStore())
        engine.register_baseline(
            tenant_id="org_studio_alpha",
            production_id="prod_broadway_01",
            version_id="v1",
            content_hash="7" * 64,
            parser_metadata=_build_test_metadata(),
            claims=_build_test_claims(),
        )

        claims = engine.extract_baseline_claims("org_studio_alpha", "prod_broadway_01", "v1")
        assert len(claims) == 2
        assert claims[0]["stable_lineage_key"] == "poster_scene42_noir"
        assert claims[0]["use_id"] == "clm_poster_noir"
        assert "intended_scope" in claims[0]
