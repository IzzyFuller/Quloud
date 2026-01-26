"""Client for owner-initiated network operations."""

from synapse.protocols.publisher import PubSubPublisher

from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import (
    StoreRequestMessage,
    RetrieveRequestMessage,
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
        publisher: PubSubPublisher,
        store_topic: str,
        retrieve_topic: str,
        proof_topic: str,
    ) -> None:
        """Initialize the client.

        Args:
            storage: Storage service for this node.
            publisher: Publisher for sending messages.
            store_topic: Topic for StoreRequest messages.
            retrieve_topic: Topic for RetrieveRequest messages.
            proof_topic: Topic for ProofOfStorageRequest messages.
        """
        self._storage = storage
        self._publisher = publisher
        self._store_topic = store_topic
        self._retrieve_topic = retrieve_topic
        self._proof_topic = proof_topic

    def store_blob(self, blob_id: str, data: bytes, replicas: int = 0) -> None:
        """Store data locally and optionally replicate to remote nodes.

        Args:
            blob_id: Unique identifier for the blob.
            data: The data to store (will be stored as-is locally).
            replicas: Number of additional remote copies (default 0 = local only).
        """
        # Always store on this node first
        self._storage.store(blob_id, data)

        # Request remote replicas if any
        if replicas > 0:
            request = StoreRequestMessage(blob_id=blob_id, data=data)
            for _ in range(replicas):
                self._publisher.publish(
                    self._store_topic, request.model_dump_json().encode()
                )

    def retrieve_blob(self, blob_id: str) -> None:
        """Publish RetrieveRequest to the network.

        Args:
            blob_id: Unique identifier for the blob to retrieve.
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
