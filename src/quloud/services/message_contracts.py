"""Pydantic message contracts for pub-sub communication.

These models define the wire format for messages sent/received via synapse.
Services convert between these contracts and domain objects.
"""

import base64
from typing import Any

from pydantic import BaseModel, field_serializer, field_validator


class StoreRequestMessage(BaseModel):
    """Wire format for store request."""

    blob_id: str
    data: bytes

    @field_serializer("data")
    @classmethod
    def serialize_data(cls, v: bytes) -> str:
        return base64.b64encode(v).decode("ascii")

    @field_validator("data", mode="before")
    @classmethod
    def validate_data(cls, v: Any) -> bytes:
        if isinstance(v, str):
            return base64.b64decode(v)
        if isinstance(v, bytes):
            return v
        raise TypeError(f"Expected str or bytes, got {type(v)}")


class StoreResponseMessage(BaseModel):
    """Wire format for store response."""

    blob_id: str
    node_id: str
    stored: bool


class RetrieveRequestMessage(BaseModel):
    """Wire format for retrieve request."""

    blob_id: str


class RetrieveResponseMessage(BaseModel):
    """Wire format for retrieve response."""

    blob_id: str
    node_id: str
    data: bytes | None
    found: bool

    @field_serializer("data")
    @classmethod
    def serialize_data(cls, v: bytes | None) -> str | None:
        if v is None:
            return None
        return base64.b64encode(v).decode("ascii")

    @field_validator("data", mode="before")
    @classmethod
    def validate_data(cls, v: Any) -> bytes | None:
        if v is None:
            return None
        if isinstance(v, str):
            return base64.b64decode(v)
        if isinstance(v, bytes):
            return v
        raise TypeError(f"Expected str, bytes, or None, got {type(v)}")


class ProofRequestMessage(BaseModel):
    """Wire format for proof of storage request."""

    blob_id: str
    seed: bytes

    @field_serializer("seed")
    @classmethod
    def serialize_seed(cls, v: bytes) -> str:
        return base64.b64encode(v).decode("ascii")

    @field_validator("seed", mode="before")
    @classmethod
    def validate_seed(cls, v: Any) -> bytes:
        if isinstance(v, str):
            return base64.b64decode(v)
        if isinstance(v, bytes):
            return v
        raise TypeError(f"Expected str or bytes, got {type(v)}")


class ProofResponseMessage(BaseModel):
    """Wire format for proof of storage response."""

    blob_id: str
    node_id: str
    proof: bytes | None
    found: bool

    @field_serializer("proof")
    @classmethod
    def serialize_proof(cls, v: bytes | None) -> str | None:
        if v is None:
            return None
        return base64.b64encode(v).decode("ascii")

    @field_validator("proof", mode="before")
    @classmethod
    def validate_proof(cls, v: Any) -> bytes | None:
        if v is None:
            return None
        if isinstance(v, str):
            return base64.b64decode(v)
        if isinstance(v, bytes):
            return v
        raise TypeError(f"Expected str, bytes, or None, got {type(v)}")
