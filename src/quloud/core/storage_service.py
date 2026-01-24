"""Storage service for Quloud storage nodes."""

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

    def delete(self, blob_id: str) -> bool:
        """Delete data. Returns True if deleted, False if not found."""
        return self._storage.delete(blob_id)

    def exists(self, blob_id: str) -> bool:
        """Check if data exists."""
        return self._storage.exists(blob_id)
