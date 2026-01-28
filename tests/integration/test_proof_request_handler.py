"""Integration tests for ProofRequestHandler."""

import hashlib
import pytest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quloud.adapters.encryption.pynacl_adapter import PyNaClEncryptionAdapter
from quloud.adapters.storage.filesystem_adapter import FilesystemStorageAdapter
from quloud.core.encryption_service import EncryptionService
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import ProofRequestMessage, ProofResponseMessage
from quloud.services.proof_request_handler import ProofRequestHandler


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
    """Provide a node encryption key."""
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
) -> ProofRequestHandler:
    """Provide a ProofRequestHandler with encryption."""
    return ProofRequestHandler(
        storage=storage_service,
        encryption=encryption_service,
        node_key=node_key,
        publisher=publisher,
        node_id="test-node-001",
        response_topic="quloud.proof.responses",
    )


class TestProofRequestHandler:
    """Tests for ProofRequestHandler."""

    def test_returns_proof_for_stored_blob(
        self,
        handler: ProofRequestHandler,
        storage_service: StorageService,
        encryption_service: EncryptionService,
        node_key: bytes,
        publisher: FakePublisher,
    ) -> None:
        """Handler computes and publishes proof for stored blob."""
        # Simulate what StoreRequestHandler does: encrypt then store
        owner_encrypted_data = b"E_owner(original data)"
        node_encrypted = encryption_service.encrypt(node_key, owner_encrypted_data)
        storage_service.store("proof-blob", node_encrypted)

        seed = b"challenge-seed"
        request = ProofRequestMessage(blob_id="proof-blob", seed=seed)

        handler.handle(request)

        assert len(publisher.published) == 1
        topic, data = publisher.published[0]
        assert topic == "quloud.proof.responses"
        response = ProofResponseMessage.model_validate_json(data)
        assert response.blob_id == "proof-blob"
        assert response.node_id == "test-node-001"
        assert response.found is True
        assert response.proof is not None

    def test_proof_computed_on_owner_encrypted_data(
        self,
        handler: ProofRequestHandler,
        storage_service: StorageService,
        encryption_service: EncryptionService,
        node_key: bytes,
        publisher: FakePublisher,
    ) -> None:
        """Proof is computed on E_owner(data), not E_node(E_owner(data)).

        This allows the owner to verify the proof using their local copy
        of E_owner(data).
        """
        owner_encrypted_data = b"E_owner(data) - what owner has locally"
        node_encrypted = encryption_service.encrypt(node_key, owner_encrypted_data)
        storage_service.store("verify-blob", node_encrypted)

        seed = b"verification-seed"
        # Owner computes expected proof from their local E_owner(data)
        expected_proof = hashlib.sha256(owner_encrypted_data + seed).digest()

        request = ProofRequestMessage(blob_id="verify-blob", seed=seed)
        handler.handle(request)

        response = ProofResponseMessage.model_validate_json(publisher.published[0][1])
        assert response.proof == expected_proof

    def test_handles_missing_blob(
        self, handler: ProofRequestHandler, publisher: FakePublisher
    ) -> None:
        """Handler publishes not-found response for missing blob."""
        request = ProofRequestMessage(blob_id="missing", seed=b"seed")

        handler.handle(request)

        topic, data = publisher.published[0]
        assert topic == "quloud.proof.responses"
        response = ProofResponseMessage.model_validate_json(data)
        assert response.blob_id == "missing"
        assert response.found is False
        assert response.proof is None

    def test_different_seeds_produce_different_proofs(
        self,
        handler: ProofRequestHandler,
        storage_service: StorageService,
        encryption_service: EncryptionService,
        node_key: bytes,
        publisher: FakePublisher,
    ) -> None:
        """Different seeds produce different proofs (replay protection)."""
        owner_encrypted_data = b"same data"
        node_encrypted = encryption_service.encrypt(node_key, owner_encrypted_data)
        storage_service.store("replay-test", node_encrypted)

        handler.handle(ProofRequestMessage(blob_id="replay-test", seed=b"seed-1"))
        handler.handle(ProofRequestMessage(blob_id="replay-test", seed=b"seed-2"))

        proof1 = ProofResponseMessage.model_validate_json(
            publisher.published[0][1]
        ).proof
        proof2 = ProofResponseMessage.model_validate_json(
            publisher.published[1][1]
        ).proof

        assert proof1 != proof2
