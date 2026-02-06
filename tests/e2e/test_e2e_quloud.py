"""E2E tests for Quloud storage node.

Real RabbitMQ, real encryption, real filesystem storage.
"""

import hashlib
import os


def test_store_and_prove(owner_client, proof_capture):
    """Full round-trip: owner stores locally, then verifies via proof."""
    blob_id = "e2e-test-blob"
    plaintext = b"hello quloud e2e"

    # Owner stores — NodeClient encrypts before local storage
    owner_client.store_blob(blob_id, plaintext)

    # Owner requests proof
    seed = os.urandom(32)
    owner_client.request_proof(blob_id, seed)

    # Proof response arrives via ProofResponseHandler
    response = proof_capture.wait()
    assert response.found is True
    assert response.blob_id == blob_id

    # Owner computes expected proof from their plaintext
    expected_proof = hashlib.sha256(plaintext + seed).digest()
    assert response.proof == expected_proof


def test_store_with_replica(owner_client, store_capture):
    """Store with replicas=1 — node processes the StoreRequest."""
    blob_id = "e2e-replica-blob"
    plaintext = b"replicate me"

    owner_client.store_blob(blob_id, plaintext, replicas=1)

    response = store_capture.wait()
    assert response.blob_id == blob_id
    assert response.stored is True


def test_store_and_retrieve(owner_client, retrieve_capture):
    """Store locally, then retrieve via network — returns decrypted plaintext."""
    blob_id = "e2e-retrieve-blob"
    plaintext = b"retrieve me"

    owner_client.store_blob(blob_id, plaintext)
    owner_client.retrieve_blob(blob_id)

    response = retrieve_capture.wait()
    assert response.found is True
    assert response.blob_id == blob_id
    assert response.data == plaintext


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
