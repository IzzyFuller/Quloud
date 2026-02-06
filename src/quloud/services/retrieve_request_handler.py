"""Handler for RetrieveRequest messages."""

import logging

from synapse.protocols.publisher import PubSubPublisher

from quloud.core.encryption_service import EncryptionService
from quloud.core.key_store_service import KeyStoreService
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import (
    RetrieveRequestMessage,
    RetrieveResponseMessage,
)

logger = logging.getLogger(__name__)


class RetrieveRequestHandler:
    """Handles RetrieveRequest messages.

    Retrieves and decrypts the blob using its per-document key, then publishes a response.
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
            encryption: EncryptionService for decrypting data.
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

    def handle(self, request: RetrieveRequestMessage) -> None:
        """Handle a RetrieveRequest.

        Looks up the per-document key and decrypts the data.

        Args:
            request: The validated RetrieveRequestMessage.
        """
        logger.info("Retrieve request received for blob_id=%s", request.blob_id)
        encrypted_data = self._storage.retrieve(request.blob_id)
        key = self._key_store.retrieve_key(request.blob_id)
        if encrypted_data is None or key is None:
            logger.warning("Blob or key not found: blob_id=%s", request.blob_id)
            data = None
            found = False
        else:
            data = self._encryption.decrypt(key, encrypted_data)
            found = True
            logger.info("Retrieved blob_id=%s", request.blob_id)

        response = RetrieveResponseMessage(
            blob_id=request.blob_id,
            node_id=self._node_id,
            data=data,
            found=found,
        )
        self._publisher.publish(
            self._response_topic, response.model_dump_json().encode()
        )
        logger.info("Retrieve response published for blob_id=%s", request.blob_id)
