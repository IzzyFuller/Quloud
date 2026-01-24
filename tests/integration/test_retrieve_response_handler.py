"""Integration tests for RetrieveResponseHandler."""

import pytest
from dataclasses import dataclass, field

from quloud.services.retrieve_response_handler import RetrieveResponseHandler
from quloud.core.messages import RetrieveResponse


@dataclass
class ResponseCollector:
    """Test double that collects responses."""

    responses: list[RetrieveResponse] = field(default_factory=list)

    def on_response(self, response: RetrieveResponse) -> None:
        """Collect the response."""
        self.responses.append(response)


@pytest.fixture
def collector() -> ResponseCollector:
    """Provide a response collector."""
    return ResponseCollector()


@pytest.fixture
def handler(collector: ResponseCollector) -> RetrieveResponseHandler:
    """Provide a RetrieveResponseHandler."""
    return RetrieveResponseHandler(on_response=collector.on_response)


class TestRetrieveResponseHandler:
    """Tests for RetrieveResponseHandler."""

    def test_invokes_callback_with_response(
        self, handler: RetrieveResponseHandler, collector: ResponseCollector
    ) -> None:
        """Handler invokes callback with the response."""
        response = RetrieveResponse(
            blob_id="blob123", node_id="node-A", data=b"my data", found=True
        )

        handler.handle(response)

        assert len(collector.responses) == 1
        assert collector.responses[0].blob_id == "blob123"
        assert collector.responses[0].data == b"my data"
        assert collector.responses[0].found is True

    def test_handles_not_found_response(
        self, handler: RetrieveResponseHandler, collector: ResponseCollector
    ) -> None:
        """Handler passes through not-found responses."""
        response = RetrieveResponse(
            blob_id="missing", node_id="node-B", data=None, found=False
        )

        handler.handle(response)

        assert len(collector.responses) == 1
        assert collector.responses[0].found is False
        assert collector.responses[0].data is None

    def test_handles_multiple_responses(
        self, handler: RetrieveResponseHandler, collector: ResponseCollector
    ) -> None:
        """Handler can process multiple responses from different nodes."""
        handler.handle(
            RetrieveResponse(
                blob_id="blob1", node_id="node-A", data=b"data", found=True
            )
        )
        handler.handle(
            RetrieveResponse(
                blob_id="blob1", node_id="node-B", data=b"data", found=True
            )
        )

        assert len(collector.responses) == 2
