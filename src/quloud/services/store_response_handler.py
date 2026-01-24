"""Handler for StoreResponse messages."""

from typing import Callable

from quloud.core.messages import StoreResponse


class StoreResponseHandler:
    """Handles StoreResponse messages.

    Invokes callback when storage confirmation is received.
    """

    def __init__(self, on_response: Callable[[StoreResponse], None]) -> None:
        """Initialize the handler.

        Args:
            on_response: Callback invoked with each StoreResponse.
        """
        self._on_response = on_response

    def handle(self, response: StoreResponse) -> None:
        """Handle a StoreResponse.

        Args:
            response: The validated StoreResponse.
        """
        self._on_response(response)
