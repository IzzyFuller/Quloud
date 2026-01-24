"""Quloud storage node entry point.

Wires up all components and runs the message consumers.
"""

import os
import signal
import threading
import uuid

import pika

from synapse.adapters.rabbitmq import RabbitMQPublisher, RabbitMQSubscriber
from synapse.consumer.message_consumer import MessageConsumer

from quloud.adapters.storage.filesystem_adapter import FilesystemStorageAdapter
from quloud.core.storage_service import StorageService
from quloud.services.message_contracts import (
    StoreRequestMessage,
    RetrieveRequestMessage,
    ProofRequestMessage,
)
from quloud.services.store_request_handler import StoreRequestHandler
from quloud.services.retrieve_request_handler import RetrieveRequestHandler
from quloud.services.proof_request_handler import ProofRequestHandler


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
    ]
    for queue in queues:
        channel.queue_declare(queue=queue, durable=True)


def main() -> None:
    """Run the quloud storage node."""
    # Configuration from environment
    node_id = os.environ.get("NODE_ID", f"node-{uuid.uuid4().hex[:8]}")
    storage_dir = os.environ.get("STORAGE_DIR", "./data")

    print(f"Starting Quloud node: {node_id}")
    print(f"Storage directory: {storage_dir}")

    # Create RabbitMQ connection and setup queues
    connection = create_rabbitmq_connection()
    channel = connection.channel()
    setup_queues(channel)

    # Create adapters
    storage_adapter = FilesystemStorageAdapter(base_dir=storage_dir)
    publisher = RabbitMQPublisher(connection)

    # Create services
    storage_service = StorageService(storage=storage_adapter)

    # Create request handlers (storage node side)
    store_handler = StoreRequestHandler(
        storage=storage_service,
        publisher=publisher,
        node_id=node_id,
        response_topic="quloud.store.responses",
    )
    retrieve_handler = RetrieveRequestHandler(
        storage=storage_service,
        publisher=publisher,
        node_id=node_id,
        response_topic="quloud.retrieve.responses",
    )
    proof_handler = ProofRequestHandler(
        storage=storage_service,
        publisher=publisher,
        node_id=node_id,
        response_topic="quloud.proof.responses",
    )

    # Create subscribers (one per consumer for thread safety)
    store_subscriber = RabbitMQSubscriber(create_rabbitmq_connection())
    retrieve_subscriber = RabbitMQSubscriber(create_rabbitmq_connection())
    proof_subscriber = RabbitMQSubscriber(create_rabbitmq_connection())

    # Create message consumers
    store_consumer = MessageConsumer(
        subscription="quloud.store.requests",
        handler=store_handler,
        request_model=StoreRequestMessage,
        subscriber=store_subscriber,
    )
    retrieve_consumer = MessageConsumer(
        subscription="quloud.retrieve.requests",
        handler=retrieve_handler,
        request_model=RetrieveRequestMessage,
        subscriber=retrieve_subscriber,
    )
    proof_consumer = MessageConsumer(
        subscription="quloud.proof.requests",
        handler=proof_handler,
        request_model=ProofRequestMessage,
        subscriber=proof_subscriber,
    )

    consumers = [store_consumer, retrieve_consumer, proof_consumer]

    # Signal handler for graceful shutdown
    def shutdown(signum: int, frame: object) -> None:
        print("\nShutting down...")
        for consumer in consumers:
            consumer.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start consumers in threads
    threads = []
    for consumer in consumers:
        consumer.start()
        thread = threading.Thread(target=consumer.run, daemon=True)
        thread.start()
        threads.append(thread)

    print("Listening for messages on queues:")
    print("  - quloud.store.requests")
    print("  - quloud.retrieve.requests")
    print("  - quloud.proof.requests")

    # Wait for threads
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        pass

    print("Node stopped.")


if __name__ == "__main__":
    main()
