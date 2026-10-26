# Full Code: Intermediate Nodes (B, C, D) Workflow

This document contains the complete source code for the Intermediate Nodes (B, C, D). Their workflow involves reading custom headers, enforcing flooding rules and TTL loop tracking, and immediately forwarding fragments to the destination without decrypting them.

## 1. Intermediate Node Implementation (`nodes/intermediate_bcd.py`)
This script contains the logic for reading packets, dropping duplicates to prevent infinite routing loops, decrementing TTL, and forwarding valid packets to Node E.

```python
"""
intermediate_bcd.py: This module implements Intermediate Nodes (B, C, or D).
These nodes receive UDP packets, drop duplicates or packets with TTL=0,
decrement the Time-To-Live (TTL), and forward valid packets to the destination Node E.
"""
import os
import sys
import argparse
import socket
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import NODE_PORTS
from common.packet import Packet, HEADER_SIZE

class IntermediateNode:
    """Class representing an intermediate router node that forwards packets."""
    def __init__(self, node_id: int):
        self.node_id = node_id
        # Set to track IDs of packets already seen to prevent routing loops (duplicate dropping)
        self.seen_packets = set()
        self.logger = logging.getLogger(f"Node{node_id}")
        
    def process_packet(self, data: bytes) -> bytes | None:
        """Processes a received packet. Returns packed bytes to forward, or None if dropped."""
        try:
            # Unpack the received raw bytes into a Packet object
            pkt = Packet.unpack(data)
        except Exception as e:
            self.logger.warning(f"Failed to unpack packet: {e}")
            return None
            
        # Check if the packet has already been processed by this node
        if pkt.packet_id in self.seen_packets:
            self.logger.info(f"Dropped duplicate {pkt.header_info}")
            return None
            
        # Record the packet ID so it's not processed again
        self.seen_packets.add(pkt.packet_id)
        
        # Decrement the Time-To-Live (TTL) to prevent infinite loops
        pkt.ttl -= 1
        if pkt.ttl == 0:
            self.logger.info(f"Dropped due to TTL=0 {pkt.header_info}")
            return None
            
        self.logger.info(f"Forwarded {pkt.header_info} to E")
        
        # Re-pack the modified packet (with new TTL) for forwarding
        return pkt.pack()

def run_intermediate(node_id: int):
    """Main execution function for an intermediate node."""
    os.makedirs('logs', exist_ok=True)
    # Map node IDs to their letter names for logging
    node_name = {1: 'B', 2: 'C', 3: 'D'}.get(node_id, f"Node{node_id}")
    
    # Configure logging to write to both a file and standard output
    logger = logging.getLogger(f"Node{node_id}")
    logger.setLevel(logging.INFO)
    
    fh = logging.FileHandler(f"logs/intermediate_{node_name.lower()}.log")
    sh = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(f'%(asctime)s - {node_name} - %(message)s')
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    
    # Lookup the port assigned to this specific node
    port = NODE_PORTS.get(node_id)
    if not port:
        logger.error(f"Unknown node ID: {node_id}")
        return
        
    # Setup the TCP socket to listen for incoming connections
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', port))
    sock.listen(5)
    
    # Set a timeout so the loop can periodically check for KeyboardInterrupt
    sock.settimeout(1.0)
    
    # Define destination Node E parameters
    dest_ip = '127.0.0.1'
    dest_port = NODE_PORTS[4] # Node E
    
    node = IntermediateNode(node_id)
    logger.info(f"Started listening on port {port}...")
    
    try:
        # Infinite loop to continuously listen for connections
        while True:
            try:
                # Accept an incoming TCP connection
                conn, addr = sock.accept()
                
                data = b''
                # Read all data from the stream until connection closes
                while True:
                    chunk = conn.recv(2048)
                    if not chunk:
                        break
                    data += chunk
                conn.close()
                
                # Ensure the data contains at least a packet header
                if len(data) < HEADER_SIZE:
                    logger.warning("Received data too small for header, dropping.")
                    continue
                    
                # Process the packet to determine if it should be forwarded
                forward_data = node.process_packet(data)
                # If the packet is valid and TTL > 0, forward it to Node E
                if forward_data:
                    try:
                        out_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        out_sock.connect((dest_ip, dest_port))
                        out_sock.sendall(forward_data)
                        out_sock.close()
                    except ConnectionRefusedError:
                        logger.warning(f"Connection refused by destination ({dest_ip}:{dest_port})")
            except socket.timeout:
                continue

                
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == "__main__":
    # Command-line argument parsing to dynamically set the node ID
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=int, required=True, help='Node ID (1=B, 2=C, 3=D)')
    args = parser.parse_args()
    run_intermediate(args.id)
```

## 2. Packet Header Structure (`common/packet.py`)
Intermediate nodes rely on this custom packet structure to read headers (specifically the `packet_id` and `ttl` fields) to make routing decisions without ever attempting to decrypt the payload.

```python
"""
packet.py: This module defines the custom Packet structure used in the simulation.
It provides a class for creating network packets and packing/unpacking them 
to and from raw bytes for UDP transmission.
"""
import struct
from dataclasses import dataclass

# | magic            | bytes  | 4             | b"IMGF" — sanity check                |
# | src_id           | uint8  | 1             | originating node id (A=0)             |
# | dest_id          | uint8  | 1             | final receiver id (E=4)               |
# | packet_id        | uint32 | 4             | unique id for this fragment (dedup)   |
# | chunk_sequence   | uint16 | 2             | order index of this fragment          |
# | total_chunks     | uint16 | 2             | total fragment count for this image   |
# | ttl              | uint8  | 1             | decremented at each hop               |
# | payload_length   | uint16 | 2             | length of the encrypted payload       |

# Network byte order (!) format string for struct pack/unpack
# 4s (4 chars), B (uint8), B (uint8), I (uint32), H (uint16), H (uint16), B (uint8), H (uint16)

HEADER_FORMAT = "!4sBBIHHBH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAGIC = b"IMGF" # Magic number to identify valid simulation packets

@dataclass
class Packet:
    """Represents a network packet with header fields and payload."""
    src_id: int
    dest_id: int
    packet_id: int
    chunk_sequence: int
    total_chunks: int
    ttl: int
    payload: bytes
    magic: bytes = MAGIC

    @property
    def header_info(self) -> str:
        return f"[magic={self.magic}, src_id={self.src_id}, dest_id={self.dest_id}, packet_id={self.packet_id}, chunk_sequence={self.chunk_sequence}, total_chunks={self.total_chunks}, ttl={self.ttl}, payload_length={len(self.payload)}]"

    def pack(self) -> bytes:
        """Serializes the Packet object into a byte stream for transmission."""
        # Pack header fields into bytes using the defined struct format
        header = struct.pack(
            HEADER_FORMAT,
            self.magic,
            self.src_id,
            self.dest_id,
            self.packet_id,
            self.chunk_sequence,
            self.total_chunks,
            self.ttl,
            len(self.payload) # Include payload length for proper unpacking
        )
        # Return header bytes followed by the payload data
        return header + self.payload

    @classmethod
    def unpack(cls, data: bytes) -> "Packet":
        """Deserializes raw bytes back into a Packet object."""
        # Ensure data is long enough to contain at least the header
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Data too short, needs at least {HEADER_SIZE} bytes")
        
        # Split received data into header and payload parts
        header_data = data[:HEADER_SIZE]
        payload_data = data[HEADER_SIZE:]
        
        # Unpack the header fields based on the struct format
        magic, src_id, dest_id, packet_id, chunk_sequence, total_chunks, ttl, payload_length = struct.unpack(
            HEADER_FORMAT, header_data
        )
        
        # Verify the magic number to ensure it's our packet protocol
        if magic != MAGIC:
            raise ValueError(f"Invalid magic: {magic}")
            
        # Extract only the specified length for payload, ignoring padding if any
        payload = payload_data[:payload_length]
            
        return cls(
            src_id=src_id,
            dest_id=dest_id,
            packet_id=packet_id,
            chunk_sequence=chunk_sequence,
            total_chunks=total_chunks,
            ttl=ttl,
            payload=payload,
            magic=magic
        )
```
