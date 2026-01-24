"""Pytest fixtures for Quloud tests."""

import pytest

from quloud.adapters.encryption.pynacl_adapter import PyNaClEncryptionAdapter
from quloud.core.encryption_service import EncryptionService


@pytest.fixture
def encryption_service() -> EncryptionService:
    """Provide an EncryptionService with PyNaCl adapter injected."""
    adapter = PyNaClEncryptionAdapter()
    return EncryptionService(encryption=adapter)
