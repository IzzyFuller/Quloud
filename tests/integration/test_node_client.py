"""Integration tests for NodeClient."""

import pytest
from dataclasses import dataclass, field
from typing import Any

from quloud.services.node_client import NodeClient
from quloud.services.message_contracts import (
    StoreRequestMessage,
    RetrieveRequestMessage,
    ProofRequestMessage,
)


@dataclass
class FakePublisher:
    """Test double that captures published messages."""

    published: list[tuple[str, bytes]] = field(default_factory=list)

    def publish(self, topic: str, data: bytes, **kwargs: Any) -> str:
        """Capture the published message."""
        self.published.append((topic, data))
        return "fake-message-id"


@pytest.fixture
def publisher() -> FakePublisher:
    """Provide a fake publisher for capturing messages."""
    return FakePublisher()


@pytest.fixture
def client(publisher: FakePublisher) -> NodeClient:
    """Provide a NodeClient."""
    return NodeClient(
        publisher=publisher,
        store_topic="quloud-store",
        retrieve_topic="quloud-retrieve",
        proof_topic="quloud-proof",
    )


class TestStoreBlob:
    """Tests for store_blob method."""

    def test_publishes_store_request(
        self, client: NodeClient, publisher: FakePublisher
    ) -> None:
        """Client publishes StoreRequest when storing."""
        client.store_blob(blob_id="blob123", data=b"my data")

        assert len(publisher.published) == 1
        topic, data = publisher.published[0]
        assert topic == "quloud-store"
        request = StoreRequestMessage.model_validate_json(data)
        assert request.blob_id == "blob123"
        assert request.data == b"my data"

    def test_publishes_n_requests_for_duplicates(
        self, client: NodeClient, publisher: FakePublisher
    ) -> None:
        """Client publishes n StoreRequests when duplicates specified."""
        client.store_blob(blob_id="blob456", data=b"redundant", duplicates=3)

        assert len(publisher.published) == 3
        for topic, data in publisher.published:
            assert topic == "quloud-store"
            request = StoreRequestMessage.model_validate_json(data)
            assert request.blob_id == "blob456"
            assert request.data == b"redundant"

    def test_default_duplicates_is_one(
        self, client: NodeClient, publisher: FakePublisher
    ) -> None:
        """Default duplicates is 1 (single copy)."""
        client.store_blob(blob_id="single", data=b"data")

        assert len(publisher.published) == 1


class TestRetrieveBlob:
    """Tests for retrieve_blob method."""

    def test_publishes_retrieve_request(
        self, client: NodeClient, publisher: FakePublisher
    ) -> None:
        """Client publishes RetrieveRequest when retrieving."""
        client.retrieve_blob(blob_id="blob789")

        assert len(publisher.published) == 1
        topic, data = publisher.published[0]
        assert topic == "quloud-retrieve"
        request = RetrieveRequestMessage.model_validate_json(data)
        assert request.blob_id == "blob789"


class TestRequestProof:
    """Tests for request_proof method."""

    def test_publishes_proof_request(
        self, client: NodeClient, publisher: FakePublisher
    ) -> None:
        """Client publishes ProofOfStorageRequest when requesting proof."""
        seed = b"challenge-seed"
        client.request_proof(blob_id="proof-blob", seed=seed)

        assert len(publisher.published) == 1
        topic, data = publisher.published[0]
        assert topic == "quloud-proof"
        request = ProofRequestMessage.model_validate_json(data)
        assert request.blob_id == "proof-blob"
        assert request.seed == seed
