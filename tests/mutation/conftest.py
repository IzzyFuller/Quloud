"""Fork-safe mutation test infrastructure for Quloud.

Replaces RabbitMQ transport with a synchronous InMemoryBus, and PyNaCl
with a pure-Python encryption adapter. No C extensions, no threads,
no state to corrupt across fork boundaries.
"""

from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from quloud.adapters.key_store.filesystem_adapter import FilesystemKeyStoreAdapter
from quloud.adapters.storage.filesystem_adapter import FilesystemStorageAdapter
from quloud.core.encryption_service import EncryptionService
from quloud.core.key_store_service import KeyStoreService
from quloud.core.storage_service import StorageService
from quloud.services.delete_request_handler import DeleteRequestHandler
from quloud.services.message_contracts import (
    DeleteRequestMessage,
    ProofRequestMessage,
    RetrieveRequestMessage,
    StoreRequestMessage,
)
from quloud.services.node_client import NodeClient
from quloud.services.proof_request_handler import ProofRequestHandler
from quloud.services.retrieve_request_handler import RetrieveRequestHandler
from quloud.services.store_request_handler import StoreRequestHandler


# ============================================================================
# Pure-Python encryption adapter — no C extensions, fork-safe
# ============================================================================


class PurePythonEncryptionAdapter:
    """Stdlib-only encryption that satisfies EncryptionProtocol.

    Uses SHA-256 CTR keystream for reversible encrypt/decrypt.
    Not cryptographically serious — but exercises the same code paths
    as PyNaCl without pulling in libsodium (which segfaults after fork).
    """

    def generate_key(self) -> bytes:
        return os.urandom(32)

    def encrypt(self, key: bytes, plaintext: bytes) -> bytes:
        nonce = os.urandom(24)
        stream = self._keystream(key, nonce, len(plaintext))
        ciphertext = bytes(a ^ b for a, b in zip(plaintext, stream))
        return nonce + ciphertext

    def decrypt(self, key: bytes, ciphertext: bytes) -> bytes:
        nonce = ciphertext[:24]
        ct = ciphertext[24:]
        stream = self._keystream(key, nonce, len(ct))
        return bytes(a ^ b for a, b in zip(ct, stream))

    @staticmethod
    def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
        stream = b""
        counter = 0
        while len(stream) < length:
            block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
            stream += block
            counter += 1
        return stream[:length]


# ============================================================================
# InMemoryBus — synchronous message router
# ============================================================================


class _InMemoryPublisher:
    """Publisher that satisfies PubSubPublisher by routing through the bus."""

    def __init__(self, bus: InMemoryBus) -> None:
        self._bus = bus

    def publish(self, topic: str, data: bytes, **kwargs: Any) -> None:
        self._bus._on_publish(topic, data)


class InMemoryBus:
    """Synchronous in-process message bus.

    Handlers are called inline on publish — no threads, no connections,
    no state to corrupt across fork boundaries.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, tuple[object, type[BaseModel]]] = {}
        self._responses: dict[str, list[bytes]] = defaultdict(list)

    def subscribe(
        self, topic: str, handler: object, request_model: type[BaseModel]
    ) -> None:
        """Register a handler for a topic.

        Args:
            topic: The topic to subscribe to.
            handler: Object with a .handle(request) method.
            request_model: Pydantic model to deserialize incoming data.
        """
        self._handlers[topic] = (handler, request_model)

    def publisher(self) -> _InMemoryPublisher:
        """Return a publisher that satisfies PubSubPublisher."""
        return _InMemoryPublisher(self)

    def _on_publish(self, topic: str, data: bytes) -> None:
        """Route a published message.

        If a handler is registered for this topic, deserialize and call it.
        Otherwise, capture the raw bytes in _responses for later retrieval.
        """
        if topic in self._handlers:
            handler, model = self._handlers[topic]
            request = model.model_validate_json(data)
            handler.handle(request)
        else:
            self._responses[topic].append(data)

    def pop_response(self, topic: str, model: type[BaseModel]) -> BaseModel:
        """Pop and deserialize the first captured response for a topic.

        Args:
            topic: The response topic to read from.
            model: Pydantic model to deserialize the response.

        Returns:
            Deserialized response message.

        Raises:
            IndexError: If no response has been captured for this topic.
        """
        data = self._responses[topic].pop(0)
        return model.model_validate_json(data)


# ============================================================================
# Fixtures — all function-scoped, fork-safe
# ============================================================================


@pytest.fixture()
def bus() -> InMemoryBus:
    """Fresh in-memory bus for each test."""
    return InMemoryBus()


@pytest.fixture()
def storage_dir(tmp_path: Path) -> Path:
    """Owner's local storage directory."""
    d = tmp_path / "owner"
    d.mkdir()
    return d


@pytest.fixture()
def replica_storage_dir(tmp_path: Path) -> Path:
    """Replica node's storage directory."""
    d = tmp_path / "replica"
    d.mkdir()
    return d


@pytest.fixture()
def replica_node(bus: InMemoryBus, replica_storage_dir: Path) -> None:
    """Wire up the 4 request handlers with real services, subscribed to bus.

    No threads, no connections — handlers are called synchronously.
    """
    storage_service = StorageService(
        storage=FilesystemStorageAdapter(base_dir=replica_storage_dir)
    )
    encryption_service = EncryptionService(encryption=PurePythonEncryptionAdapter())
    key_store_service = KeyStoreService(
        key_store=FilesystemKeyStoreAdapter(base_dir=replica_storage_dir)
    )

    publisher = bus.publisher()

    store_handler = StoreRequestHandler(
        storage=storage_service,
        encryption=encryption_service,
        key_store=key_store_service,
        publisher=publisher,
        node_id="replica-node",
        response_topic="quloud.store.responses",
    )
    retrieve_handler = RetrieveRequestHandler(
        storage=storage_service,
        encryption=encryption_service,
        key_store=key_store_service,
        publisher=publisher,
        node_id="replica-node",
        response_topic="quloud.retrieve.responses",
    )
    proof_handler = ProofRequestHandler(
        storage=storage_service,
        encryption=encryption_service,
        key_store=key_store_service,
        publisher=publisher,
        node_id="replica-node",
        response_topic="quloud.proof.responses",
    )
    delete_handler = DeleteRequestHandler(
        storage=storage_service,
        key_store=key_store_service,
    )

    bus.subscribe("quloud.store.requests", store_handler, StoreRequestMessage)
    bus.subscribe("quloud.retrieve.requests", retrieve_handler, RetrieveRequestMessage)
    bus.subscribe("quloud.proof.requests", proof_handler, ProofRequestMessage)
    bus.subscribe("quloud.delete.requests", delete_handler, DeleteRequestMessage)


@pytest.fixture()
def owner_client(bus: InMemoryBus, replica_node: None, storage_dir: Path) -> NodeClient:
    """Owner's NodeClient with real services and bus publisher."""
    storage_service = StorageService(
        storage=FilesystemStorageAdapter(base_dir=storage_dir)
    )
    encryption_service = EncryptionService(encryption=PurePythonEncryptionAdapter())
    key_store_service = KeyStoreService(
        key_store=FilesystemKeyStoreAdapter(base_dir=storage_dir)
    )

    return NodeClient(
        storage=storage_service,
        encryption=encryption_service,
        key_store=key_store_service,
        publisher=bus.publisher(),
        store_topic="quloud.store.requests",
        retrieve_topic="quloud.retrieve.requests",
        proof_topic="quloud.proof.requests",
        delete_topic="quloud.delete.requests",
    )


@pytest.fixture()
def bus_response(bus: InMemoryBus):
    """Helper to pop typed responses from bus."""

    def _pop(topic: str, model: type[BaseModel]) -> BaseModel:
        return bus.pop_response(topic, model)

    return _pop
