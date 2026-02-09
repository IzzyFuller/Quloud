"""Handler for delete requests from the network."""

from quloud.core.key_store_service import KeyStoreService
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import DeleteRequestMessage


class DeleteRequestHandler:
    """Handles DeleteRequest messages by deleting blob data and key.

    Anonymous delete — no node_id, no response published.
    """

    def __init__(
        self,
        storage: StorageService,
        key_store: KeyStoreService,
    ) -> None:
        self._storage = storage
        self._key_store = key_store

    def handle(self, request: DeleteRequestMessage) -> None:
        self._storage.delete(request.blob_id)
        self._key_store.delete_key(request.blob_id)
