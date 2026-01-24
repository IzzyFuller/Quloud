"""PyNaCl implementation of EncryptionProtocol."""

from nacl.secret import SecretBox
from nacl.utils import random


class PyNaClEncryptionAdapter:
    """PyNaCl SecretBox implementation of EncryptionProtocol.

    Uses NaCl's SecretBox for authenticated symmetric encryption.
    SecretBox uses XSalsa20 stream cipher with Poly1305 MAC.
    """

    def generate_key(self) -> bytes:
        """Generate a new 32-byte encryption key."""
        return random(SecretBox.KEY_SIZE)

    def encrypt(self, key: bytes, plaintext: bytes) -> bytes:
        """Encrypt data with the given key.

        Returns ciphertext with prepended nonce (24 bytes).
        """
        box = SecretBox(key)
        return bytes(box.encrypt(plaintext))

    def decrypt(self, key: bytes, ciphertext: bytes) -> bytes:
        """Decrypt data with the given key.

        Expects ciphertext with prepended nonce (24 bytes).
        """
        box = SecretBox(key)
        return bytes(box.decrypt(ciphertext))
