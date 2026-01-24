"""Handler for RetrieveRequest messages."""

from synapse.protocols.publisher import PubSubPublisher

from quloud.core.storage_service import StorageService
from quloud.core.messages import RetrieveRequest, RetrieveResponse


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

    def handle(self, request: RetrieveRequest) -> None:
        """Handle a RetrieveRequest.

        Args:
            request: The validated RetrieveRequest.
        """
        data = self._storage.retrieve(request.blob_id)
        response = RetrieveResponse(
            blob_id=request.blob_id,
            node_id=self._node_id,
            data=data,
            found=data is not None,
        )
        self._publisher.publish(self._response_topic, response.to_bytes())
