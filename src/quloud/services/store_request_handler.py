"""Handler for StoreRequest messages."""

import logging

from synapse.protocols.publisher import PubSubPublisher

from quloud.core.encryption_service import EncryptionService
from quloud.core.key_store_service import KeyStoreService
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import StoreRequestMessage, StoreResponseMessage

logger = logging.getLogger(__name__)


class StoreRequestHandler:
    """Handles StoreRequest messages.

    Encrypts the blob with a per-document key, stores it, and publishes a response.
    """

    def __init__(
        self,
        storage: StorageService,
        encryption: EncryptionService,
        key_store: KeyStoreService,
        publisher: PubSubPublisher,
        node_id: str,
        response_topic: str,
    ) -> None:
        """Initialize the handler.

        Args:
            storage: StorageService for data operations.
            encryption: EncryptionService for encrypting data.
            key_store: Per-document key store service.
            publisher: Publisher for sending responses.
            node_id: Unique identifier for this storage node.
            response_topic: Topic to publish responses to.
        """
        self._storage = storage
        self._encryption = encryption
        self._key_store = key_store
        self._publisher = publisher
        self._node_id = node_id
        self._response_topic = response_topic

    def handle(self, request: StoreRequestMessage) -> None:
        """Handle a StoreRequest.

        Generates a per-document key, encrypts the data, stores both.

        Args:
            request: The validated StoreRequestMessage.
        """
        logger.info("Store request received for blob_id=%s", request.blob_id)
        key = self._encryption.generate_key()
        encrypted_data = self._encryption.encrypt(key, request.data)
        self._storage.store(request.blob_id, encrypted_data)
        self._key_store.store_key(request.blob_id, key)
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
