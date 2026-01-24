"""Integration tests for StorageService."""

import pytest
from pathlib import Path

from quloud.core.storage_service import StorageService
from quloud.adapters.storage.filesystem_adapter import FilesystemStorageAdapter


@pytest.fixture
def storage_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for storage."""
    return tmp_path / "blobs"


@pytest.fixture
def service(storage_dir: Path) -> StorageService:
    """Provide a StorageService with filesystem adapter."""
    adapter = FilesystemStorageAdapter(storage_dir)
    return StorageService(adapter)


class TestStorageService:
    """Tests for StorageService."""

    def test_store_and_retrieve(self, service: StorageService) -> None:
        """Store and retrieve returns the same data."""
        blob_id = "test123"
        data = b"encrypted data"

        service.store(blob_id, data)
        result = service.retrieve(blob_id)

        assert result == data

    def test_retrieve_returns_none_for_missing(self, service: StorageService) -> None:
        """Retrieve returns None if data doesn't exist."""
        result = service.retrieve("nonexistent")

        assert result is None

    def test_exists_returns_true_for_stored(self, service: StorageService) -> None:
        """Exists returns True for stored data."""
        service.store("blob1", b"data")

        assert service.exists("blob1") is True

    def test_exists_returns_false_for_missing(self, service: StorageService) -> None:
        """Exists returns False for data that doesn't exist."""
        assert service.exists("missing") is False

    def test_delete_removes_data(self, service: StorageService) -> None:
        """Delete removes the data."""
        service.store("to_delete", b"data")
        assert service.exists("to_delete") is True

        result = service.delete("to_delete")

        assert result is True
        assert service.exists("to_delete") is False

    def test_delete_returns_false_for_missing(self, service: StorageService) -> None:
        """Delete returns False if data doesn't exist."""
        result = service.delete("nonexistent")

        assert result is False

    def test_handles_binary_data(self, service: StorageService) -> None:
        """Service handles binary data with all byte values."""
        data = bytes(range(256))

        service.store("binary", data)
        result = service.retrieve("binary")

        assert result == data
