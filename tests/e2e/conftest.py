"""E2E test infrastructure for Quloud.

Real Docker RabbitMQ, real synapse adapters, real encryption and storage.
"""

import subprocess
import tempfile
import threading
import time
from pathlib import Path

import pika
import pytest

from synapse.adapters.rabbitmq import RabbitMQPublisher, RabbitMQSubscriber
from synapse.consumer.message_consumer import MessageConsumer

from quloud.adapters.encryption.pynacl_adapter import PyNaClEncryptionAdapter
from quloud.adapters.key_store.filesystem_adapter import FilesystemKeyStoreAdapter
from quloud.adapters.storage.filesystem_adapter import FilesystemStorageAdapter
from quloud.core.encryption_service import EncryptionService
from quloud.core.key_store_service import KeyStoreService
from quloud.core.storage_service import StorageService
from quloud.main import start_node
from quloud.services.message_contracts import (
    ProofResponseMessage,
    RetrieveResponseMessage,
    StoreResponseMessage,
)
from quloud.services.node_client import NodeClient
from quloud.services.proof_response_handler import ProofResponseHandler

RABBITMQ_PORT = 5672

REQUEST_QUEUES = [
    "quloud.store.requests",
    "quloud.retrieve.requests",
    "quloud.proof.requests",
    "quloud.delete.requests",
]


def _make_connection() -> pika.BlockingConnection:
    return pika.BlockingConnection(
        pika.ConnectionParameters(host="localhost", port=RABBITMQ_PORT)
    )


def _wait_for_consumers(queues: list[str], timeout: float = 5.0) -> None:
    """Block until every queue has at least one active consumer."""
    conn = _make_connection()
    ch = conn.channel()
    deadline = time.time() + timeout
    while time.time() < deadline:
        if all(
            ch.queue_declare(queue=q, passive=True).method.consumer_count > 0
            for q in queues
        ):
            conn.close()
            return
        time.sleep(0.05)
    conn.close()
    raise RuntimeError(f"Consumers not ready on {queues} within {timeout}s")


# ============================================================================
# Docker RabbitMQ
# ============================================================================


def _rabbitmq_reachable() -> bool:
    """Check if RabbitMQ is already listening on localhost."""
    try:
        conn = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost", port=RABBITMQ_PORT)
        )
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def rabbitmq_broker():
    """Ensure RabbitMQ is available for the test session.

    If RabbitMQ is already reachable (e.g. CI service container), skip
    Docker management entirely.  Otherwise start a container and tear it
    down on session end.
    """
    if _rabbitmq_reachable():
        yield
        return

    subprocess.run(["docker", "rm", "-f", "rabbitmq-quloud-test"], capture_output=True)

    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            "rabbitmq-quloud-test",
            "-p",
            f"{RABBITMQ_PORT}:5672",
            "rabbitmq:3-management",
        ],
        check=True,
        capture_output=True,
    )

    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            conn = pika.BlockingConnection(
                pika.ConnectionParameters(host="localhost", port=RABBITMQ_PORT)
            )
            conn.close()
            break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("RabbitMQ did not become ready within 30s")

    yield

    subprocess.run(["docker", "stop", "rabbitmq-quloud-test"], capture_output=True)
    subprocess.run(["docker", "rm", "rabbitmq-quloud-test"], capture_output=True)


# ============================================================================
# Storage Node
# ============================================================================


@pytest.fixture(scope="session")
def storage_dir():
    """Owner's local storage directory."""
    with tempfile.TemporaryDirectory(prefix="quloud_owner_") as d:
        yield Path(d)


@pytest.fixture(scope="session")
def replica_storage_dir():
    """Replica node's storage directory."""
    with tempfile.TemporaryDirectory(prefix="quloud_replica_") as d:
        yield Path(d)


@pytest.fixture(scope="session")
def replica_node(rabbitmq_broker, replica_storage_dir):
    """Replica node that handles network requests (store, retrieve, proof, delete)."""
    handle = start_node(
        make_connection=_make_connection,
        storage_dir=replica_storage_dir,
        node_id="replica-node",
    )

    _wait_for_consumers(REQUEST_QUEUES)

    yield handle

    for consumer in handle.consumers:
        consumer.stop()


# ============================================================================
# Owner Client
# ============================================================================


@pytest.fixture(scope="session")
def owner_client(replica_node, storage_dir):
    """Owner's NodeClient with separate local storage from the replica."""
    storage_service = StorageService(
        storage=FilesystemStorageAdapter(base_dir=storage_dir)
    )
    encryption_service = EncryptionService(encryption=PyNaClEncryptionAdapter())
    key_store_service = KeyStoreService(
        key_store=FilesystemKeyStoreAdapter(base_dir=storage_dir)
    )

    conn = _make_connection()
    publisher = RabbitMQPublisher(conn)

    return NodeClient(
        storage=storage_service,
        encryption=encryption_service,
        key_store=key_store_service,
        publisher=publisher,
        store_topic="quloud.store.requests",
        retrieve_topic="quloud.retrieve.requests",
        proof_topic="quloud.proof.requests",
        delete_topic="quloud.delete.requests",
    )


# ============================================================================
# Response Capture
# ============================================================================


class ResponseCapture:
    """Captures a single response message via threading.Event."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._response: object = None

    def callback(self, response: object) -> None:
        self._response = response
        self._event.set()

    def wait(self, timeout: float = 5.0) -> object:
        """Wait for a response. Resets state for next capture."""
        if not self._event.wait(timeout):
            raise TimeoutError(f"No response within {timeout}s")
        result = self._response
        self._response = None
        self._event.clear()
        return result


@pytest.fixture(scope="session")
def proof_capture(replica_node):
    """ProofResponseHandler wired to a MessageConsumer on proof responses."""
    capture = ResponseCapture()
    handler = ProofResponseHandler(on_response=capture.callback)

    conn = _make_connection()
    consumer = MessageConsumer(
        subscription="quloud.proof.responses",
        handler=handler,
        request_model=ProofResponseMessage,
        subscriber=RabbitMQSubscriber(conn),
    )

    consumer.start()
    threading.Thread(target=consumer.run, daemon=True).start()
    _wait_for_consumers(["quloud.proof.responses"])

    yield capture

    consumer.stop()


class StoreResponseHandler:
    """Handles StoreResponse messages via callback."""

    def __init__(self, on_response):
        self._on_response = on_response

    def handle(self, response: StoreResponseMessage) -> None:
        self._on_response(response)


@pytest.fixture(scope="session")
def store_capture(replica_node):
    """StoreResponseHandler wired to a MessageConsumer on store responses."""
    capture = ResponseCapture()
    handler = StoreResponseHandler(on_response=capture.callback)

    conn = _make_connection()
    consumer = MessageConsumer(
        subscription="quloud.store.responses",
        handler=handler,
        request_model=StoreResponseMessage,
        subscriber=RabbitMQSubscriber(conn),
    )

    consumer.start()
    threading.Thread(target=consumer.run, daemon=True).start()
    _wait_for_consumers(["quloud.store.responses"])

    yield capture

    consumer.stop()


class RetrieveResponseHandler:
    """Handles RetrieveResponse messages via callback."""

    def __init__(self, on_response):
        self._on_response = on_response

    def handle(self, response: RetrieveResponseMessage) -> None:
        self._on_response(response)


@pytest.fixture(scope="session")
def restore_capture(replica_node):
    """RetrieveResponseHandler wired to a MessageConsumer on retrieve responses."""
    capture = ResponseCapture()
    handler = RetrieveResponseHandler(on_response=capture.callback)

    conn = _make_connection()
    consumer = MessageConsumer(
        subscription="quloud.retrieve.responses",
        handler=handler,
        request_model=RetrieveResponseMessage,
        subscriber=RabbitMQSubscriber(conn),
    )

    consumer.start()
    threading.Thread(target=consumer.run, daemon=True).start()
    _wait_for_consumers(["quloud.retrieve.responses"])

    yield capture

    consumer.stop()
