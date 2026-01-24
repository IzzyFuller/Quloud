"""Integration tests for EncryptionService with PyNaCl adapter."""

import pytest
from nacl.secret import SecretBox

from quloud.core.encryption_service import EncryptionService


class TestKeyGeneration:
    """Tests for key generation."""

    def test_generated_key_is_correct_length(
        self, encryption_service: EncryptionService
    ) -> None:
        """Generated key should be 32 bytes (SecretBox.KEY_SIZE)."""
        key = encryption_service.generate_key()
        assert len(key) == SecretBox.KEY_SIZE
        assert len(key) == 32

    def test_generated_keys_are_unique(
        self, encryption_service: EncryptionService
    ) -> None:
        """Each call to generate_key should produce a unique key."""
        keys = [encryption_service.generate_key() for _ in range(100)]
        assert len(set(keys)) == 100


class TestEncryptDecryptRoundTrip:
    """Tests for encrypt/decrypt operations."""

    def test_encrypt_decrypt_returns_original_data(
        self, encryption_service: EncryptionService
    ) -> None:
        """Encrypt then decrypt should return the original plaintext."""
        key = encryption_service.generate_key()
        plaintext = b"Hello, Quloud!"

        ciphertext = encryption_service.encrypt(key, plaintext)
        decrypted = encryption_service.decrypt(key, ciphertext)

        assert decrypted == plaintext

    def test_ciphertext_differs_from_plaintext(
        self, encryption_service: EncryptionService
    ) -> None:
        """Ciphertext should not equal plaintext."""
        key = encryption_service.generate_key()
        plaintext = b"Secret message"

        ciphertext = encryption_service.encrypt(key, plaintext)

        assert ciphertext != plaintext

    def test_encrypt_with_empty_data(
        self, encryption_service: EncryptionService
    ) -> None:
        """Should handle empty byte string."""
        key = encryption_service.generate_key()
        plaintext = b""

        ciphertext = encryption_service.encrypt(key, plaintext)
        decrypted = encryption_service.decrypt(key, ciphertext)

        assert decrypted == plaintext

    def test_encrypt_with_large_data(
        self, encryption_service: EncryptionService
    ) -> None:
        """Should handle large data (1MB+)."""
        key = encryption_service.generate_key()
        plaintext = b"x" * (1024 * 1024)  # 1MB

        ciphertext = encryption_service.encrypt(key, plaintext)
        decrypted = encryption_service.decrypt(key, ciphertext)

        assert decrypted == plaintext

    def test_same_plaintext_produces_different_ciphertext(
        self, encryption_service: EncryptionService
    ) -> None:
        """Same plaintext encrypted twice should produce different ciphertext (due to nonce)."""
        key = encryption_service.generate_key()
        plaintext = b"Hello, Quloud!"

        ciphertext1 = encryption_service.encrypt(key, plaintext)
        ciphertext2 = encryption_service.encrypt(key, plaintext)

        assert ciphertext1 != ciphertext2


class TestErrorCases:
    """Tests for error handling."""

    def test_wrong_key_fails_to_decrypt(
        self, encryption_service: EncryptionService
    ) -> None:
        """Decryption with wrong key should raise an exception."""
        key1 = encryption_service.generate_key()
        key2 = encryption_service.generate_key()
        plaintext = b"Secret message"

        ciphertext = encryption_service.encrypt(key1, plaintext)

        with pytest.raises(Exception):  # CryptoError
            encryption_service.decrypt(key2, ciphertext)

    def test_corrupted_ciphertext_fails_to_decrypt(
        self, encryption_service: EncryptionService
    ) -> None:
        """Corrupted ciphertext should raise an exception."""
        key = encryption_service.generate_key()
        plaintext = b"Secret message"

        ciphertext = encryption_service.encrypt(key, plaintext)
        corrupted = ciphertext[:-1] + bytes([ciphertext[-1] ^ 0xFF])

        with pytest.raises(Exception):  # CryptoError
            encryption_service.decrypt(key, corrupted)

    def test_invalid_key_length_rejected_on_encrypt(
        self, encryption_service: EncryptionService
    ) -> None:
        """Invalid key length should raise an exception."""
        invalid_key = b"too short"
        plaintext = b"Secret message"

        with pytest.raises(Exception):  # ValueError
            encryption_service.encrypt(invalid_key, plaintext)

    def test_invalid_key_length_rejected_on_decrypt(
        self, encryption_service: EncryptionService
    ) -> None:
        """Invalid key length should raise an exception on decrypt."""
        invalid_key = b"too short"
        ciphertext = b"some fake ciphertext"

        with pytest.raises(Exception):  # ValueError
            encryption_service.decrypt(invalid_key, ciphertext)


class TestDoubleEncryption:
    """Tests for Quloud use case - double encryption."""

    def test_double_encryption_with_different_keys(
        self, encryption_service: EncryptionService
    ) -> None:
        """Data encrypted twice with different keys should decrypt in reverse order."""
        key1 = encryption_service.generate_key()  # Owner's key
        key2 = encryption_service.generate_key()  # Storage node's key
        original = b"Original data for storage"

        # Owner encrypts, then storage node encrypts
        encrypted_by_owner = encryption_service.encrypt(key1, original)
        double_encrypted = encryption_service.encrypt(key2, encrypted_by_owner)

        # Storage node decrypts, then owner decrypts
        decrypted_by_node = encryption_service.decrypt(key2, double_encrypted)
        final_result = encryption_service.decrypt(key1, decrypted_by_node)

        assert final_result == original
