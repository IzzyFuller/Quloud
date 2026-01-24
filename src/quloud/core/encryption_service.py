"""Encryption service for Quloud storage nodes."""

from quloud.core.protocols import EncryptionProtocol


class EncryptionService:
    """Service for encryption operations.

    Each storage node uses this service to encrypt everything it stores
    with its own key.
    """

    def __init__(self, encryption: EncryptionProtocol) -> None:
        """Initialize with an encryption adapter.

        Args:
            encryption: Implementation of EncryptionProtocol.
        """
        self._encryption = encryption

    def generate_key(self) -> bytes:
        """Generate a new encryption key."""
        return self._encryption.generate_key()

    def encrypt(self, key: bytes, plaintext: bytes) -> bytes:
        """Encrypt data with the given key."""
        return self._encryption.encrypt(key, plaintext)

    def decrypt(self, key: bytes, ciphertext: bytes) -> bytes:
        """Decrypt data with the given key."""
        return self._encryption.decrypt(key, ciphertext)
