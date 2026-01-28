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
class FakeStorage:
    """Test double that captures storage operations."""

    stored: dict[str, bytes] = field(default_factory=dict)

    def store(self, blob_id: str, data: bytes) -> None:
        """Capture the stored data."""
        self.stored[blob_id] = data


@dataclass
class FakePublisher:
    """Test double that captures published messages."""

    published: list[tuple[str, bytes]] = field(default_factory=list)

    def publish(self, topic: str, data: bytes, **kwargs: Any) -> str:
        """Capture the published message."""
        self.published.append((topic, data))
        return "fake-message-id"


@pytest.fixture
def storage() -> FakeStorage:
    """Provide a fake storage for capturing store calls."""
    return FakeStorage()


@pytest.fixture
def publisher() -> FakePublisher:
    """Provide a fake publisher for capturing messages."""
    return FakePublisher()


@pytest.fixture
def client(storage: FakeStorage, publisher: FakePublisher) -> NodeClient:
    """Provide a NodeClient."""
    return NodeClient(
        storage=storage,  # type: ignore[arg-type]
        publisher=publisher,
        store_topic="quloud-store",
        retrieve_topic="quloud-retrieve",
        proof_topic="quloud-proof",
    )


class TestStoreBlob:
    """Tests for store_blob method."""

    def test_always_stores_locally(
        self, client: NodeClient, storage: FakeStorage
    ) -> None:
        """Client always stores data locally."""
        client.store_blob(blob_id="blob123", data=b"my data")

        assert "blob123" in storage.stored
        assert storage.stored["blob123"] == b"my data"

    @pytest.mark.parametrize("replicas", [0, 1, 2, 3, 5])
    def test_publishes_n_requests_for_n_replicas(
        self,
        client: NodeClient,
        storage: FakeStorage,
        publisher: FakePublisher,
        replicas: int,
    ) -> None:
        """Client publishes exactly n StoreRequests for n replicas."""
        client.store_blob(blob_id="test-blob", data=b"data", replicas=replicas)

        # Always stored locally
        assert "test-blob" in storage.stored

        # Exactly n remote replica requests
        assert len(publisher.published) == replicas
        for topic, msg in publisher.published:
            assert topic == "quloud-store"
            request = StoreRequestMessage.model_validate_json(msg)
            assert request.blob_id == "test-blob"
            assert request.data == b"data"

    def test_default_replicas_is_zero(
        self, client: NodeClient, publisher: FakePublisher
    ) -> None:
        """Default replicas is 0 (local only)."""
        client.store_blob(blob_id="single", data=b"data")

        assert len(publisher.published) == 0


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
