"""
tests/test_baseline_store.py

Authoritative test suite for Baseline Store under Lienmark Milestone B:
1. Atomic baseline progression with monotonic version advancement.
2. Parent baseline linkage validation and broken pointer rejection.
3. get_latest_baseline() retrieval across tenants and productions.
4. Thread safety under concurrent access.
5. Transactional Firestore writes and fallback behavior.
"""

from __future__ import annotations

import concurrent.futures
from unittest.mock import MagicMock
import pytest

from backend.core.baseline_types import (
    BaselineAlreadyExistsError,
    BaselineLineageBrokenError,
    CreativeUseNode,
    ParserMetadata,
    ProductionVersion,
    compute_baseline_digest,
)
from backend.storage.baseline_store import (
    FirestoreBaselineStore,
    InMemoryBaselineStore,
    get_default_baseline_store,
    parse_version_tuple,
)


def _build_meta() -> ParserMetadata:
    return ParserMetadata(
        parser_name="gemini_screenplay_ast",
        parser_version="2.5.0",
        model_id="gemini-2.5-flash",
    )


def _build_baseline(
    version_id: str,
    tenant_id: str = "org_paramount",
    production_id: str = "prod_godfather",
    previous_version_id: str | None = None,
    created_at: str | None = None,
) -> ProductionVersion:
    meta = _build_meta()
    claims = [
        CreativeUseNode(
            claim_id=f"clm_{version_id}_01",
            stable_lineage_key=f"poster_{version_id}",
            asset_type="artwork",
            scene_or_timecode="Scene 1",
            description="Background poster",
            prominence="incidental",
            context_hash="0123456789abcdef",
        )
    ]
    digest = compute_baseline_digest(
        version_id=version_id,
        production_id=production_id,
        tenant_id=tenant_id,
        version_tag=f"Version {version_id}",
        content_hash="f" * 64,
        parser_metadata=meta,
        claims=claims,
        previous_version_id=previous_version_id,
    )
    kwargs = {
        "version_id": version_id,
        "production_id": production_id,
        "tenant_id": tenant_id,
        "version_tag": f"Version {version_id}",
        "content_hash": "f" * 64,
        "parser_metadata": meta,
        "claims": tuple(claims),
        "previous_version_id": previous_version_id,
        "baseline_digest": digest,
    }
    if created_at:
        kwargs["created_at"] = created_at
    return ProductionVersion(**kwargs)


class TestParseVersionTuple:
    """Verifies version string parsing."""

    def test_parses_standard_versions(self) -> None:
        assert parse_version_tuple("v1") == (1,)
        assert parse_version_tuple("v2") == (2,)
        assert parse_version_tuple("v10") == (10,)
        assert parse_version_tuple("v1.2.3") == (1, 2, 3)
        assert parse_version_tuple("1") == (1,)

    def test_parses_non_standard_returns_none(self) -> None:
        assert parse_version_tuple("arbitrary_cut") is None
        assert parse_version_tuple("") is None


class TestBaselineProgression:
    """Verifies atomic baseline progression: monotonic advancement & parent linkage."""

    def test_monotonic_progression_success(self) -> None:
        store = InMemoryBaselineStore()
        b1 = _build_baseline("v1")
        b2 = _build_baseline("v2", previous_version_id="v1")
        b3 = _build_baseline("v3", previous_version_id="v2")

        store.save_baseline(b1)
        store.save_baseline(b2)
        store.save_baseline(b3)

        assert store.has_baseline("org_paramount", "prod_godfather", "v1")
        assert store.has_baseline("org_paramount", "prod_godfather", "v2")
        assert store.has_baseline("org_paramount", "prod_godfather", "v3")

    def test_non_monotonic_version_without_parent_link_rejected(self) -> None:
        store = InMemoryBaselineStore()
        b2 = _build_baseline("v2")
        store.save_baseline(b2)

        # Attempt to save v1 without valid parent linkage
        b1 = _build_baseline("v1")
        with pytest.raises(BaselineLineageBrokenError) as exc_info:
            store.save_baseline(b1)
        assert "does not advance monotonically" in str(exc_info.value)

    def test_parent_baseline_linkage_allows_branching_or_named_cut(self) -> None:
        store = InMemoryBaselineStore()
        b1 = _build_baseline("v1")
        store.save_baseline(b1)

        # Named version that does not parse as numeric tuple, but has valid parent linkage
        b_cut = _build_baseline("directors_cut", previous_version_id="v1")
        store.save_baseline(b_cut)
        assert store.has_baseline("org_paramount", "prod_godfather", "directors_cut")

    def test_broken_parent_linkage_rejected(self) -> None:
        store = InMemoryBaselineStore()
        b1 = _build_baseline("v1")
        store.save_baseline(b1)

        # Points to non-existent predecessor
        b_broken = _build_baseline("v2", previous_version_id="v999")
        with pytest.raises(BaselineLineageBrokenError) as exc_info:
            store.save_baseline(b_broken)
        assert "Lineage broken" in str(exc_info.value)

    def test_duplicate_version_rejected(self) -> None:
        store = InMemoryBaselineStore()
        b1 = _build_baseline("v1")
        store.save_baseline(b1)

        with pytest.raises(BaselineAlreadyExistsError):
            store.save_baseline(b1)


class TestGetLatestBaseline:
    """Verifies get_latest_baseline returns the latest snapshot."""

    def test_returns_none_when_no_baselines_registered(self) -> None:
        store = InMemoryBaselineStore()
        latest = store.get_latest_baseline("org_paramount", "prod_godfather")
        assert latest is None

    def test_returns_latest_registered_baseline(self) -> None:
        store = InMemoryBaselineStore()
        b1 = _build_baseline("v1", created_at="2026-01-01T10:00:00Z")
        b2 = _build_baseline("v2", previous_version_id="v1", created_at="2026-01-02T10:00:00Z")
        b3 = _build_baseline("v3", previous_version_id="v2", created_at="2026-01-03T10:00:00Z")

        store.save_baseline(b1)
        store.save_baseline(b2)
        store.save_baseline(b3)

        latest = store.get_latest_baseline("org_paramount", "prod_godfather")
        assert latest is not None
        assert latest.version_id == "v3"

    def test_respects_tenant_and_production_isolation(self) -> None:
        store = InMemoryBaselineStore()
        b_a = _build_baseline("v1", tenant_id="org_paramount", production_id="prod_godfather")
        b_b = _build_baseline("v1", tenant_id="org_universal", production_id="prod_jurassic")

        store.save_baseline(b_a)
        store.save_baseline(b_b)

        latest_a = store.get_latest_baseline("org_paramount", "prod_godfather")
        latest_b = store.get_latest_baseline("org_universal", "prod_jurassic")
        latest_c = store.get_latest_baseline("org_warner", "prod_batman")

        assert latest_a is not None and latest_a.tenant_id == "org_paramount"
        assert latest_b is not None and latest_b.tenant_id == "org_universal"
        assert latest_c is None


class TestThreadSafetyAndFirestore:
    """Verifies thread safety and transactional operations."""

    def test_thread_safe_concurrent_access(self) -> None:
        store = InMemoryBaselineStore()
        store.save_baseline(_build_baseline("v1", production_id="prod_concurrent_safe"))

        errors = []

        def read_latest():
            try:
                for _ in range(50):
                    latest = store.get_latest_baseline("org_paramount", "prod_concurrent_safe")
                    assert latest is not None
            except Exception as e:
                errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(read_latest) for _ in range(8)]
            concurrent.futures.wait(futures)

        assert len(errors) == 0

    def test_firestore_fallback_operates_cleanly(self) -> None:
        store = FirestoreBaselineStore(client=None)
        store._client = None
        b1 = _build_baseline("v1", production_id="prod_fb_isolated")
        store.save_baseline(b1)

        latest = store.get_latest_baseline("org_paramount", "prod_fb_isolated")
        assert latest is not None
        assert latest.version_id == "v1"

    def test_firestore_transactional_execution(self) -> None:
        mock_client = MagicMock()
        mock_transaction = MagicMock()
        mock_client.transaction.return_value = mock_transaction

        # Setup doc_ref mocks
        mock_doc = MagicMock()
        mock_doc.get.return_value.exists = False
        mock_client.collection.return_value.document.return_value.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_doc

        store = FirestoreBaselineStore(client=mock_client)
        store.has_baseline = MagicMock(return_value=False)  # type: ignore
        store.get_latest_baseline = MagicMock(return_value=None)  # type: ignore

        b1 = _build_baseline("v1", production_id="prod_tx_isolated")
        store.save_baseline(b1)

        assert mock_client.transaction.called
        assert mock_transaction.set.called

    def test_factory_singleton(self) -> None:
        store1 = get_default_baseline_store(force_in_memory=True)
        assert isinstance(store1, InMemoryBaselineStore)
