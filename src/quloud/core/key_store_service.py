"""Key store service for per-document encryption keys."""

from quloud.core.protocols import KeyStoreProtocol


class KeyStoreService:
    """Service for per-document encryption key operations."""

    def __init__(self, key_store: KeyStoreProtocol) -> None:
        """Initialize with a key store adapter.

        Args:
            key_store: Implementation of KeyStoreProtocol.
        """
        self._key_store = key_store

    def store_key(self, blob_id: str, key: bytes) -> None:
        """Store an encryption key for the given blob."""
        self._key_store.store_key(blob_id, key)

    def retrieve_key(self, blob_id: str) -> bytes | None:
        """Retrieve the encryption key for a blob."""
        return self._key_store.retrieve_key(blob_id)

    def delete_key(self, blob_id: str) -> None:
        """Securely delete the encryption key for a blob."""
        self._key_store.delete_key(blob_id)
