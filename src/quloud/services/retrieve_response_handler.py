"""Handler for RetrieveResponse messages."""

from typing import Callable

from quloud.services.message_contracts import RetrieveResponseMessage


class RetrieveResponseHandler:
    """Handles RetrieveResponse messages.

    Invokes callback when retrieved data is received.
    """

    def __init__(self, on_response: Callable[[RetrieveResponseMessage], None]) -> None:
        """Initialize the handler.

        Args:
            on_response: Callback invoked with each RetrieveResponseMessage.
        """
        self._on_response = on_response

    def handle(self, response: RetrieveResponseMessage) -> None:
        """Handle a RetrieveResponse.

        Args:
            response: The validated RetrieveResponseMessage.
        """
        self._on_response(response)
