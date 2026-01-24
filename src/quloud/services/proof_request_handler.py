"""Handler for ProofOfStorageRequest messages."""

from synapse.protocols.publisher import PubSubPublisher

from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import ProofRequestMessage, ProofResponseMessage


class ProofRequestHandler:
    """Handles ProofOfStorageRequest messages.

    Computes proof-of-storage and publishes a ProofOfStorageResponse.
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

    def handle(self, request: ProofRequestMessage) -> None:
        """Handle a ProofOfStorageRequest.

        Args:
            request: The validated ProofRequestMessage.
        """
        result = self._storage.provide_proof_of_storage(request.blob_id, request.seed)
        response = ProofResponseMessage(
            blob_id=request.blob_id,
            node_id=self._node_id,
            proof=result.proof,
            found=result.found,
        )
        self._publisher.publish(
            self._response_topic, response.model_dump_json().encode()
        )
