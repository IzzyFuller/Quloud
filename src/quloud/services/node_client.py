"""Client for owner-initiated network operations."""

from synapse.protocols.publisher import PubSubPublisher

from quloud.core.encryption_service import EncryptionService
from quloud.core.key_store_service import KeyStoreService
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import (
    DeleteRequestMessage,
    RetrieveRequestMessage,
    RetrieveResponseMessage,
    StoreRequestMessage,
    ProofRequestMessage,
)


class NodeClient:
    """Client for publishing requests to the storage network.

    Used by node owners to store, retrieve, and verify data.
    The local node always stores data; replicas are additional remote copies.
    """

    def __init__(
        self,
        storage: StorageService,
        encryption: EncryptionService,
        key_store: KeyStoreService,
        publisher: PubSubPublisher,
        store_topic: str,
        retrieve_topic: str,
        proof_topic: str,
        delete_topic: str,
    ) -> None:
        """Initialize the client.

        Args:
            storage: Storage service for this node.
            encryption: Encryption service for this node.
            key_store: Per-document key store service.
            publisher: Publisher for sending messages.
            store_topic: Topic for StoreRequest messages.
            retrieve_topic: Topic for RetrieveRequest messages.
            proof_topic: Topic for ProofOfStorageRequest messages.
            delete_topic: Topic for DeleteRequest messages.
        """
        self._storage = storage
        self._encryption = encryption
        self._key_store = key_store
        self._publisher = publisher
        self._store_topic = store_topic
        self._retrieve_topic = retrieve_topic
        self._proof_topic = proof_topic
        self._delete_topic = delete_topic

    def store_blob(self, blob_id: str, data: bytes, replicas: int = 0) -> None:
        """Store data locally and optionally replicate to remote nodes.

        Args:
            blob_id: Unique identifier for the blob.
            data: The plaintext data to store (encrypted before local storage).
            replicas: Number of additional remote copies (default 0 = local only).
        """
        key = self._encryption.generate_key()
        encrypted = self._encryption.encrypt(key, data)
        self._storage.store(blob_id, encrypted)
        self._key_store.store_key(blob_id, key)

        # Request remote replicas if any
        if replicas > 0:
            request = StoreRequestMessage(blob_id=blob_id, data=encrypted)
            for _ in range(replicas):
                self._publisher.publish(
                    self._store_topic, request.model_dump_json().encode()
                )

    def retrieve_blob(self, blob_id: str) -> RetrieveResponseMessage:
        """Retrieve a blob from local storage.

        Args:
            blob_id: Unique identifier for the blob to retrieve.

        Returns:
            Response with found=True and decrypted data, or found=False.
        """
        encrypted = self._storage.retrieve(blob_id)
        if encrypted is None:
            return RetrieveResponseMessage(
                blob_id=blob_id, node_id="", found=False, data=None
            )

        key = self._key_store.retrieve_key(blob_id)
        if key is None:
            return RetrieveResponseMessage(
                blob_id=blob_id, node_id="", found=False, data=None
            )

        plaintext = self._encryption.decrypt(key, encrypted)
        return RetrieveResponseMessage(
            blob_id=blob_id, node_id="", found=True, data=plaintext
        )

    def restore_blob(self, blob_id: str) -> None:
        """Request a blob be restored from a remote backup node.

        Publishes a RetrieveRequest to the network. The response
        is handled asynchronously by the restore response handler.

        Args:
            blob_id: Unique identifier for the blob to restore.
        """
        request = RetrieveRequestMessage(blob_id=blob_id)
        self._publisher.publish(
            self._retrieve_topic, request.model_dump_json().encode()
        )

    def request_proof(self, blob_id: str, seed: bytes) -> None:
        """Publish ProofOfStorageRequest to the network.

        Args:
            blob_id: Unique identifier for the blob to verify.
            seed: Random seed for replay protection.
        """
        request = ProofRequestMessage(blob_id=blob_id, seed=seed)
        self._publisher.publish(self._proof_topic, request.model_dump_json().encode())

    def delete_blob(self, blob_id: str) -> None:
        """Delete a blob locally and publish delete request to the network.

        Shreds the local encryption key, deletes the local blob data,
        and publishes a DeleteRequest for remote nodes to do the same.

        Args:
            blob_id: Unique identifier for the blob to delete.
        """
        self._key_store.delete_key(blob_id)
        self._storage.delete(blob_id)
        request = DeleteRequestMessage(blob_id=blob_id)
        self._publisher.publish(self._delete_topic, request.model_dump_json().encode())
