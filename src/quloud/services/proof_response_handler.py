"""Handler for ProofOfStorageResponse messages."""

from typing import Callable

from quloud.core.messages import ProofOfStorageResponse


class ProofResponseHandler:
    """Handles ProofOfStorageResponse messages.

    Invokes callback when proof-of-storage response is received.
    """

    def __init__(self, on_response: Callable[[ProofOfStorageResponse], None]) -> None:
        """Initialize the handler.

        Args:
            on_response: Callback invoked with each ProofOfStorageResponse.
        """
        self._on_response = on_response

    def handle(self, response: ProofOfStorageResponse) -> None:
        """Handle a ProofOfStorageResponse.

        Args:
            response: The validated ProofOfStorageResponse.
        """
        self._on_response(response)
