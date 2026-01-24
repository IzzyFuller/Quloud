# Quloud Technical Research

This document tracks potential technologies, libraries, and implementation approaches under consideration. All items here are research targets - not decisions.

## Pub-Sub Infrastructure

The message-driven architecture requires a pub-sub system that supports:
- Message durability (hold until N ACKs received)
- Quorum-based acknowledgment
- Topic-based routing
- Both LAN and WAN deployment

### Options Under Investigation

#### NATS with JetStream
- **Pros**: Streaming + durable messages, built-in ACK tracking, lightweight
- **Cons**: Requires NATS server infrastructure
- **Python Support**: `nats.py` library available
- **Quorum Support**: Can configure streams with acknowledgment requirements
- **Use Case**: Production-ready for both LAN and internet deployment

#### Apache Pulsar
- **Pros**: Enterprise-grade, multi-tenancy, geo-replication
- **Cons**: Heavy infrastructure, complex setup
- **Python Support**: Official `pulsar-client` library
- **Quorum Support**: Native quorum ACK support
- **Use Case**: Large-scale deployments

#### Redis Streams
- **Pros**: Simple, widely deployed, familiar to many developers
- **Cons**: Not designed for large-scale pub-sub, persistence challenges
- **Python Support**: `redis-py` with streams support
- **Quorum Support**: Manual implementation required
- **Use Case**: Development, small-scale deployments

#### Nostr Relays
- **Pros**: Decentralized, censorship-resistant, no infrastructure to manage
- **Cons**: No built-in quorum support, requires custom ACK logic, relay availability varies
- **Python Support**: `python-nostr` library available
- **Quorum Support**: Must implement application-level tracking
- **Use Case**: Fully decentralized deployment, privacy-focused scenarios

#### Custom Gossip Protocol
- **Pros**: Full control, minimal dependencies
- **Cons**: Significant development effort, need to solve coordination problems
- **Python Support**: Build from scratch with `asyncio`
- **Quorum Support**: Custom implementation
- **Use Case**: Research, highly specialized requirements

### LAN-Specific Options

For local network deployments:
- **mDNS + UDP Multicast**: Simple discovery and broadcast
- **WebSocket Relay**: Lightweight broker running on one node
- **ZeroMQ**: Distributed messaging without central broker

## Zero-Knowledge Proof Libraries

ZKP implementation for ownership verification and future proof-of-storage.

### Options Under Investigation

#### Circom + SnarkJS
- **Type**: Circuit-based ZKP (zk-SNARKs)
- **Language**: Circom circuits, JavaScript/WASM runtime
- **Python Integration**: Run via subprocess or WASM
- **Maturity**: Widely used in production (e.g., zkSync, Polygon)
- **Use Case**: Full ZKP circuits for ownership and storage proofs

#### py_ecc
- **Type**: Elliptic curve cryptography library
- **Features**: BLS signatures, pairing-based crypto
- **Python Native**: Yes, pure Python
- **Maturity**: Used by Ethereum 2.0
- **Use Case**: Building blocks for custom ZKP implementations

#### circompy
- **Type**: Python wrapper for Circom
- **Features**: Compile and execute Circom circuits from Python
- **Python Native**: Yes, but depends on Circom toolchain
- **Maturity**: Experimental
- **Use Case**: If we want Circom circuits with Python integration

#### Halo2
- **Type**: zkSNARK library (no trusted setup)
- **Language**: Rust
- **Python Integration**: Via PyO3 bindings
- **Maturity**: Production-ready (used by Zcash)
- **Use Case**: Long-term production ZKP implementation

### Phase 1: HMAC-Based Proof (MVP)

For initial implementation, use standard HMAC instead of full ZKP:
```python
proof = HMAC-SHA256(node_key, chunk_id + E_owner(data) + challenge_seed)
```

**Advantages:**
- No ZKP library needed
- Fast computation
- Simple to verify
- Proves possession of data + node key

**Limitations:**
- Verifier must have the data to validate
- Not zero-knowledge (but acceptable for owner-initiated audit)

**Migration Path:**
- Start with HMAC for MVP
- Design ZKP circuit for ownership proof
- Implement zkPoR (Zero-Knowledge Proof of Retrievability) for future

## Cryptography Libraries

### For Multi-Layer Encryption

#### cryptography (Python)
- **Features**: Modern cryptographic primitives, well-maintained
- **Algorithms**: AES, ChaCha20, RSA, ECC
- **Status**: Industry standard for Python
- **Use Case**: Primary encryption library

#### libsodium (via PyNaCl)
- **Features**: High-level crypto API, designed for ease of use
- **Algorithms**: XSalsa20, Poly1305, Ed25519
- **Status**: Battle-tested
- **Use Case**: Alternative to cryptography, simpler API

## Network Protocol Libraries

For implementing node communication (after pub-sub infrastructure):

### aiohttp
- **Type**: Async HTTP client/server
- **Use Case**: RESTful API for node endpoints (if needed)
- **Status**: Mature, widely used

### websockets
- **Type**: WebSocket implementation for Python
- **Use Case**: Persistent connections for real-time communication
- **Status**: Standard library in Python 3.11+

### QUIC (aioquic)
- **Type**: Next-gen transport protocol (HTTP/3)
- **Features**: Low latency, built-in encryption
- **Status**: Experimental but promising
- **Use Case**: Future optimization for fast retrieval

## Message Format

JSON for initial implementation, MessagePack or Protocol Buffers for optimization.

### Message Schemas (Draft)

```json
// store_request
{
  "type": "store_request",
  "chunk_id": "sha256(...)",
  "data": "base64(E_owner(chunk))",
  "zkp": "0x...",
  "quorum": 3,
  "ttl": 31536000,
  "timestamp": 1740123456,
  "signature": "sig(...)"
}

// store_ack
{
  "type": "store_ack",
  "chunk_id": "abc123",
  "node_id": "pubkey_...",
  "timestamp": 1740123460,
  "signature": "sig(...)"
}

// retrieve_request
{
  "type": "retrieve_request",
  "chunk_id": "abc123",
  "zkp": "0x...",
  "timestamp": 1740123456,
  "signature": "sig(...)"
}

// retrieve_response
{
  "type": "retrieve_response",
  "chunk_id": "abc123",
  "data": "base64(E_owner(chunk))",
  "node_id": "pubkey_...",
  "signature": "sig(...)"
}

// proof_of_storage_request
{
  "type": "proof_of_storage_request",
  "chunk_id": "abc123",
  "challenge_seed": "rand_...",
  "timestamp": 1740123456,
  "signature": "sig(...)"
}

// proof_of_storage_response
{
  "type": "proof_of_storage_response",
  "chunk_id": "abc123",
  "node_id": "pubkey_...",
  "proof": "hmac(...)",
  "timestamp": 1740123460,
  "signature": "sig(...)"
}
```

## Storage Backend

Local storage abstraction - support multiple backends:

### Options
- **Filesystem**: Simple, universal, good for MVP
- **SQLite**: Lightweight database, built-in indexing
- **LevelDB/RocksDB**: Key-value store, high performance
- **S3-Compatible**: MinIO, Garage for distributed setups

### Chunking Strategies
- **Fixed-size chunks**: Simple, predictable (e.g., 1MB chunks)
- **Rabin fingerprinting**: Content-defined chunking, better deduplication
- **Library**: `fastcdc` (Python implementation of FastCDC)

## Testing Infrastructure

### Unit Testing
- **pytest**: Standard Python testing framework
- **pytest-asyncio**: For async code testing
- **hypothesis**: Property-based testing

### Integration Testing
- **testcontainers**: Spin up pub-sub infrastructure for tests
- **Factory fixtures**: Pattern from deep-agent-service project
- **Mock at boundaries**: Only mock network calls, use real types

### Performance Testing
- **locust**: Load testing framework
- **metrics**: Track latency, throughput, storage overhead

## Evaluation Criteria

When choosing between options, prioritize:

1. **Simplicity for MVP** - Can we get a working prototype quickly?
2. **Production viability** - Is this sustainable long-term?
3. **Decentralization** - Does it align with trustless philosophy?
4. **Python ecosystem** - Good library support and documentation?
5. **Performance** - Acceptable latency for user experience?

## Implementation Phases

### Phase 1: MVP (HMAC + Simple Pub-Sub)
- Choose lightweight pub-sub (Redis Streams or NATS)
- HMAC-based proof-of-storage
- File-based storage backend
- Fixed-size chunking
- Simple JSON messages

### Phase 2: Production Hardening
- Evaluate production pub-sub (NATS JetStream or Pulsar)
- Add reputation system
- Implement retry logic and failure handling
- Performance optimization

### Phase 3: Advanced Features
- Implement full ZKP circuits
- zkPoR for storage proofs
- Content-defined chunking
- Multiple storage backend support
- Incentive mechanisms (optional)

## References

### Academic Papers
- "Proofs of Retrievability" (Juels & Kaliski)
- "Zero-Knowledge Proofs" (Goldwasser, Micali, Rackoff)
- "Content-Defined Chunking" (FastCDC paper)

### Existing Systems
- **Storj**: Decentralized cloud storage with reputation
- **Filecoin**: Blockchain-based storage with proof-of-replication
- **IPFS**: Content-addressed distributed storage
- **Sia**: Decentralized storage marketplace

### Differences from Quloud
- We focus on trustless federation for individuals, not marketplaces
- Owner-initiated auditing vs. miner-based proofs
- Physical key exchange for sharing (privacy-first)
- No blockchain or cryptocurrency required

---

**Last Updated**: 2026-01-17  
**Status**: Research phase - all options under active investigation
