"""Message protocol types for Quloud pub-sub communication."""

import base64
import json
from dataclasses import dataclass


@dataclass
class StoreRequest:
    """Request to store a blob on the network."""

    blob_id: str
    data: bytes

    def to_bytes(self) -> bytes:
        """Serialize to JSON bytes for pub-sub transport."""
        return json.dumps(
            {
                "type": "store_request",
                "blob_id": self.blob_id,
                "data": base64.b64encode(self.data).decode("ascii"),
            }
        ).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "StoreRequest":
        """Deserialize from JSON bytes."""
        parsed = json.loads(data)
        return cls(
            blob_id=parsed["blob_id"],
            data=base64.b64decode(parsed["data"]),
        )


@dataclass
class StoreResponse:
    """Response confirming blob storage."""

    blob_id: str
    node_id: str
    stored: bool

    def to_bytes(self) -> bytes:
        """Serialize to JSON bytes for pub-sub transport."""
        return json.dumps(
            {
                "type": "store_response",
                "blob_id": self.blob_id,
                "node_id": self.node_id,
                "stored": self.stored,
            }
        ).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "StoreResponse":
        """Deserialize from JSON bytes."""
        parsed = json.loads(data)
        return cls(
            blob_id=parsed["blob_id"],
            node_id=parsed["node_id"],
            stored=parsed["stored"],
        )


@dataclass
class RetrieveRequest:
    """Request to retrieve a blob from the network."""

    blob_id: str

    def to_bytes(self) -> bytes:
        """Serialize to JSON bytes for pub-sub transport."""
        return json.dumps(
            {
                "type": "retrieve_request",
                "blob_id": self.blob_id,
            }
        ).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "RetrieveRequest":
        """Deserialize from JSON bytes."""
        parsed = json.loads(data)
        return cls(blob_id=parsed["blob_id"])


@dataclass
class RetrieveResponse:
    """Response with retrieved blob data."""

    blob_id: str
    node_id: str
    data: bytes | None
    found: bool

    def to_bytes(self) -> bytes:
        """Serialize to JSON bytes for pub-sub transport."""
        return json.dumps(
            {
                "type": "retrieve_response",
                "blob_id": self.blob_id,
                "node_id": self.node_id,
                "data": base64.b64encode(self.data).decode("ascii")
                if self.data
                else None,
                "found": self.found,
            }
        ).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "RetrieveResponse":
        """Deserialize from JSON bytes."""
        parsed = json.loads(data)
        return cls(
            blob_id=parsed["blob_id"],
            node_id=parsed["node_id"],
            data=base64.b64decode(parsed["data"]) if parsed["data"] else None,
            found=parsed["found"],
        )


@dataclass
class ProofOfStorageRequest:
    """Request for proof that a node still has a blob."""

    blob_id: str
    seed: bytes

    def to_bytes(self) -> bytes:
        """Serialize to JSON bytes for pub-sub transport."""
        return json.dumps(
            {
                "type": "proof_of_storage_request",
                "blob_id": self.blob_id,
                "seed": base64.b64encode(self.seed).decode("ascii"),
            }
        ).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "ProofOfStorageRequest":
        """Deserialize from JSON bytes."""
        parsed = json.loads(data)
        return cls(
            blob_id=parsed["blob_id"],
            seed=base64.b64decode(parsed["seed"]),
        )


@dataclass
class ProofOfStorageResponse:
    """Response with proof of storage or lost indication."""

    blob_id: str
    node_id: str
    proof: bytes | None
    found: bool

    def to_bytes(self) -> bytes:
        """Serialize to JSON bytes for pub-sub transport."""
        return json.dumps(
            {
                "type": "proof_of_storage_response",
                "blob_id": self.blob_id,
                "node_id": self.node_id,
                "proof": base64.b64encode(self.proof).decode("ascii")
                if self.proof
                else None,
                "found": self.found,
            }
        ).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "ProofOfStorageResponse":
        """Deserialize from JSON bytes."""
        parsed = json.loads(data)
        return cls(
            blob_id=parsed["blob_id"],
            node_id=parsed["node_id"],
            proof=base64.b64decode(parsed["proof"]) if parsed["proof"] else None,
            found=parsed["found"],
        )
