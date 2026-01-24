"""Integration tests for StoreRequestHandler."""

import pytest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quloud.core.storage_service import StorageService
from quloud.handlers.store_request_handler import StoreRequestHandler
from quloud.core.messages import StoreRequest, StoreResponse
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
) -> StoreRequestHandler:
    """Provide a StoreRequestHandler."""
    return StoreRequestHandler(
        storage=storage_service,
        publisher=publisher,
        node_id="test-node-001",
        response_topic="quloud-responses",
    )


class TestStoreRequestHandler:
    """Tests for StoreRequestHandler."""

    def test_stores_data(
        self, handler: StoreRequestHandler, storage_service: StorageService
    ) -> None:
        """Handler stores data when receiving StoreRequest."""
        request = StoreRequest(blob_id="blob123", data=b"encrypted content")

        handler.handle(request)

        assert storage_service.retrieve("blob123") == b"encrypted content"

    def test_publishes_response(
        self, handler: StoreRequestHandler, publisher: FakePublisher
    ) -> None:
        """Handler publishes StoreResponse after storing."""
        request = StoreRequest(blob_id="blob456", data=b"data")

        handler.handle(request)

        assert len(publisher.published) == 1
        topic, data = publisher.published[0]
        assert topic == "quloud-responses"
        response = StoreResponse.from_bytes(data)
        assert response.blob_id == "blob456"
        assert response.node_id == "test-node-001"
        assert response.stored is True

    def test_handles_binary_data(
        self, handler: StoreRequestHandler, storage_service: StorageService
    ) -> None:
        """Handler correctly stores binary data with all byte values."""
        data = bytes(range(256))
        request = StoreRequest(blob_id="binary-blob", data=data)

        handler.handle(request)

        assert storage_service.retrieve("binary-blob") == data
