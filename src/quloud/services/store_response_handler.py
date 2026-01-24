"""Handler for StoreResponse messages."""

from typing import Callable

from quloud.services.message_contracts import StoreResponseMessage


class StoreResponseHandler:
    """Handles StoreResponse messages.

    Invokes callback when storage confirmation is received.
    """

    def __init__(self, on_response: Callable[[StoreResponseMessage], None]) -> None:
        """Initialize the handler.

        Args:
            on_response: Callback invoked with each StoreResponseMessage.
        """
        self._on_response = on_response

    def handle(self, response: StoreResponseMessage) -> None:
        """Handle a StoreResponse.

        Args:
            response: The validated StoreResponseMessage.
        """
        self._on_response(response)
