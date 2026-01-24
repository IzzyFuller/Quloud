"""Unit tests for message protocol types."""

import json

from quloud.core.messages import (
    StoreRequest,
    StoreResponse,
    RetrieveRequest,
    RetrieveResponse,
    ProofOfStorageRequest,
    ProofOfStorageResponse,
)


class TestStoreRequest:
    """Tests for StoreRequest message."""

    def test_create_with_required_fields(self) -> None:
        """Can create with blob_id and data."""
        msg = StoreRequest(blob_id="abc123", data=b"encrypted blob")

        assert msg.blob_id == "abc123"
        assert msg.data == b"encrypted blob"

    def test_serializes_to_json(self) -> None:
        """Can serialize to JSON bytes."""
        msg = StoreRequest(blob_id="abc123", data=b"encrypted blob")

        serialized = msg.to_bytes()

        assert isinstance(serialized, bytes)
        parsed = json.loads(serialized)
        assert parsed["blob_id"] == "abc123"
        assert parsed["type"] == "store_request"

    def test_deserializes_from_json(self) -> None:
        """Can deserialize from JSON bytes."""
        msg = StoreRequest(blob_id="abc123", data=b"encrypted blob")
        serialized = msg.to_bytes()

        restored = StoreRequest.from_bytes(serialized)

        assert restored.blob_id == msg.blob_id
        assert restored.data == msg.data


class TestStoreResponse:
    """Tests for StoreResponse message."""

    def test_create_success_response(self) -> None:
        """Can create successful store response."""
        msg = StoreResponse(blob_id="abc123", node_id="node_xyz", stored=True)

        assert msg.blob_id == "abc123"
        assert msg.node_id == "node_xyz"
        assert msg.stored is True

    def test_create_failure_response(self) -> None:
        """Can create failed store response."""
        msg = StoreResponse(blob_id="abc123", node_id="node_xyz", stored=False)

        assert msg.stored is False

    def test_roundtrip_serialization(self) -> None:
        """Serializes and deserializes correctly."""
        msg = StoreResponse(blob_id="abc123", node_id="node_xyz", stored=True)

        restored = StoreResponse.from_bytes(msg.to_bytes())

        assert restored.blob_id == msg.blob_id
        assert restored.node_id == msg.node_id
        assert restored.stored == msg.stored


class TestRetrieveRequest:
    """Tests for RetrieveRequest message."""

    def test_create_with_blob_id(self) -> None:
        """Can create with blob_id."""
        msg = RetrieveRequest(blob_id="abc123")

        assert msg.blob_id == "abc123"

    def test_roundtrip_serialization(self) -> None:
        """Serializes and deserializes correctly."""
        msg = RetrieveRequest(blob_id="abc123")

        restored = RetrieveRequest.from_bytes(msg.to_bytes())

        assert restored.blob_id == msg.blob_id


class TestRetrieveResponse:
    """Tests for RetrieveResponse message."""

    def test_create_success_with_data(self) -> None:
        """Can create successful response with data."""
        msg = RetrieveResponse(
            blob_id="abc123", node_id="node_xyz", data=b"the blob", found=True
        )

        assert msg.blob_id == "abc123"
        assert msg.data == b"the blob"
        assert msg.found is True

    def test_create_not_found_response(self) -> None:
        """Can create not-found response."""
        msg = RetrieveResponse(
            blob_id="abc123", node_id="node_xyz", data=None, found=False
        )

        assert msg.found is False
        assert msg.data is None

    def test_roundtrip_serialization(self) -> None:
        """Serializes and deserializes correctly."""
        msg = RetrieveResponse(
            blob_id="abc123", node_id="node_xyz", data=b"the blob", found=True
        )

        restored = RetrieveResponse.from_bytes(msg.to_bytes())

        assert restored.blob_id == msg.blob_id
        assert restored.data == msg.data
        assert restored.found == msg.found


class TestProofOfStorageRequest:
    """Tests for ProofOfStorageRequest message."""

    def test_create_with_blob_id_and_seed(self) -> None:
        """Can create with blob_id and seed."""
        msg = ProofOfStorageRequest(blob_id="abc123", seed=b"random_seed")

        assert msg.blob_id == "abc123"
        assert msg.seed == b"random_seed"

    def test_roundtrip_serialization(self) -> None:
        """Serializes and deserializes correctly."""
        msg = ProofOfStorageRequest(blob_id="abc123", seed=b"random_seed")

        restored = ProofOfStorageRequest.from_bytes(msg.to_bytes())

        assert restored.blob_id == msg.blob_id
        assert restored.seed == msg.seed


class TestProofOfStorageResponse:
    """Tests for ProofOfStorageResponse message."""

    def test_create_success_with_proof(self) -> None:
        """Can create successful response with proof."""
        msg = ProofOfStorageResponse(
            blob_id="abc123", node_id="node_xyz", proof=b"hash_proof", found=True
        )

        assert msg.blob_id == "abc123"
        assert msg.proof == b"hash_proof"
        assert msg.found is True

    def test_create_lost_response(self) -> None:
        """Can create blob-lost response."""
        msg = ProofOfStorageResponse(
            blob_id="abc123", node_id="node_xyz", proof=None, found=False
        )

        assert msg.found is False
        assert msg.proof is None

    def test_roundtrip_serialization(self) -> None:
        """Serializes and deserializes correctly."""
        msg = ProofOfStorageResponse(
            blob_id="abc123", node_id="node_xyz", proof=b"hash_proof", found=True
        )

        restored = ProofOfStorageResponse.from_bytes(msg.to_bytes())

        assert restored.blob_id == msg.blob_id
        assert restored.node_id == msg.node_id
        assert restored.proof == msg.proof
        assert restored.found == msg.found
