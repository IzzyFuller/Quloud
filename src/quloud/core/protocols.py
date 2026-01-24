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
