"""Storage service for Quloud storage nodes."""

import hashlib

from quloud.core.protocols import StorageProtocol


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

    def compute_proof(self, data: bytes, seed: bytes) -> bytes:
        """Compute hash(data + seed) proof.

        Args:
            data: The data to prove possession of.
            seed: Random challenge seed for replay protection.

        Returns:
            SHA256 hash of data + seed.
        """
        return hashlib.sha256(data + seed).digest()
