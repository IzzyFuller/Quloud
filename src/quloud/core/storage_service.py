"""Storage service for Quloud storage nodes."""

import hashlib
from dataclasses import dataclass

from quloud.core.protocols import StorageProtocol


@dataclass
class ProofResult:
    """Result of a proof-of-storage request.

    Attributes:
        found: True if the blob was found, False if lost.
        proof: The hash proof if found, None if lost.
    """

    found: bool
    proof: bytes | None


class StorageService:
    """Service for storage operations.

    Each storage node uses this service to persist encrypted data locally.
    """

    def __init__(self, storage: StorageProtocol) -> None:
        """Initialize with a storage adapter.

        Args:
            storage: Implementation of StorageProtocol.
        """
        self._storage = storage

    def store(self, blob_id: str, data: bytes) -> None:
        """Store data with the given ID."""
        return self._storage.store(blob_id, data)

    def retrieve(self, blob_id: str) -> bytes | None:
        """Retrieve data by ID. Returns None if not found."""
        return self._storage.retrieve(blob_id)

    def delete(self, blob_id: str) -> bool:
        """Delete data. Returns True if deleted, False if not found."""
        return self._storage.delete(blob_id)

    def exists(self, blob_id: str) -> bool:
        """Check if data exists."""
        return self._storage.exists(blob_id)

    def provide_proof_of_storage(self, blob_id: str, seed: bytes) -> ProofResult:
        """Compute proof that this node has the blob.

        Called by storage nodes responding to proof requests.

        Args:
            blob_id: The blob to prove possession of.
            seed: Random challenge seed from the owner.

        Returns:
            ProofResult with found=True and proof hash if blob exists,
            or found=False and proof=None if blob is lost.
        """
        data = self._storage.retrieve(blob_id)
        if data is None:
            return ProofResult(found=False, proof=None)

        proof = self._compute_proof(data, seed)
        return ProofResult(found=True, proof=proof)

    def request_proof_of_storage(self, blob_id: str, seed: bytes) -> bytes | None:
        """Compute expected proof for verification.

        Called by owners to know what proof to expect from storage nodes.

        Args:
            blob_id: The blob to compute expected proof for.
            seed: Random challenge seed being sent to storage nodes.

        Returns:
            Expected proof hash, or None if blob not found locally.
        """
        data = self._storage.retrieve(blob_id)
        if data is None:
            return None

        return self._compute_proof(data, seed)

    def _compute_proof(self, data: bytes, seed: bytes) -> bytes:
        """Compute hash(data + seed) proof."""
        return hashlib.sha256(data + seed).digest()
