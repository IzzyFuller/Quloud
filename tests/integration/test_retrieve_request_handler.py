"""Integration tests for RetrieveRequestHandler."""

import pytest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quloud.adapters.encryption.pynacl_adapter import PyNaClEncryptionAdapter
from quloud.adapters.storage.filesystem_adapter import FilesystemStorageAdapter
from quloud.core.encryption_service import EncryptionService
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import (
    RetrieveRequestMessage,
    RetrieveResponseMessage,
)
from quloud.services.retrieve_request_handler import RetrieveRequestHandler


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
def encryption_service() -> EncryptionService:
    """Provide an EncryptionService with PyNaCl adapter."""
    adapter = PyNaClEncryptionAdapter()
    return EncryptionService(adapter)


@pytest.fixture
def node_key(encryption_service: EncryptionService) -> bytes:
    """Provide a test node encryption key."""
    return encryption_service.generate_key()


@pytest.fixture
def publisher() -> FakePublisher:
    """Provide a fake publisher for capturing responses."""
    return FakePublisher()


@pytest.fixture
def handler(
    storage_service: StorageService,
    encryption_service: EncryptionService,
    node_key: bytes,
    publisher: FakePublisher,
) -> RetrieveRequestHandler:
    """Provide a RetrieveRequestHandler."""
    return RetrieveRequestHandler(
        storage=storage_service,
        encryption=encryption_service,
        node_key=node_key,
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
        encryption_service: EncryptionService,
        node_key: bytes,
        publisher: FakePublisher,
    ) -> None:
        """Handler retrieves, decrypts, and publishes stored data."""
        # Store encrypted data (as the store handler would)
        encrypted = encryption_service.encrypt(node_key, b"stored data")
        storage_service.store("existing-blob", encrypted)
        request = RetrieveRequestMessage(blob_id="existing-blob")

        handler.handle(request)

        assert len(publisher.published) == 1
        topic, data = publisher.published[0]
        assert topic == "quloud-responses"
        response = RetrieveResponseMessage.model_validate_json(data)
        assert response.blob_id == "existing-blob"
        assert response.node_id == "test-node-001"
        assert response.found is True
        assert response.data == b"stored data"  # Decrypted

    def test_handles_missing_blob(
        self, handler: RetrieveRequestHandler, publisher: FakePublisher
    ) -> None:
        """Handler publishes not-found response for missing blob."""
        request = RetrieveRequestMessage(blob_id="nonexistent")

        handler.handle(request)

        assert len(publisher.published) == 1
        topic, data = publisher.published[0]
        assert topic == "quloud-responses"
        response = RetrieveResponseMessage.model_validate_json(data)
        assert response.blob_id == "nonexistent"
        assert response.found is False
        assert response.data is None
