"""E2E tests for Quloud storage node.

Real RabbitMQ, real encryption, real filesystem storage.
"""

import hashlib
import os
from pathlib import Path


def test_blob_lifecycle(
    owner_client, store_capture, proof_capture, restore_capture, storage_dir
):
    """Full blob lifecycle: store, retrieve, prove, restore from backup, delete."""
    blob_id = "e2e-lifecycle"
    plaintext = b"hello quloud e2e"

    # 1. Store with replica — local encrypted copy + remote backup
    owner_client.store_blob(blob_id, plaintext, replicas=1)
    store_response = store_capture.wait()
    assert store_response.blob_id == blob_id
    assert store_response.stored is True

    # 2. Retrieve — local read, returns plaintext directly
    retrieve_response = owner_client.retrieve_blob(blob_id)
    assert retrieve_response.found is True
    assert retrieve_response.blob_id == blob_id
    assert retrieve_response.data == plaintext

    # 3. Proof — remote node proves it still has the backup
    #    Proof is computed on E_owner (owner-encrypted data), not plaintext
    e_owner = (Path(storage_dir) / f"{blob_id}.blob").read_bytes()
    seed = os.urandom(32)
    owner_client.request_proof(blob_id, seed)

    proof_response = proof_capture.wait()
    assert proof_response.found is True
    assert proof_response.blob_id == blob_id

    expected_proof = hashlib.sha256(e_owner + seed).digest()
    assert proof_response.proof == expected_proof

    # 4. Simulate local data loss — blob gone, key intact
    blob_path = Path(storage_dir) / f"{blob_id}.blob"
    blob_path.unlink()
    assert not blob_path.exists()

    # 5. Restore from backup — remote returns E_owner, which matches our local copy
    owner_client.restore_blob(blob_id)
    restore_response = restore_capture.wait()
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


def test_proof_missing_blob(owner_client, proof_capture):
    """Proof request for a non-existent blob returns found=False."""
    owner_client.request_proof("does-not-exist", os.urandom(32))

    response = proof_capture.wait()
    assert response.found is False
    assert response.proof is None


def test_store_uses_per_document_key(owner_client, storage_dir):
    """Storing a blob creates a per-document .key file alongside the .blob file."""
    blob_id = "e2e-per-doc-key"
    owner_client.store_blob(blob_id, b"per-document key test")

    key_path = Path(storage_dir) / f"{blob_id}.key"
    blob_path = Path(storage_dir) / f"{blob_id}.blob"

    assert blob_path.exists(), "Blob file should exist after store"
    assert key_path.exists(), "Per-document key file should exist after store"
    assert len(key_path.read_bytes()) == 32, "Key should be 32 bytes (NaCl SecretBox)"
