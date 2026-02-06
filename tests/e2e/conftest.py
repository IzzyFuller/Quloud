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

from quloud.main import start_node
from quloud.services.message_contracts import (
    ProofResponseMessage,
    RetrieveResponseMessage,
    StoreResponseMessage,
)
from quloud.services.node_client import NodeClient
from quloud.services.proof_response_handler import ProofResponseHandler

RABBITMQ_PORT = 5672


def _make_connection() -> pika.BlockingConnection:
    return pika.BlockingConnection(
        pika.ConnectionParameters(host="localhost", port=RABBITMQ_PORT)
    )


# ============================================================================
# Docker RabbitMQ
# ============================================================================


@pytest.fixture(scope="session")
def rabbitmq_broker():
    """Start RabbitMQ Docker container for test session."""
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
    """Provide temporary storage directory."""
    with tempfile.TemporaryDirectory(prefix="quloud_e2e_") as d:
        yield Path(d)


@pytest.fixture(scope="session")
def quloud_node(rabbitmq_broker, storage_dir):
    """Start a Quloud storage node using the real start_node() entry point."""
    handle = start_node(
        make_connection=_make_connection,
        storage_dir=storage_dir,
        node_id="test-node",
    )

    yield handle

    for consumer in handle.consumers:
        consumer.stop()


# ============================================================================
# Owner Client
# ============================================================================


@pytest.fixture(scope="session")
def owner_client(quloud_node, storage_dir):
    """Real NodeClient for the owner — stores locally with encryption."""
    conn = _make_connection()
    publisher = RabbitMQPublisher(conn)

    return NodeClient(
        storage=quloud_node.storage_service,
        encryption=quloud_node.encryption_service,
        key_store=quloud_node.key_store_service,
        publisher=publisher,
        store_topic="quloud.store.requests",
        retrieve_topic="quloud.retrieve.requests",
        proof_topic="quloud.proof.requests",
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

    def wait(self, timeout: float = 10.0) -> object:
        """Wait for a response. Resets state for next capture."""
        if not self._event.wait(timeout):
            raise TimeoutError(f"No response within {timeout}s")
        result = self._response
        self._response = None
        self._event.clear()
        return result


@pytest.fixture(scope="session")
def proof_capture(quloud_node):
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

    yield capture

    consumer.stop()


class StoreResponseHandler:
    """Handles StoreResponse messages via callback."""

    def __init__(self, on_response):
        self._on_response = on_response

    def handle(self, response: StoreResponseMessage) -> None:
        self._on_response(response)


@pytest.fixture(scope="session")
def store_capture(quloud_node):
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

    yield capture

    consumer.stop()


class RetrieveResponseHandler:
    """Handles RetrieveResponse messages via callback."""

    def __init__(self, on_response):
        self._on_response = on_response

    def handle(self, response: RetrieveResponseMessage) -> None:
        self._on_response(response)


@pytest.fixture(scope="session")
def retrieve_capture(quloud_node):
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

    yield capture

    consumer.stop()
