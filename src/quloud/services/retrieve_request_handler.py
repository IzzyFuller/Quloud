"""Handler for RetrieveRequest messages."""

from synapse.protocols.publisher import PubSubPublisher

from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import (
    RetrieveRequestMessage,
    RetrieveResponseMessage,
)


class RetrieveRequestHandler:
    """Handles RetrieveRequest messages.

    Retrieves the blob and publishes a RetrieveResponse.
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

    def handle(self, request: RetrieveRequestMessage) -> None:
        """Handle a RetrieveRequest.

        Args:
            request: The validated RetrieveRequestMessage.
        """
        data = self._storage.retrieve(request.blob_id)
        response = RetrieveResponseMessage(
            blob_id=request.blob_id,
            node_id=self._node_id,
            data=data,
            found=data is not None,
        )
        self._publisher.publish(
            self._response_topic, response.model_dump_json().encode()
        )
