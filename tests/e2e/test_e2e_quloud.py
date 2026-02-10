"""E2E tests for Quloud storage node.

Real RabbitMQ, real encryption, real filesystem storage.
"""

import hashlib
import logging
import os
import time
from pathlib import Path


def test_store_and_prove(owner_client, store_capture, retrieve_capture, proof_capture):
    """Full round-trip: owner stores with replica, then verifies via proof."""
    blob_id = "e2e-test-blob"
    plaintext = b"hello quloud e2e"

    # Owner stores and replicates — handler double-encrypts its copy
    owner_client.store_blob(blob_id, plaintext, replicas=1)
    store_response = store_capture.wait()
    assert store_response.stored is True

    # Retrieve the data — handler decrypts its layer, returns E_owner
    owner_client.retrieve_blob(blob_id)
    retrieve_response = retrieve_capture.wait()
    assert retrieve_response.found is True

    # Request proof — handler decrypts its layer, computes SHA256(E_owner + seed)
    seed = os.urandom(32)
    owner_client.request_proof(blob_id, seed)

    response = proof_capture.wait()
    assert response.found is True
    assert response.blob_id == blob_id

    # Verify proof against retrieved data
    expected_proof = hashlib.sha256(retrieve_response.data + seed).digest()
    assert response.proof == expected_proof


def test_store_with_replica(owner_client, store_capture):
    """Store with replicas=1 — node processes the StoreRequest."""
    blob_id = "e2e-replica-blob"
    plaintext = b"replicate me"

    owner_client.store_blob(blob_id, plaintext, replicas=1)

    response = store_capture.wait()
    assert response.blob_id == blob_id
    assert response.stored is True


def test_store_and_retrieve(owner_client, retrieve_capture, caplog):
    """Store locally, then retrieve via network — returns decrypted plaintext."""
    blob_id = "e2e-retrieve-blob"
    plaintext = b"retrieve me"

    owner_client.store_blob(blob_id, plaintext)
    with caplog.at_level(logging.INFO):
        owner_client.retrieve_blob(blob_id)

        response = retrieve_capture.wait()

    assert response.found is True
    assert response.blob_id == blob_id
    assert response.data == plaintext
    assert f"Retrieve response published for blob_id={blob_id}" in caplog.text


def test_retrieve_missing_blob(owner_client, retrieve_capture):
    """Retrieving a non-existent blob returns found=False."""
    owner_client.retrieve_blob("does-not-exist")

    response = retrieve_capture.wait()
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


def test_delete_shreds_key(owner_client, retrieve_capture, storage_dir):
    """Deleting a blob shreds the key file and removes blob — retrieve fails after delete."""
    blob_id = "e2e-delete-blob"
    plaintext = b"delete me securely"

    owner_client.store_blob(blob_id, plaintext)

    key_path = Path(storage_dir) / f"{blob_id}.key"
    blob_path = Path(storage_dir) / f"{blob_id}.blob"
    assert key_path.exists(), "Key file should exist before delete"
    assert blob_path.exists(), "Blob file should exist before delete"

    owner_client.delete_blob(blob_id)

    assert not key_path.exists(), "Key file should be gone after delete"
    assert not blob_path.exists(), "Blob file should be gone after delete"

    # Retrieve should fail — key is shredded, blob is deleted
    owner_client.retrieve_blob(blob_id)
    response = retrieve_capture.wait()
    assert response.found is False


def test_network_delete(owner_client, store_capture, proof_capture):
    """Delete propagates to remote nodes — proof fails after network delete."""
    blob_id = "e2e-network-delete"
    plaintext = b"delete me from network"

    # Store with replica — remote node has it
    owner_client.store_blob(blob_id, plaintext, replicas=1)
    store_capture.wait()

    # Delete — local key+blob gone, DeleteRequest published
    owner_client.delete_blob(blob_id)

    time.sleep(2)  # let handler process

    # Remote should have nothing
    owner_client.request_proof(blob_id, os.urandom(32))
    response = proof_capture.wait()
    assert response.found is False
