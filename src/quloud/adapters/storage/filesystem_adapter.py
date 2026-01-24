"""Filesystem adapter for storage implementing StorageProtocol."""

from pathlib import Path


class FilesystemStorageAdapter:
    """
    Local filesystem-based storage adapter.

    Stores data at: {base_dir}/{blob_id}.blob
    """

    def __init__(self, base_dir: str | Path) -> None:
        """
        Initialize filesystem storage adapter.

        Args:
            base_dir: Base directory for storage.
        """
        self._base_dir = Path(base_dir)

    def _get_blob_path(self, blob_id: str) -> Path:
        """Get file path for a blob."""
        return self._base_dir / f"{blob_id}.blob"

    def store(self, blob_id: str, data: bytes) -> None:
        """
        Store data to the filesystem.

        Args:
            blob_id: Unique identifier for the data.
            data: Binary data to store.
        """
        self._base_dir.mkdir(parents=True, exist_ok=True)
        blob_path = self._get_blob_path(blob_id)
        blob_path.write_bytes(data)

    def retrieve(self, blob_id: str) -> bytes | None:
        """
        Retrieve data from the filesystem.

        Args:
            blob_id: Unique identifier for the data.

        Returns:
            Binary data if found, None otherwise.
        """
        blob_path = self._get_blob_path(blob_id)
        if not blob_path.exists():
            return None
        return blob_path.read_bytes()

    def delete(self, blob_id: str) -> bool:
        """
        Delete data from the filesystem.

        Args:
            blob_id: Unique identifier for the data.

        Returns:
            True if deleted, False if data didn't exist.
        """
        blob_path = self._get_blob_path(blob_id)
        if not blob_path.exists():
            return False
        blob_path.unlink()
        return True

    def exists(self, blob_id: str) -> bool:
        """
        Check if data exists.

        Args:
            blob_id: Unique identifier for the data.

        Returns:
            True if data exists, False otherwise.
        """
        return self._get_blob_path(blob_id).exists()
