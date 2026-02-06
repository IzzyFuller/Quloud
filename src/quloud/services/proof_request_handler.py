"""Handler for ProofOfStorageRequest messages."""

import logging

from synapse.protocols.publisher import PubSubPublisher

from quloud.core.encryption_service import EncryptionService
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import ProofRequestMessage, ProofResponseMessage

logger = logging.getLogger(__name__)


class ProofRequestHandler:
    """Handles ProofOfStorageRequest messages.

    Decrypts the stored blob and computes proof on the owner-encrypted data.
    This allows the owner to verify the proof using their local copy.
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
            encryption: EncryptionService for decrypting stored data.
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

    def handle(self, request: ProofRequestMessage) -> None:
        """Handle a ProofOfStorageRequest.

        Decrypts the stored blob first, then computes proof on the
        owner-encrypted data (E_owner(data)), not the node-encrypted
        data (E_node(E_owner(data))).

        Args:
            request: The validated ProofRequestMessage.
        """
        logger.info("Proof request received for blob_id=%s", request.blob_id)
        encrypted_data = self._storage.retrieve(request.blob_id)
        if encrypted_data is None:
            logger.warning("Blob not found: blob_id=%s", request.blob_id)
            response = ProofResponseMessage(
                blob_id=request.blob_id,
                node_id=self._node_id,
                proof=None,
                found=False,
            )
        else:
            # Decrypt to get E_owner(data), then compute proof
            owner_encrypted_data = self._encryption.decrypt(
                self._node_key, encrypted_data
            )
            result = self._storage.compute_proof(owner_encrypted_data, request.seed)
            logger.info("Proof computed for blob_id=%s", request.blob_id)
            response = ProofResponseMessage(
                blob_id=request.blob_id,
                node_id=self._node_id,
                proof=result,
                found=True,
            )

        self._publisher.publish(
            self._response_topic, response.model_dump_json().encode()
        )
        logger.info("Proof response published for blob_id=%s", request.blob_id)
