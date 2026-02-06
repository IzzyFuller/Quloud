"""Handler for StoreRequest messages."""

import logging

from synapse.protocols.publisher import PubSubPublisher

from quloud.core.encryption_service import EncryptionService
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import StoreRequestMessage, StoreResponseMessage

logger = logging.getLogger(__name__)


class StoreRequestHandler:
    """Handles StoreRequest messages.

    Encrypts the blob with the node's key, stores it, and publishes a response.
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
            encryption: EncryptionService for encrypting data.
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

    def handle(self, request: StoreRequestMessage) -> None:
        """Handle a StoreRequest.

        Encrypts the data with the node's key before storing.

        Args:
            request: The validated StoreRequestMessage.
        """
        logger.info("Store request received for blob_id=%s", request.blob_id)
        encrypted_data = self._encryption.encrypt(self._node_key, request.data)
        self._storage.store(request.blob_id, encrypted_data)
        logger.info("Stored blob_id=%s", request.blob_id)
        response = StoreResponseMessage(
            blob_id=request.blob_id,
            node_id=self._node_id,
            stored=True,
        )
        self._publisher.publish(
            self._response_topic, response.model_dump_json().encode()
        )
        logger.info("Store response published for blob_id=%s", request.blob_id)
