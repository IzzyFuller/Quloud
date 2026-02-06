"""Filesystem adapter for per-document key storage."""

import os
from pathlib import Path


class FilesystemKeyStoreAdapter:
    """Stores per-document encryption keys on the filesystem.

    Keys stored at: {base_dir}/{blob_id}.key
    Secure delete overwrites with random bytes before unlinking.
    """

    def __init__(self, base_dir: str | Path) -> None:
        """Initialize filesystem key store adapter.

        Args:
            base_dir: Base directory for key storage.
        """
        self._base_dir = Path(base_dir)

    def _get_key_path(self, blob_id: str) -> Path:
        """Get file path for a blob's key."""
        return self._base_dir / f"{blob_id}.key"

    def store_key(self, blob_id: str, key: bytes) -> None:
        """Store an encryption key for the given blob.

        Args:
            blob_id: Unique identifier for the blob.
            key: Encryption key bytes.
        """
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._get_key_path(blob_id).write_bytes(key)

    def retrieve_key(self, blob_id: str) -> bytes | None:
        """Retrieve the encryption key for a blob.

        Args:
            blob_id: Unique identifier for the blob.

        Returns:
            Key bytes if found, None otherwise.
        """
        key_path = self._get_key_path(blob_id)
        if not key_path.exists():
            return None
        return key_path.read_bytes()

    def delete_key(self, blob_id: str) -> None:
        """Securely delete the encryption key for a blob.

        Overwrites the key file with random bytes before unlinking,
        making the encrypted blob permanently inaccessible.

        Args:
            blob_id: Unique identifier for the blob.
        """
        key_path = self._get_key_path(blob_id)
        if key_path.exists():
            key_path.write_bytes(os.urandom(len(key_path.read_bytes())))
            key_path.unlink()
