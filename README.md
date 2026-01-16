# Quloud

**Trustless federated storage - autonomous NAS node for decentralized data redundancy**

## Overview

Quloud is a single-node implementation for participating in a trustless federated storage network. Each installation runs independently on a NAS device, cooperating with other nodes to provide cross-node redundancy while maintaining complete encryption control.

The federation emerges from multiple autonomous nodes communicating - there is no central coordinator. Each node manages its own encryption keys, validates requests cryptographically, and operates without trusting other nodes in the network.

## Core Concepts

### Trustless Federation Model

- **Individual Node Autonomy**: Each node controls its own encryption and data
- **No Trust Required**: Nodes verify requests cryptographically without trust relationships
- **Decentralized**: No central authority or coordinator
- **Open Protocol**: Anyone can run a node and join the federation

### Multi-Layer Encryption

When Node A stores data across the federation:

1. **Node A** encrypts file with its private key → generates Zero-Knowledge Proof (ZKP)
2. **Node A** sends encrypted chunk + ZKP to storage nodes (B, C, D)
3. **Storage nodes** encrypt received data again with their own private keys
4. **Result**: Multiple encryption layers - compromised storage node can't read data

### Zero-Knowledge Proofs (ZKP)

- Owner node creates ZKP proving data ownership
- ZKP stored as encrypted metadata on storage nodes
- Retrieval requires presenting valid ZKP
- Storage nodes verify proof without knowing the data
- Compromised ZKP alone is useless - data still encrypted with owner's key

### Data Sharing

**Primary method**: Physical key exchange (human-to-human)
- Share the owner's decryption key directly
- Storage nodes don't know data was shared
- Trustless model preserved

**Future feature**: Link relationships
- Owner node re-encrypts data with shared key
- Creates new ZKP for recipient
- Trust relationship remains personal between nodes

## Architecture

### Node Responsibilities

Each node must:

1. **Accept chunks** - Receive encrypted data from other nodes
2. **Return chunks** - Send stored data when valid ZKP presented
3. **Send chunks** - Store data on remote nodes with ZKP metadata
4. **Encrypt chunks** - Apply node's encryption layer to all stored data
5. **Decrypt chunks** - Remove only its own encryption layer (for owned data)
6. **Authenticate retrieval** - Verify ZKP before returning chunks
7. **Validate storage** - Verify storage requests are legitimate

### Node Discovery

Broadcast/pub-sub model:
- Nodes announce themselves to a discovery topic
- Other nodes subscribe to learn about peers
- Supports both LAN (local network) and internet-wide federation

### Protocol Boundary

The federation protocol defines **how nodes communicate**, not how they store data locally. Each node can:
- Use any storage backend (filesystem, database, object storage)
- Implement any chunking strategy
- Choose any indexing approach

As long as the node responds correctly to protocol requests, it's a valid federation participant.

## Technology

- **Language**: Python 3.13+
- **Package Management**: uv
- **Architecture**: Hexagonal (ports & adapters)
- **Cryptography**: TBD (investigating ZKP libraries)
- **Network**: TBD (protocol design in progress)

## Current Status

**Phase**: Initial Planning & Setup

✅ Project structure initialized  
✅ Core architecture defined  
✅ Design conversation documented ([initiating_conversation.md](initiating_conversation.md))  
🔄 Protocol specification (in progress)  
⬜ ZKP implementation  
⬜ Encryption layer  
⬜ Network protocol  
⬜ Node discovery  
⬜ Storage interface  

## Getting Started

**Prerequisites:**
- Python 3.13+
- uv package manager

**Installation:**
```bash
git clone https://github.com/IzzyFuller/Quloud.git
cd Quloud
uv sync
```

## Design Documentation

The initial design conversation is preserved in [initiating_conversation.md](initiating_conversation.md). This documents the exploration of:
- Trustless federation architecture
- Zero-Knowledge Proof verification
- Multi-layer encryption strategy
- Storage and retrieval flows
- Security model and threat analysis

## Contributing

This is an early-stage project. Design feedback and architectural discussion welcome.

## License

TBD

---

**Repository**: [IzzyFuller/Quloud](https://github.com/IzzyFuller/Quloud)
