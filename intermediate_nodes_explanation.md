# Intermediate Nodes (B, C, D) Operation Guide

This document explains the behavior of intermediate nodes (B, C, and D) in the simulation network. These nodes act as routers that process custom packet headers, enforce loop-prevention mechanisms, and forward encrypted data chunks to the destination node without needing to decrypt them.

## Overview of Operations

When an intermediate node receives a packet, it executes the following pipeline:

1. **Read Custom Header**: Unpacks the binary header to extract metadata.
2. **Enforce Flooding/TTL loop tracking**: Drops duplicates and decrements TTL to prevent infinite loops.
3. **Forward Fragments**: Re-packs and forwards the packet directly to the destination without decrypting the payload.

---

## 1. Reading the Custom Header

Packets sent through the network use a custom binary header format defined in [`common/packet.py`](file:///g:/Projects/Assesment/ComputerNetworks/common/packet.py).

The 17-byte header is structured as follows, with each field serving a specific purpose:
- `magic` (4 bytes): Identifier `b"IMGF"`. **Need:** Acts as a sanity check to quickly validate that the packet belongs to our simulation network, dropping invalid or corrupted packets immediately.
- `src_id` (1 byte): Originating node ID. **Need:** Identifies which node generated the packet (e.g., Node A), useful for logging and tracing the origin.
- `dest_id` (1 byte): Final destination ID. **Need:** Tells intermediate routing nodes the ultimate target (Node E) so they know it is meant to be forwarded.
- `packet_id` (4 bytes): Unique identifier for the fragment. **Need:** Used by intermediate nodes to track `seen_packets`. This is critical for preventing infinite routing loops (flooding redundancy) by allowing nodes to drop duplicate packets.
- `chunk_sequence` (2 bytes): Order index of the fragment. **Need:** Allows the final destination node to correctly place the fragments in the exact order before decryption.
- `total_chunks` (2 bytes): Total fragments for the image. **Need:** Tells the final destination node exactly when it has successfully received all parts of the fragmented message so it can begin reassembly.
- `ttl` (1 byte): Time-To-Live counter. **Need:** A critical loop-prevention mechanism. Decremented at each hop; if it reaches zero, the packet is dropped to prevent it from indefinitely circling the network.
- `payload_length` (2 bytes): Length of the encrypted payload. **Need:** Ensures the unpacking function reads the exact number of bytes for the payload, separating it from subsequent packets in a continuous TCP stream.

**Code Reference:**
- **Packet Unpacking**: [`common/packet.py`](file:///g:/Projects/Assesment/ComputerNetworks/common/packet.py#L53-L85)
- **Node Processing**: [`nodes/intermediate_bcd.py`](file:///g:/Projects/Assesment/ComputerNetworks/nodes/intermediate_bcd.py#L27-L32) where the raw bytes are unpacked into a `Packet` object via `pkt = Packet.unpack(data)`.

## 2. Enforcing Flooding and TTL Loop Tracking

To prevent network congestion and infinite routing loops during flooding, intermediate nodes implement two key safety mechanisms:

### Duplicate Packet Dropping
Each node maintains a `seen_packets` set. When a packet arrives, its `packet_id` is checked against this set. If it has been seen before, the node drops the packet. Otherwise, the ID is added to the set.

**Code Reference:**
[`nodes/intermediate_bcd.py`](file:///g:/Projects/Assesment/ComputerNetworks/nodes/intermediate_bcd.py#L34-L40)
```python
if pkt.packet_id in self.seen_packets:
    self.logger.info(f"Dropped duplicate packet_id={pkt.packet_id}")
    return None
self.seen_packets.add(pkt.packet_id)
```

### TTL (Time-To-Live) Enforcement
The packet's `ttl` field is decremented by 1 at each hop. If the TTL reaches zero, the packet is considered to have traveled too far without reaching its destination and is immediately dropped.

**Code Reference:**
[`nodes/intermediate_bcd.py`](file:///g:/Projects/Assesment/ComputerNetworks/nodes/intermediate_bcd.py#L42-L46)
```python
pkt.ttl -= 1
if pkt.ttl == 0:
    self.logger.info(f"Dropped packet_id={pkt.packet_id} due to TTL=0")
    return None
```

## 3. Forwarding Fragments Without Decrypting

Because intermediate nodes do not possess the private key required to decrypt the payload, they treat the `payload` portion of the packet as an opaque byte sequence. The node simply repackages the updated header (with the decremented TTL) alongside the original encrypted payload, and forwards it to the destination (Node E).

> [!NOTE]
> Even though the original prompt mentions UDP packets, the simulation currently implements forwarding over **TCP sockets** as seen in the networking logic.

**Code References:**
- **Re-packing**: [`nodes/intermediate_bcd.py`](file:///g:/Projects/Assesment/ComputerNetworks/nodes/intermediate_bcd.py#L50-L51) (`return pkt.pack()`)
- **Forwarding to Destination**: [`nodes/intermediate_bcd.py`](file:///g:/Projects/Assesment/ComputerNetworks/nodes/intermediate_bcd.py#L116-L124)
```python
# Forwarding logic
out_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
out_sock.connect((dest_ip, dest_port))
out_sock.sendall(forward_data)
out_sock.close()
```
