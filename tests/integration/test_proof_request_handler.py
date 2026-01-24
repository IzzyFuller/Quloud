"""Integration tests for ProofRequestHandler."""

import pytest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quloud.core.storage_service import StorageService
from quloud.services.proof_request_handler import ProofRequestHandler
from quloud.core.messages import ProofOfStorageRequest, ProofOfStorageResponse
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
) -> ProofRequestHandler:
    """Provide a ProofRequestHandler."""
    return ProofRequestHandler(
        storage=storage_service,
        publisher=publisher,
        node_id="test-node-001",
        response_topic="quloud-responses",
    )


class TestProofRequestHandler:
    """Tests for ProofRequestHandler."""

    def test_returns_proof_for_stored_blob(
        self,
        handler: ProofRequestHandler,
        storage_service: StorageService,
        publisher: FakePublisher,
    ) -> None:
        """Handler computes and publishes proof for stored blob."""
        storage_service.store("proof-blob", b"data to prove")
        seed = b"challenge-seed"
        request = ProofOfStorageRequest(blob_id="proof-blob", seed=seed)

        handler.handle(request)

        assert len(publisher.published) == 1
        response = ProofOfStorageResponse.from_bytes(publisher.published[0][1])
        assert response.blob_id == "proof-blob"
        assert response.node_id == "test-node-001"
        assert response.found is True
        assert response.proof is not None

    def test_proof_matches_service_computation(
        self,
        handler: ProofRequestHandler,
        storage_service: StorageService,
        publisher: FakePublisher,
    ) -> None:
        """Handler's published proof matches StorageService computation."""
        storage_service.store("verify-blob", b"verify data")
        seed = b"verification-seed"
        expected = storage_service.request_proof_of_storage("verify-blob", seed)
        request = ProofOfStorageRequest(blob_id="verify-blob", seed=seed)

        handler.handle(request)

        response = ProofOfStorageResponse.from_bytes(publisher.published[0][1])
        assert response.proof == expected

    def test_handles_missing_blob(
        self, handler: ProofRequestHandler, publisher: FakePublisher
    ) -> None:
        """Handler publishes not-found response for missing blob."""
        request = ProofOfStorageRequest(blob_id="missing", seed=b"seed")

        handler.handle(request)

        response = ProofOfStorageResponse.from_bytes(publisher.published[0][1])
        assert response.blob_id == "missing"
        assert response.found is False
        assert response.proof is None
