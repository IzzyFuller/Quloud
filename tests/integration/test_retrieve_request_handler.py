"""Integration tests for RetrieveRequestHandler."""

import pytest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quloud.core.storage_service import StorageService
from quloud.handlers.retrieve_request_handler import RetrieveRequestHandler
from quloud.core.messages import RetrieveRequest, RetrieveResponse
from quloud.adapters.storage.filesystem_adapter import FilesystemStorageAdapter


@dataclass
class FakePublisher:
    """Test double that captures published messages."""

    published: list[tuple[str, bytes]] = field(default_factory=list)

    def publish(self, topic: str, data: bytes, **kwargs: Any) -> str:
        """Capture the published message."""
        self.published.append((topic, data))
        return "fake-message-id"


@pytest.fixture
def storage_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for storage."""
    return tmp_path / "blobs"


@pytest.fixture
def storage_service(storage_dir: Path) -> StorageService:
    """Provide a StorageService with filesystem adapter."""
    adapter = FilesystemStorageAdapter(storage_dir)
    return StorageService(adapter)


@pytest.fixture
def publisher() -> FakePublisher:
    """Provide a fake publisher for capturing responses."""
    return FakePublisher()


@pytest.fixture
def handler(
    storage_service: StorageService, publisher: FakePublisher
) -> RetrieveRequestHandler:
    """Provide a RetrieveRequestHandler."""
    return RetrieveRequestHandler(
        storage=storage_service,
        publisher=publisher,
        node_id="test-node-001",
        response_topic="quloud-responses",
    )


class TestRetrieveRequestHandler:
    """Tests for RetrieveRequestHandler."""

    def test_retrieves_and_publishes_data(
        self,
        handler: RetrieveRequestHandler,
        storage_service: StorageService,
        publisher: FakePublisher,
    ) -> None:
        """Handler retrieves and publishes stored data."""
        storage_service.store("existing-blob", b"stored data")
        request = RetrieveRequest(blob_id="existing-blob")

        handler.handle(request)

        assert len(publisher.published) == 1
        topic, data = publisher.published[0]
        response = RetrieveResponse.from_bytes(data)
        assert response.blob_id == "existing-blob"
        assert response.node_id == "test-node-001"
        assert response.found is True
        assert response.data == b"stored data"

    def test_handles_missing_blob(
        self, handler: RetrieveRequestHandler, publisher: FakePublisher
    ) -> None:
        """Handler publishes not-found response for missing blob."""
        request = RetrieveRequest(blob_id="nonexistent")

        handler.handle(request)

        assert len(publisher.published) == 1
        response = RetrieveResponse.from_bytes(publisher.published[0][1])
        assert response.blob_id == "nonexistent"
        assert response.found is False
        assert response.data is None
