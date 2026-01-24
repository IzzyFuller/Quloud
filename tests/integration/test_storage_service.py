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


class TestProofOfStorage:
    """Tests for proof-of-storage operations."""

    def test_provide_proof_returns_hash_when_blob_exists(
        self, service: StorageService
    ) -> None:
        """Storage node can prove it has the blob."""
        blob_id = "owned_blob"
        data = b"encrypted owner data"
        seed = b"random_challenge_seed"
        service.store(blob_id, data)

        result = service.provide_proof_of_storage(blob_id, seed)

        assert result.found is True
        assert result.proof is not None
        assert isinstance(result.proof, bytes)

    def test_provide_proof_returns_lost_when_blob_missing(
        self, service: StorageService
    ) -> None:
        """Storage node reports blob lost if not found."""
        result = service.provide_proof_of_storage("missing_blob", b"seed")

        assert result.found is False
        assert result.proof is None

    def test_provide_proof_is_deterministic_for_same_inputs(
        self, service: StorageService
    ) -> None:
        """Same blob + seed always produces same proof."""
        service.store("blob1", b"data")
        seed = b"consistent_seed"

        proof1 = service.provide_proof_of_storage("blob1", seed)
        proof2 = service.provide_proof_of_storage("blob1", seed)

        assert proof1.proof == proof2.proof

    def test_provide_proof_differs_with_different_seed(
        self, service: StorageService
    ) -> None:
        """Different seeds produce different proofs (replay protection)."""
        service.store("blob1", b"data")

        proof1 = service.provide_proof_of_storage("blob1", b"seed_one")
        proof2 = service.provide_proof_of_storage("blob1", b"seed_two")

        assert proof1.proof != proof2.proof

    def test_provide_proof_differs_with_different_data(
        self, service: StorageService
    ) -> None:
        """Different data produces different proofs."""
        service.store("blob_a", b"data_a")
        service.store("blob_b", b"data_b")
        seed = b"same_seed"

        proof_a = service.provide_proof_of_storage("blob_a", seed)
        proof_b = service.provide_proof_of_storage("blob_b", seed)

        assert proof_a.proof != proof_b.proof

    def test_request_proof_returns_expected_hash(self, service: StorageService) -> None:
        """Owner can compute expected proof for verification."""
        blob_id = "my_blob"
        data = b"my encrypted data"
        seed = b"challenge"
        service.store(blob_id, data)

        expected = service.request_proof_of_storage(blob_id, seed)

        assert expected is not None
        assert isinstance(expected, bytes)

    def test_request_and_provide_match_for_same_data(
        self, service: StorageService
    ) -> None:
        """Owner's expected proof matches storage node's provided proof."""
        blob_id = "shared_blob"
        data = b"the actual encrypted data"
        seed = b"verification_seed"
        service.store(blob_id, data)

        expected = service.request_proof_of_storage(blob_id, seed)
        provided = service.provide_proof_of_storage(blob_id, seed)

        assert provided.proof == expected

    def test_request_returns_none_for_missing_blob(
        self, service: StorageService
    ) -> None:
        """Can't request proof for blob we don't have."""
        result = service.request_proof_of_storage("not_here", b"seed")

        assert result is None
