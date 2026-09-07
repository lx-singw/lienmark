"""
Unit tests for storage watcher domain types, models, enums, and GCS path validation.
"""

import pytest

from backend.services.storage_watcher_types import (
    FolderScopeResult,
    IngestionStatus,
    StorageEvent,
    WatcherConfig,
    parse_and_validate_gcs_path,
)


def test_ingestion_status_values() -> None:
    """Verifies all mandatory IngestionStatus enum variants."""
    assert IngestionStatus.QUEUED.value == "queued"
    assert IngestionStatus.PROCESSING.value == "processing"
    assert IngestionStatus.COMPLETED.value == "completed"
    assert IngestionStatus.REJECTED_OUT_OF_SCOPE.value == "rejected_out_of_scope"
    assert IngestionStatus.FAILED.value == "failed"


def test_storage_event_instantiation() -> None:
    """Verifies StorageEvent model attributes and default values."""
    event = StorageEvent(
        event_id="evt_test_001",
        bucket="lienmark-scripts-prod",
        object_name="organizations/org_alpha/productions/prod_beta/locked/script_v8.pdf",
        etag="9fa0c714c3e0",
        size_bytes=1048576,
        time_created_utc="2026-09-07T08:00:00Z",
    )
    assert event.content_type == "application/pdf"
    assert event.source == "eventarc"
    assert event.generation is None
    assert event.size_bytes == 1048576


def test_watcher_config_defaults() -> None:
    """Verifies default parameters for WatcherConfig."""
    cfg = WatcherConfig()
    assert cfg.polling_interval_seconds == 5.0
    assert cfg.max_batch_size == 50
    assert cfg.lease_ttl_seconds == 60.0


def test_parse_and_validate_gcs_path_valid() -> None:
    """Verifies parsing of strict, compliant locked GCS paths."""
    path = "organizations/org_studio_01/productions/prod_broadway/locked/script_v8.pdf"
    result = parse_and_validate_gcs_path(path)

    assert result.is_valid_scope is True
    assert result.organization_id == "org_studio_01"
    assert result.production_id == "prod_broadway"
    assert result.filename == "script_v8.pdf"
    assert result.rejection_reason is None


def test_parse_and_validate_gcs_path_leading_slash() -> None:
    """Verifies leading slashes are normalized safely."""
    path = "/organizations/org_alpha/productions/prod_beta/locked/scene_42.pdf"
    result = parse_and_validate_gcs_path(path)

    assert result.is_valid_scope is True
    assert result.organization_id == "org_alpha"
    assert result.production_id == "prod_beta"
    assert result.filename == "scene_42.pdf"


def test_parse_and_validate_gcs_path_rejects_empty_and_null() -> None:
    """Verifies rejection of empty, null, or whitespace-only paths."""
    assert parse_and_validate_gcs_path("").is_valid_scope is False
    assert parse_and_validate_gcs_path("   ").is_valid_scope is False


def test_parse_and_validate_gcs_path_rejects_traversal() -> None:
    """Verifies rejection of directory traversal attempts."""
    path = "organizations/org_alpha/productions/../locked/script.pdf"
    result = parse_and_validate_gcs_path(path)

    assert result.is_valid_scope is False
    assert "traversal" in (result.rejection_reason or "").lower()


@pytest.mark.parametrize("sandbox_marker", ["sandbox", "drafts", "temp", "scratch"])
def test_parse_and_validate_gcs_path_rejects_sandboxes(sandbox_marker: str) -> None:
    """Verifies rejection of writer sandbox folders."""
    path = f"organizations/org_alpha/productions/prod_beta/{sandbox_marker}/script.pdf"
    result = parse_and_validate_gcs_path(path)

    assert result.is_valid_scope is False
    assert "sandbox" in (result.rejection_reason or "").lower()


@pytest.mark.parametrize("ext", [".docx", ".png", ".txt", ".csv", ".json"])
def test_parse_and_validate_gcs_path_rejects_non_pdf(ext: str) -> None:
    """Verifies rejection of non-PDF assets."""
    path = f"organizations/org_alpha/productions/prod_beta/locked/asset{ext}"
    result = parse_and_validate_gcs_path(path)

    assert result.is_valid_scope is False
    assert "only pdf" in (result.rejection_reason or "").lower()


def test_parse_and_validate_gcs_path_rejects_malformed_structure() -> None:
    """Verifies rejection of paths missing mandatory production/locked segments."""
    assert parse_and_validate_gcs_path("organizations/org_alpha/locked/file.pdf").is_valid_scope is False
    assert parse_and_validate_gcs_path("productions/prod_beta/locked/file.pdf").is_valid_scope is False
    assert parse_and_validate_gcs_path("organizations/org/productions/prod/open/file.pdf").is_valid_scope is False
