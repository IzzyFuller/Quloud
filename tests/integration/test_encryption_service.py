"""Integration tests for EncryptionService."""

import pytest

from quloud.core.encryption_service import EncryptionService
from quloud.adapters.encryption.pynacl_adapter import PyNaClEncryptionAdapter


@pytest.fixture
def service() -> EncryptionService:
    """Provide an EncryptionService with PyNaCl adapter."""
    adapter = PyNaClEncryptionAdapter()
    return EncryptionService(adapter)


class TestEncryptionService:
    """Tests for EncryptionService."""

    def test_generate_key_returns_bytes(self, service: EncryptionService) -> None:
        """Generate key returns bytes."""
        key = service.generate_key()

        assert isinstance(key, bytes)
        assert len(key) == 32  # SecretBox key size

    def test_generate_key_returns_unique_keys(self, service: EncryptionService) -> None:
        """Each call to generate_key returns a unique key."""
        key1 = service.generate_key()
        key2 = service.generate_key()

        assert key1 != key2

    def test_encrypt_returns_bytes(self, service: EncryptionService) -> None:
        """Encrypt returns bytes."""
        key = service.generate_key()
        plaintext = b"secret data"

        ciphertext = service.encrypt(key, plaintext)

        assert isinstance(ciphertext, bytes)

    def test_encrypt_produces_different_output_than_input(
        self, service: EncryptionService
    ) -> None:
        """Ciphertext differs from plaintext."""
        key = service.generate_key()
        plaintext = b"secret data"

        ciphertext = service.encrypt(key, plaintext)

        assert ciphertext != plaintext

    def test_decrypt_recovers_plaintext(self, service: EncryptionService) -> None:
        """Decrypt recovers the original plaintext."""
        key = service.generate_key()
        plaintext = b"secret data"

        ciphertext = service.encrypt(key, plaintext)
        result = service.decrypt(key, ciphertext)

        assert result == plaintext

    def test_encrypt_with_same_key_produces_different_ciphertext(
        self, service: EncryptionService
    ) -> None:
        """Same plaintext encrypted twice produces different ciphertext (nonce)."""
        key = service.generate_key()
        plaintext = b"secret data"

        ciphertext1 = service.encrypt(key, plaintext)
        ciphertext2 = service.encrypt(key, plaintext)

        assert ciphertext1 != ciphertext2

    def test_decrypt_with_wrong_key_fails(self, service: EncryptionService) -> None:
        """Decrypt with wrong key raises an error."""
        key1 = service.generate_key()
        key2 = service.generate_key()
        plaintext = b"secret data"

        ciphertext = service.encrypt(key1, plaintext)

        with pytest.raises(Exception):  # nacl.exceptions.CryptoError
            service.decrypt(key2, ciphertext)

    def test_handles_empty_plaintext(self, service: EncryptionService) -> None:
        """Service handles empty plaintext."""
        key = service.generate_key()

        ciphertext = service.encrypt(key, b"")
        result = service.decrypt(key, ciphertext)

        assert result == b""

    def test_handles_binary_data(self, service: EncryptionService) -> None:
        """Service handles binary data with all byte values."""
        key = service.generate_key()
        plaintext = bytes(range(256))

        ciphertext = service.encrypt(key, plaintext)
        result = service.decrypt(key, ciphertext)

        assert result == plaintext
