"""Storage node message handler for pub-sub integration."""

import json

from synapse.protocols.publisher import PubSubPublisher

from quloud.core.storage_service import StorageService
from quloud.core.messages import (
    StoreRequest,
    StoreResponse,
    RetrieveRequest,
    RetrieveResponse,
    ProofOfStorageRequest,
    ProofOfStorageResponse,
)


class StorageNodeHandler:
    """Handles incoming messages for a storage node.

    Receives serialized messages, routes to StorageService operations,
    and publishes responses.
    """

    def __init__(
        self,
        storage: StorageService,
        publisher: PubSubPublisher,
        node_id: str,
        response_topic: str,
    ) -> None:
        """Initialize the handler.

        Args:
            storage: StorageService for data operations.
            publisher: Publisher for sending responses.
            node_id: Unique identifier for this storage node.
            response_topic: Topic to publish responses to.
        """
        self._storage = storage
        self._publisher = publisher
        self._node_id = node_id
        self._response_topic = response_topic

    def handle(self, request: bytes) -> None:
        """Handle an incoming message.

        Args:
            request: Serialized message bytes (JSON with 'type' field).
        """
        try:
            parsed = json.loads(request)
            msg_type = parsed.get("type")
        except (json.JSONDecodeError, AttributeError):
            return

        if msg_type == "store_request":
            self._handle_store(StoreRequest.from_bytes(request))
        elif msg_type == "retrieve_request":
            self._handle_retrieve(RetrieveRequest.from_bytes(request))
        elif msg_type == "proof_of_storage_request":
            self._handle_proof(ProofOfStorageRequest.from_bytes(request))

    def _handle_store(self, request: StoreRequest) -> None:
        """Handle a store request."""
        self._storage.store(request.blob_id, request.data)
        response = StoreResponse(
            blob_id=request.blob_id,
            node_id=self._node_id,
            stored=True,
        )
        self._publisher.publish(self._response_topic, response.to_bytes())

    def _handle_retrieve(self, request: RetrieveRequest) -> None:
        """Handle a retrieve request."""
        data = self._storage.retrieve(request.blob_id)
        response = RetrieveResponse(
            blob_id=request.blob_id,
            node_id=self._node_id,
            data=data,
            found=data is not None,
        )
        self._publisher.publish(self._response_topic, response.to_bytes())

    def _handle_proof(self, request: ProofOfStorageRequest) -> None:
        """Handle a proof-of-storage request."""
        result = self._storage.provide_proof_of_storage(request.blob_id, request.seed)
        response = ProofOfStorageResponse(
            blob_id=request.blob_id,
            node_id=self._node_id,
            proof=result.proof,
            found=result.found,
        )
        self._publisher.publish(self._response_topic, response.to_bytes())
