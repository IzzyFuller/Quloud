"""Client for owner-initiated network operations."""

from synapse.protocols.publisher import PubSubPublisher

from quloud.core.messages import (
    StoreRequest,
    RetrieveRequest,
    ProofOfStorageRequest,
)


class NodeClient:
    """Client for publishing requests to the storage network.

    Used by node owners to store, retrieve, and verify data.
    """

    def __init__(
        self,
        publisher: PubSubPublisher,
        store_topic: str,
        retrieve_topic: str,
        proof_topic: str,
    ) -> None:
        """Initialize the client.

        Args:
            publisher: Publisher for sending messages.
            store_topic: Topic for StoreRequest messages.
            retrieve_topic: Topic for RetrieveRequest messages.
            proof_topic: Topic for ProofOfStorageRequest messages.
        """
        self._publisher = publisher
        self._store_topic = store_topic
        self._retrieve_topic = retrieve_topic
        self._proof_topic = proof_topic

    def store_blob(self, blob_id: str, data: bytes, duplicates: int = 1) -> None:
        """Publish StoreRequests to the network.

        Args:
            blob_id: Unique identifier for the blob.
            data: The encrypted data to store.
            duplicates: Number of copies to request (default 1).
        """
        request = StoreRequest(blob_id=blob_id, data=data)
        for _ in range(duplicates):
            self._publisher.publish(self._store_topic, request.to_bytes())

    def retrieve_blob(self, blob_id: str) -> None:
        """Publish RetrieveRequest to the network.

        Args:
            blob_id: Unique identifier for the blob to retrieve.
        """
        request = RetrieveRequest(blob_id=blob_id)
        self._publisher.publish(self._retrieve_topic, request.to_bytes())

    def request_proof(self, blob_id: str, seed: bytes) -> None:
        """Publish ProofOfStorageRequest to the network.

        Args:
            blob_id: Unique identifier for the blob to verify.
            seed: Random seed for replay protection.
        """
        request = ProofOfStorageRequest(blob_id=blob_id, seed=seed)
        self._publisher.publish(self._proof_topic, request.to_bytes())
