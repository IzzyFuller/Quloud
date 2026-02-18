"""Fork-safe mutation tests for Quloud.

Mirrors all 5 e2e test scenarios with synchronous InMemoryBus
instead of RabbitMQ. Real encryption, real filesystem, real handlers.
"""

import hashlib
import os
from pathlib import Path

from quloud.adapters.key_store.filesystem_adapter import FilesystemKeyStoreAdapter
from quloud.adapters.storage.filesystem_adapter import FilesystemStorageAdapter
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import (
    ProofResponseMessage,
    RetrieveResponseMessage,
    StoreResponseMessage,
)


def test_blob_lifecycle(owner_client, bus_response, storage_dir):
    """Full blob lifecycle: store, retrieve, prove, restore, delete."""
    blob_id = "mut-lifecycle"
    plaintext = b"hello quloud mutation"

    # 1. Store with replica — local encrypted copy + remote backup
    owner_client.store_blob(blob_id, plaintext, replicas=1)
    store_response = bus_response("quloud.store.responses", StoreResponseMessage)
    assert store_response.blob_id == blob_id
    assert store_response.stored is True

    # 2. Retrieve — local read, returns plaintext directly
    retrieve_response = owner_client.retrieve_blob(blob_id)
    assert retrieve_response.found is True
    assert retrieve_response.blob_id == blob_id
    assert retrieve_response.data == plaintext

    # 3. Proof — remote node proves it still has the backup
    #    Proof is computed on E_owner (owner-encrypted data), not plaintext.
    #    Chain: owner encrypts plaintext→E_owner, sends E_owner to replica,
    #    replica re-encrypts E_owner→E_replica. On proof: replica decrypts
    #    E_replica→E_owner, computes sha256(E_owner + seed).
    e_owner = (Path(storage_dir) / f"{blob_id}.blob").read_bytes()
    seed = os.urandom(32)
    owner_client.request_proof(blob_id, seed)

    proof_response = bus_response("quloud.proof.responses", ProofResponseMessage)
    assert proof_response.found is True
    assert proof_response.blob_id == blob_id

    expected_proof = hashlib.sha256(e_owner + seed).digest()
    assert proof_response.proof == expected_proof

    # 4. Simulate local data loss — blob gone, key intact
    blob_path = Path(storage_dir) / f"{blob_id}.blob"
    blob_path.unlink()
    assert not blob_path.exists()

    # 5. Restore from backup — remote returns E_owner
    owner_client.restore_blob(blob_id)
    restore_response = bus_response(
        "quloud.retrieve.responses", RetrieveResponseMessage
    )
    assert restore_response.found is True
    assert restore_response.blob_id == blob_id
    assert restore_response.data == e_owner

    # 6. Delete — shred key, remove blob, publish delete to network
    owner_client.delete_blob(blob_id)

    key_path = Path(storage_dir) / f"{blob_id}.key"
    assert not key_path.exists(), "Key should be shredded after delete"
    assert not blob_path.exists(), "Blob should be gone after delete"


def test_retrieve_missing_blob(owner_client):
    """Retrieving a non-existent blob returns found=False."""
    response = owner_client.retrieve_blob("does-not-exist")
    assert response.found is False
    assert response.data is None


def test_proof_missing_blob(owner_client, bus_response):
    """Proof request for a non-existent blob returns found=False."""
    owner_client.request_proof("does-not-exist", os.urandom(32))

    response = bus_response("quloud.proof.responses", ProofResponseMessage)
    assert response.found is False
    assert response.proof is None


def test_restore_missing_blob(owner_client, bus_response):
    """Retrieve request for a non-existent blob on remote returns found=False."""
    owner_client.restore_blob("does-not-exist")

    response = bus_response("quloud.retrieve.responses", RetrieveResponseMessage)
    assert response.found is False
    assert response.data is None


def test_adapter_delete_and_nested_directory_creation(tmp_path):
    """Delete returns correct status; adapters create nested directories.

    Kills delete-return-value mutations (StorageService.delete(None),
    return True/False flips) and mkdir(parents=True) mutations.
    """
    # Part 1: delete return values
    flat_dir = tmp_path / "flat"
    flat_dir.mkdir()
    storage = StorageService(storage=FilesystemStorageAdapter(base_dir=flat_dir))

    storage.store("del-test", b"some data")
    assert storage.delete("del-test") is True
    assert storage.delete("del-test") is False

    # Part 2: nested storage directory creation (kills mkdir(parents=True) mutations)
    nested_dir = tmp_path / "deep" / "nested" / "storage"

    nested_storage = FilesystemStorageAdapter(base_dir=nested_dir)
    nested_storage.store("nested-test", b"data")
    assert (nested_dir / "nested-test.blob").read_bytes() == b"data"


def test_store_uses_per_document_key(owner_client, storage_dir, tmp_path):
    """Per-document key file created alongside blob; key store creates nested dirs."""
    blob_id = "mut-per-doc-key"
    owner_client.store_blob(blob_id, b"per-document key test")

    key_path = Path(storage_dir) / f"{blob_id}.key"
    blob_path = Path(storage_dir) / f"{blob_id}.blob"

    assert blob_path.exists(), "Blob file should exist after store"
    assert key_path.exists(), "Per-document key file should exist after store"
    assert len(key_path.read_bytes()) == 32, "Key should be 32 bytes (NaCl SecretBox)"

    # Nested key directory creation (kills mkdir(parents=True) mutations)
    key_dir = tmp_path / "deep" / "nested" / "keys"
    key_store = FilesystemKeyStoreAdapter(base_dir=key_dir)
    key_store.store_key("nested-test", b"k" * 32)
    assert (key_dir / "nested-test.key").read_bytes() == b"k" * 32
