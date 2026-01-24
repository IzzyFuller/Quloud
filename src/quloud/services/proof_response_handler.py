"""Handler for ProofOfStorageResponse messages."""

from typing import Callable

from quloud.services.message_contracts import ProofResponseMessage


class ProofResponseHandler:
    """Handles ProofOfStorageResponse messages.

    Invokes callback when proof-of-storage response is received.
    """

    def __init__(self, on_response: Callable[[ProofResponseMessage], None]) -> None:
        """Initialize the handler.

        Args:
            on_response: Callback invoked with each ProofResponseMessage.
        """
        self._on_response = on_response

    def handle(self, response: ProofResponseMessage) -> None:
        """Handle a ProofOfStorageResponse.

        Args:
            response: The validated ProofResponseMessage.
        """
        self._on_response(response)
