"""Protocol definitions for Quloud core ports."""

from typing import Protocol


class EncryptionProtocol(Protocol):
    """Port for encryption operations.

    Defines the interface for symmetric encryption used by storage nodes.
    Each node encrypts everything it stores with its own key.
    """

    def generate_key(self) -> bytes:
        """Generate a new encryption key."""
        ...

    def encrypt(self, key: bytes, plaintext: bytes) -> bytes:
        """Encrypt data with the given key."""
        ...

    def decrypt(self, key: bytes, ciphertext: bytes) -> bytes:
        """Decrypt data with the given key."""
        ...


class StorageProtocol(Protocol):
    """Port for storage operations.

    Defines the interface for storing and retrieving encrypted data.
    Each storage node uses this to persist data locally.
    """

    def store(self, blob_id: str, data: bytes) -> None:
        """Store data with the given ID."""
        ...

    def retrieve(self, blob_id: str) -> bytes | None:
        """Retrieve data by ID. Returns None if not found."""
        ...

    def delete(self, blob_id: str) -> bool:
        """Delete data. Returns True if deleted, False if not found."""
        ...

    def exists(self, blob_id: str) -> bool:
        """Check if data exists."""
        ...
