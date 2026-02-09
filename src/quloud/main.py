"""Quloud storage node entry point.

Wires up all components and runs the message consumers.
"""

import logging
import os
import signal
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pika

from synapse.adapters.rabbitmq import RabbitMQPublisher, RabbitMQSubscriber
from synapse.consumer.message_consumer import MessageConsumer

from quloud.adapters.encryption.pynacl_adapter import PyNaClEncryptionAdapter
from quloud.adapters.key_store.filesystem_adapter import FilesystemKeyStoreAdapter
from quloud.adapters.storage.filesystem_adapter import FilesystemStorageAdapter
from quloud.core.encryption_service import EncryptionService
from quloud.core.key_store_service import KeyStoreService
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import (
    DeleteRequestMessage,
    StoreRequestMessage,
    RetrieveRequestMessage,
    ProofRequestMessage,
)
from quloud.services.delete_request_handler import DeleteRequestHandler
from quloud.services.store_request_handler import StoreRequestHandler
from quloud.services.retrieve_request_handler import RetrieveRequestHandler
from quloud.services.proof_request_handler import ProofRequestHandler

logger = logging.getLogger(__name__)


class NodeHandle(NamedTuple):
    """Everything returned by start_node for cleanup and further wiring."""

    consumers: list[MessageConsumer]
    threads: list[threading.Thread]
    storage_service: StorageService
    encryption_service: EncryptionService
    key_store_service: KeyStoreService


def create_rabbitmq_connection() -> pika.BlockingConnection:
    """Create RabbitMQ connection from environment variables."""
    host = os.environ.get("RABBITMQ_HOST", "localhost")
    port = int(os.environ.get("RABBITMQ_PORT", "5672"))
    user = os.environ.get("RABBITMQ_USER", "guest")
    password = os.environ.get("RABBITMQ_PASSWORD", "guest")

    credentials = pika.PlainCredentials(user, password)
    parameters = pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials,
        heartbeat=60,
    )
    return pika.BlockingConnection(parameters)


def setup_queues(channel: pika.channel.Channel) -> None:
    """Declare all required queues."""
    queues = [
        "quloud.store.requests",
        "quloud.store.responses",
        "quloud.retrieve.requests",
        "quloud.retrieve.responses",
        "quloud.proof.requests",
        "quloud.proof.responses",
        "quloud.delete.requests",
    ]
    for queue in queues:
        channel.queue_declare(queue=queue, durable=True)


def start_node(
    make_connection: Callable[[], pika.BlockingConnection],
    storage_dir: str | Path,
    node_id: str = "node",
) -> NodeHandle:
    """Wire up and start a Quloud storage node.

    Args:
        make_connection: Factory for creating RabbitMQ connections.
        storage_dir: Directory for local blob storage.
        node_id: Unique identifier for this node.

    Returns:
        NodeHandle with consumers, threads, and services for cleanup.
    """
    # Create adapters
    storage_adapter = FilesystemStorageAdapter(base_dir=storage_dir)
    encryption_adapter = PyNaClEncryptionAdapter()
    key_store_adapter = FilesystemKeyStoreAdapter(base_dir=storage_dir)

    # Create services
    storage_service = StorageService(storage=storage_adapter)
    encryption_service = EncryptionService(encryption=encryption_adapter)
    key_store_service = KeyStoreService(key_store=key_store_adapter)

    # Setup queues on a dedicated connection
    setup_connection = make_connection()
    setup_queues(setup_connection.channel())
    setup_connection.close()

    # Each handler gets its own connection to avoid idle timeouts
    store_connection = make_connection()
    store_subscriber = RabbitMQSubscriber(store_connection)
    store_publisher = RabbitMQPublisher(store_connection)

    retrieve_connection = make_connection()
    retrieve_subscriber = RabbitMQSubscriber(retrieve_connection)
    retrieve_publisher = RabbitMQPublisher(retrieve_connection)

    proof_connection = make_connection()
    proof_subscriber = RabbitMQSubscriber(proof_connection)
    proof_publisher = RabbitMQPublisher(proof_connection)

    delete_connection = make_connection()
    delete_subscriber = RabbitMQSubscriber(delete_connection)

    # Create request handlers
    store_handler = StoreRequestHandler(
        storage=storage_service,
        encryption=encryption_service,
        key_store=key_store_service,
        publisher=store_publisher,
        node_id=node_id,
        response_topic="quloud.store.responses",
    )
    retrieve_handler = RetrieveRequestHandler(
        storage=storage_service,
        encryption=encryption_service,
        key_store=key_store_service,
        publisher=retrieve_publisher,
        node_id=node_id,
        response_topic="quloud.retrieve.responses",
    )
    proof_handler = ProofRequestHandler(
        storage=storage_service,
        encryption=encryption_service,
        key_store=key_store_service,
        publisher=proof_publisher,
        node_id=node_id,
        response_topic="quloud.proof.responses",
    )
    delete_handler = DeleteRequestHandler(
        storage=storage_service,
        key_store=key_store_service,
    )

    # Create and start message consumers
    consumers = [
        MessageConsumer(
            subscription="quloud.store.requests",
            handler=store_handler,
            request_model=StoreRequestMessage,
            subscriber=store_subscriber,
        ),
        MessageConsumer(
            subscription="quloud.retrieve.requests",
            handler=retrieve_handler,
            request_model=RetrieveRequestMessage,
            subscriber=retrieve_subscriber,
        ),
        MessageConsumer(
            subscription="quloud.proof.requests",
            handler=proof_handler,
            request_model=ProofRequestMessage,
            subscriber=proof_subscriber,
        ),
        MessageConsumer(
            subscription="quloud.delete.requests",
            handler=delete_handler,
            request_model=DeleteRequestMessage,
            subscriber=delete_subscriber,
        ),
    ]

    threads = []
    for consumer in consumers:
        consumer.start()
        thread = threading.Thread(target=consumer.run, daemon=True)
        thread.start()
        threads.append(thread)

    logger.info("Node %s listening on request queues", node_id)

    return NodeHandle(
        consumers=consumers,
        threads=threads,
        storage_service=storage_service,
        encryption_service=encryption_service,
        key_store_service=key_store_service,
    )


def main() -> None:
    """Run the quloud storage node."""
    node_id = os.environ.get("NODE_ID", f"node-{uuid.uuid4().hex[:8]}")
    storage_dir = os.environ.get("STORAGE_DIR", "./data")

    logger.info("Starting Quloud node: %s", node_id)
    logger.info("Storage directory: %s", storage_dir)

    handle = start_node(
        make_connection=create_rabbitmq_connection,
        storage_dir=storage_dir,
        node_id=node_id,
    )

    # Signal handler for graceful shutdown
    def shutdown(signum: int, frame: object) -> None:
        logger.info("Shutting down...")
        for consumer in handle.consumers:
            consumer.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for threads
    try:
        for thread in handle.threads:
            thread.join()
    except KeyboardInterrupt:
        pass

    logger.info("Node stopped.")


if __name__ == "__main__":
    main()
