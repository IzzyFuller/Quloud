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

    def test_no_publish_when_zero_replicas(
        self, client: NodeClient, publisher: FakePublisher
    ) -> None:
        """Client does not publish when replicas=0 (local only)."""
        client.store_blob(blob_id="local-only", data=b"data", replicas=0)

        assert len(publisher.published) == 0

    def test_publishes_n_requests_for_replicas(
        self, client: NodeClient, storage: FakeStorage, publisher: FakePublisher
    ) -> None:
        """Client publishes n StoreRequests for n replicas."""
        client.store_blob(blob_id="blob456", data=b"redundant", replicas=3)

        # Always stored locally
        assert "blob456" in storage.stored

        # Plus 3 remote replicas
        assert len(publisher.published) == 3
        for topic, data in publisher.published:
            assert topic == "quloud-store"
            request = StoreRequestMessage.model_validate_json(data)
            assert request.blob_id == "blob456"
            assert request.data == b"redundant"

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
