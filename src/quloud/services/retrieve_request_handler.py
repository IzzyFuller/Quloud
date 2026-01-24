"""Handler for RetrieveRequest messages."""

from synapse.protocols.publisher import PubSubPublisher

from quloud.core.encryption_service import EncryptionService
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import (
    RetrieveRequestMessage,
    RetrieveResponseMessage,
)


class RetrieveRequestHandler:
    """Handles RetrieveRequest messages.

    Retrieves and decrypts the blob, then publishes a response.
    """

    def __init__(
        self,
        storage: StorageService,
        encryption: EncryptionService,
        node_key: bytes,
        publisher: PubSubPublisher,
        node_id: str,
        response_topic: str,
    ) -> None:
        """Initialize the handler.

        Args:
            storage: StorageService for data operations.
            encryption: EncryptionService for decrypting data.
            node_key: This node's symmetric encryption key.
            publisher: Publisher for sending responses.
            node_id: Unique identifier for this storage node.
            response_topic: Topic to publish responses to.
        """
        self._storage = storage
        self._encryption = encryption
        self._node_key = node_key
        self._publisher = publisher
        self._node_id = node_id
        self._response_topic = response_topic

    def handle(self, request: RetrieveRequestMessage) -> None:
        """Handle a RetrieveRequest.

        Decrypts the data with the node's key before returning.

        Args:
            request: The validated RetrieveRequestMessage.
        """
        encrypted_data = self._storage.retrieve(request.blob_id)
        if encrypted_data is None:
            data = None
            found = False
        else:
            data = self._encryption.decrypt(self._node_key, encrypted_data)
            found = True

        response = RetrieveResponseMessage(
            blob_id=request.blob_id,
            node_id=self._node_id,
            data=data,
            found=found,
        )
        self._publisher.publish(
            self._response_topic, response.model_dump_json().encode()
        )
