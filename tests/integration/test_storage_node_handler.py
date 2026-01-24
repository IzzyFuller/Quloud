"""Integration tests for StorageNodeHandler."""

import pytest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quloud.core.storage_service import StorageService
from quloud.core.storage_node_handler import StorageNodeHandler
from quloud.core.messages import (
    StoreRequest,
    StoreResponse,
    RetrieveRequest,
    RetrieveResponse,
    ProofOfStorageRequest,
    ProofOfStorageResponse,
)
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
) -> StorageNodeHandler:
    """Provide a StorageNodeHandler."""
    return StorageNodeHandler(
        storage=storage_service,
        publisher=publisher,
        node_id="test-node-001",
        response_topic="quloud-responses",
    )


class TestStoreRequestHandling:
    """Tests for handling StoreRequest messages."""

    def test_handle_store_request_stores_data(
        self, handler: StorageNodeHandler, storage_service: StorageService
    ) -> None:
        """Handler stores data when receiving StoreRequest."""
        request = StoreRequest(blob_id="blob123", data=b"encrypted content")

        handler.handle(request.to_bytes())

        assert storage_service.retrieve("blob123") == b"encrypted content"

    def test_handle_store_request_publishes_response(
        self, handler: StorageNodeHandler, publisher: FakePublisher
    ) -> None:
        """Handler publishes StoreResponse after storing."""
        request = StoreRequest(blob_id="blob456", data=b"data")

        handler.handle(request.to_bytes())

        assert len(publisher.published) == 1
        topic, data = publisher.published[0]
        assert topic == "quloud-responses"
        response = StoreResponse.from_bytes(data)
        assert response.blob_id == "blob456"
        assert response.node_id == "test-node-001"
        assert response.stored is True

    def test_handle_store_request_with_binary_data(
        self, handler: StorageNodeHandler, storage_service: StorageService
    ) -> None:
        """Handler correctly stores binary data with all byte values."""
        data = bytes(range(256))
        request = StoreRequest(blob_id="binary-blob", data=data)

        handler.handle(request.to_bytes())

        assert storage_service.retrieve("binary-blob") == data


class TestRetrieveRequestHandling:
    """Tests for handling RetrieveRequest messages."""

    def test_handle_retrieve_request_returns_data(
        self,
        handler: StorageNodeHandler,
        storage_service: StorageService,
        publisher: FakePublisher,
    ) -> None:
        """Handler retrieves and publishes stored data."""
        storage_service.store("existing-blob", b"stored data")
        request = RetrieveRequest(blob_id="existing-blob")

        handler.handle(request.to_bytes())

        assert len(publisher.published) == 1
        topic, data = publisher.published[0]
        response = RetrieveResponse.from_bytes(data)
        assert response.blob_id == "existing-blob"
        assert response.node_id == "test-node-001"
        assert response.found is True
        assert response.data == b"stored data"

    def test_handle_retrieve_request_for_missing_blob(
        self, handler: StorageNodeHandler, publisher: FakePublisher
    ) -> None:
        """Handler publishes not-found response for missing blob."""
        request = RetrieveRequest(blob_id="nonexistent")

        handler.handle(request.to_bytes())

        assert len(publisher.published) == 1
        response = RetrieveResponse.from_bytes(publisher.published[0][1])
        assert response.blob_id == "nonexistent"
        assert response.found is False
        assert response.data is None


class TestProofOfStorageRequestHandling:
    """Tests for handling ProofOfStorageRequest messages."""

    def test_handle_proof_request_returns_proof(
        self,
        handler: StorageNodeHandler,
        storage_service: StorageService,
        publisher: FakePublisher,
    ) -> None:
        """Handler computes and publishes proof for stored blob."""
        storage_service.store("proof-blob", b"data to prove")
        seed = b"challenge-seed"
        request = ProofOfStorageRequest(blob_id="proof-blob", seed=seed)

        handler.handle(request.to_bytes())

        assert len(publisher.published) == 1
        response = ProofOfStorageResponse.from_bytes(publisher.published[0][1])
        assert response.blob_id == "proof-blob"
        assert response.node_id == "test-node-001"
        assert response.found is True
        assert response.proof is not None

    def test_handle_proof_request_matches_service_proof(
        self,
        handler: StorageNodeHandler,
        storage_service: StorageService,
        publisher: FakePublisher,
    ) -> None:
        """Handler's published proof matches StorageService computation."""
        storage_service.store("verify-blob", b"verify data")
        seed = b"verification-seed"
        expected = storage_service.request_proof_of_storage("verify-blob", seed)
        request = ProofOfStorageRequest(blob_id="verify-blob", seed=seed)

        handler.handle(request.to_bytes())

        response = ProofOfStorageResponse.from_bytes(publisher.published[0][1])
        assert response.proof == expected

    def test_handle_proof_request_for_missing_blob(
        self, handler: StorageNodeHandler, publisher: FakePublisher
    ) -> None:
        """Handler publishes not-found response for missing blob."""
        request = ProofOfStorageRequest(blob_id="missing", seed=b"seed")

        handler.handle(request.to_bytes())

        response = ProofOfStorageResponse.from_bytes(publisher.published[0][1])
        assert response.blob_id == "missing"
        assert response.found is False
        assert response.proof is None


class TestMessageRouting:
    """Tests for message type routing."""

    def test_routes_by_message_type_field(
        self,
        handler: StorageNodeHandler,
        storage_service: StorageService,
        publisher: FakePublisher,
    ) -> None:
        """Handler routes based on 'type' field in JSON."""
        # Send store, then retrieve - verifies both routes work
        store_req = StoreRequest(blob_id="route-test", data=b"routed")
        handler.handle(store_req.to_bytes())

        retrieve_req = RetrieveRequest(blob_id="route-test")
        handler.handle(retrieve_req.to_bytes())

        assert len(publisher.published) == 2
        # First response is StoreResponse
        store_resp = StoreResponse.from_bytes(publisher.published[0][1])
        assert store_resp.stored is True
        # Second response is RetrieveResponse
        retrieve_resp = RetrieveResponse.from_bytes(publisher.published[1][1])
        assert retrieve_resp.data == b"routed"

    def test_handles_unknown_message_type_gracefully(
        self, handler: StorageNodeHandler, publisher: FakePublisher
    ) -> None:
        """Handler doesn't crash on unknown message types."""
        unknown_msg = b'{"type": "unknown_type", "foo": "bar"}'

        # Should not raise - handlers should be resilient
        handler.handle(unknown_msg)

        # No response published for unknown types
        assert len(publisher.published) == 0

    def test_handles_invalid_json_gracefully(
        self, handler: StorageNodeHandler, publisher: FakePublisher
    ) -> None:
        """Handler doesn't crash on malformed JSON."""
        invalid_json = b"not valid json at all"

        # Should not raise
        handler.handle(invalid_json)

        # No response published for invalid messages
        assert len(publisher.published) == 0
