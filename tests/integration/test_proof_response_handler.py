"""Integration tests for ProofResponseHandler."""

import pytest
from dataclasses import dataclass, field

from quloud.services.proof_response_handler import ProofResponseHandler
from quloud.services.message_contracts import ProofResponseMessage


@dataclass
class ResponseCollector:
    """Test double that collects responses."""

    responses: list[ProofResponseMessage] = field(default_factory=list)

    def on_response(self, response: ProofResponseMessage) -> None:
        """Collect the response."""
        self.responses.append(response)


@pytest.fixture
def collector() -> ResponseCollector:
    """Provide a response collector."""
    return ResponseCollector()


@pytest.fixture
def handler(collector: ResponseCollector) -> ProofResponseHandler:
    """Provide a ProofResponseHandler."""
    return ProofResponseHandler(on_response=collector.on_response)


class TestProofResponseHandler:
    """Tests for ProofResponseHandler."""

    def test_invokes_callback_with_response(
        self, handler: ProofResponseHandler, collector: ResponseCollector
    ) -> None:
        """Handler invokes callback with the response."""
        response = ProofResponseMessage(
            blob_id="blob123", node_id="node-A", proof=b"proof-hash", found=True
        )

        handler.handle(response)

        assert len(collector.responses) == 1
        assert collector.responses[0].blob_id == "blob123"
        assert collector.responses[0].proof == b"proof-hash"
        assert collector.responses[0].found is True

    def test_handles_not_found_response(
        self, handler: ProofResponseHandler, collector: ResponseCollector
    ) -> None:
        """Handler passes through not-found responses (blob lost)."""
        response = ProofResponseMessage(
            blob_id="lost-blob", node_id="node-B", proof=None, found=False
        )

        handler.handle(response)

        assert len(collector.responses) == 1
        assert collector.responses[0].found is False
        assert collector.responses[0].proof is None

    def test_handles_multiple_proof_responses(
        self, handler: ProofResponseHandler, collector: ResponseCollector
    ) -> None:
        """Handler can process proofs from multiple storage nodes."""
        handler.handle(
            ProofResponseMessage(
                blob_id="blob1", node_id="node-A", proof=b"proof-A", found=True
            )
        )
        handler.handle(
            ProofResponseMessage(
                blob_id="blob1", node_id="node-B", proof=b"proof-B", found=True
            )
        )
        handler.handle(
            ProofResponseMessage(
                blob_id="blob1", node_id="node-C", proof=b"proof-C", found=True
            )
        )

        assert len(collector.responses) == 3
        node_ids = {r.node_id for r in collector.responses}
        assert node_ids == {"node-A", "node-B", "node-C"}
