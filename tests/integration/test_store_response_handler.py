"""Integration tests for StoreResponseHandler."""

import pytest
from dataclasses import dataclass, field

from quloud.services.store_response_handler import StoreResponseHandler
from quloud.core.messages import StoreResponse


@dataclass
class ResponseCollector:
    """Test double that collects responses."""

    responses: list[StoreResponse] = field(default_factory=list)

    def on_response(self, response: StoreResponse) -> None:
        """Collect the response."""
        self.responses.append(response)


@pytest.fixture
def collector() -> ResponseCollector:
    """Provide a response collector."""
    return ResponseCollector()


@pytest.fixture
def handler(collector: ResponseCollector) -> StoreResponseHandler:
    """Provide a StoreResponseHandler."""
    return StoreResponseHandler(on_response=collector.on_response)


class TestStoreResponseHandler:
    """Tests for StoreResponseHandler."""

    def test_invokes_callback_with_response(
        self, handler: StoreResponseHandler, collector: ResponseCollector
    ) -> None:
        """Handler invokes callback with the response."""
        response = StoreResponse(blob_id="blob123", node_id="node-A", stored=True)

        handler.handle(response)

        assert len(collector.responses) == 1
        assert collector.responses[0].blob_id == "blob123"
        assert collector.responses[0].node_id == "node-A"
        assert collector.responses[0].stored is True

    def test_handles_multiple_responses(
        self, handler: StoreResponseHandler, collector: ResponseCollector
    ) -> None:
        """Handler can process multiple responses."""
        handler.handle(StoreResponse(blob_id="blob1", node_id="node-A", stored=True))
        handler.handle(StoreResponse(blob_id="blob1", node_id="node-B", stored=True))
        handler.handle(StoreResponse(blob_id="blob1", node_id="node-C", stored=True))

        assert len(collector.responses) == 3
        node_ids = {r.node_id for r in collector.responses}
        assert node_ids == {"node-A", "node-B", "node-C"}

    def test_handles_failed_store_response(
        self, handler: StoreResponseHandler, collector: ResponseCollector
    ) -> None:
        """Handler passes through failed store responses."""
        response = StoreResponse(blob_id="blob456", node_id="node-X", stored=False)

        handler.handle(response)

        assert len(collector.responses) == 1
        assert collector.responses[0].stored is False
