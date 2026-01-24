"""Integration tests for StoreRequestHandler."""

import pytest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quloud.adapters.encryption.pynacl_adapter import PyNaClEncryptionAdapter
from quloud.adapters.storage.filesystem_adapter import FilesystemStorageAdapter
from quloud.core.encryption_service import EncryptionService
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import StoreRequestMessage, StoreResponseMessage
from quloud.services.store_request_handler import StoreRequestHandler


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
) -> StoreRequestHandler:
    """Provide a StoreRequestHandler."""
    return StoreRequestHandler(
        storage=storage_service,
        encryption=encryption_service,
        node_key=node_key,
        publisher=publisher,
        node_id="test-node-001",
        response_topic="quloud-responses",
    )


class TestStoreRequestHandler:
    """Tests for StoreRequestHandler."""

    def test_stores_data(
        self,
        handler: StoreRequestHandler,
        storage_service: StorageService,
        encryption_service: EncryptionService,
        node_key: bytes,
    ) -> None:
        """Handler encrypts and stores data when receiving StoreRequest."""
        request = StoreRequestMessage(blob_id="blob123", data=b"encrypted content")

        handler.handle(request)

        # Data is stored encrypted
        stored = storage_service.retrieve("blob123")
        assert stored is not None
        assert stored != b"encrypted content"  # Not stored as plaintext
        # But can be decrypted to original
        decrypted = encryption_service.decrypt(node_key, stored)
        assert decrypted == b"encrypted content"

    def test_publishes_response(
        self, handler: StoreRequestHandler, publisher: FakePublisher
    ) -> None:
        """Handler publishes StoreResponse after storing."""
        request = StoreRequestMessage(blob_id="blob456", data=b"data")

        handler.handle(request)

        assert len(publisher.published) == 1
        topic, data = publisher.published[0]
        assert topic == "quloud-responses"
        response = StoreResponseMessage.model_validate_json(data)
        assert response.blob_id == "blob456"
        assert response.node_id == "test-node-001"
        assert response.stored is True

    def test_handles_binary_data(
        self,
        handler: StoreRequestHandler,
        storage_service: StorageService,
        encryption_service: EncryptionService,
        node_key: bytes,
    ) -> None:
        """Handler correctly stores binary data with all byte values."""
        data = bytes(range(256))
        request = StoreRequestMessage(blob_id="binary-blob", data=data)

        handler.handle(request)

        stored = storage_service.retrieve("binary-blob")
        assert stored is not None
        decrypted = encryption_service.decrypt(node_key, stored)
        assert decrypted == data
