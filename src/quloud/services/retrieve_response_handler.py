"""Handler for RetrieveResponse messages."""

from typing import Callable

from quloud.core.messages import RetrieveResponse


class RetrieveResponseHandler:
    """Handles RetrieveResponse messages.

    Invokes callback when retrieved data is received.
    """

    def __init__(self, on_response: Callable[[RetrieveResponse], None]) -> None:
        """Initialize the handler.

        Args:
            on_response: Callback invoked with each RetrieveResponse.
        """
        self._on_response = on_response

    def handle(self, response: RetrieveResponse) -> None:
        """Handle a RetrieveResponse.

        Args:
            response: The validated RetrieveResponse.
        """
        self._on_response(response)
