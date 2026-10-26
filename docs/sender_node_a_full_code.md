# Full Code: Sender Node A Workflow

This document contains the complete source code for all modules involved in Sender Node (A)'s workflow: loading the image, encrypting, fragmenting, creating packets, and flooding the network.

## 1. Main Sender Node Implementation (`nodes/sender_a.py`)
This script orchestrates the entire workflow.

```python
"""
sender_a.py: This module implements Node A, the sender in the network simulation.
It loads an image, encrypts it, fragments it into chunks, and broadcasts the chunks
to its neighboring intermediate nodes (B, C, D) using UDP sockets.
"""
import os
import sys
import time
import socket
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import NODE_PORTS, TTL_DEFAULT, FRAGMENT_SIZE
from common.packet import Packet
from common.crypto import encrypt_bytes
from common.fragment import fragment

# Ensure the logs directory exists before creating log handlers
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - NodeA - %(message)s',
    handlers=[
        logging.FileHandler("logs/sender_a.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def run_sender():
    """Main execution function for the sender node."""
    # Define the path to the input image file
    image_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'input_image.png')
    if not os.path.exists(image_path):
        logging.error(f"Image not found at {image_path}")
        return
        
    # Read the original image data from disk
    with open(image_path, 'rb') as f:
        original_data = f.read()
        
    logging.info(f"Loaded image, {len(original_data)} bytes")
    
    # Encrypt the raw image data to ensure privacy over the network
    encrypted_data = encrypt_bytes(original_data)
    
    # Fragment the encrypted data into manageable packet chunks
    fragments = fragment(encrypted_data, size=FRAGMENT_SIZE)
    total_chunks = len(fragments)
    
    logging.info(f"Encrypted and split into {total_chunks} chunks")
    # Removed global UDP socket initialization
    # Define the neighboring nodes (B, C, and D) that will act as intermediate routers
    neighbors = [1, 2, 3] # B=1, C=2, D=3
    dest_ips_ports = [(dest, '127.0.0.1', NODE_PORTS[dest]) for dest in neighbors]
    
    # Generate a unique base ID for this run to avoid packets being flagged as duplicates across runs
    packet_id_base = int(time.time() * 1000) % 100000000
    
    # Iterate through all fragments and send them
    for chunk_sequence, payload in enumerate(fragments):
        # Create a unique packet ID for each chunk
        packet_id = packet_id_base + chunk_sequence
        
        # Construct the packet object
        pkt = Packet(
            src_id=0, # Source: Node A
            dest_id=4, # Destination: Node E
            packet_id=packet_id,
            chunk_sequence=chunk_sequence,
            total_chunks=total_chunks,
            ttl=TTL_DEFAULT,
            payload=payload
        )
        
        # Serialize the packet into a raw byte stream
        packed_data = pkt.pack()
        
        # Broadcast the packet to all neighboring nodes using a new TCP connection per packet
        for dest, ip, port in dest_ips_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((ip, port))
                sock.sendall(packed_data)
                sock.close()
                logging.info(f"Sent {pkt.header_info} dest={dest}")
            except ConnectionRefusedError:
                logging.warning(f"Connection refused by Node {dest} ({ip}:{port})")
            
        # Add a slight delay to prevent overwhelming the local UDP buffers
        time.sleep(0.01)
        
    logging.info("Sender finished transmitting all chunks.")

if __name__ == "__main__":
    run_sender()
```

## 2. Encryption Algorithm (`common/crypto.py`)
Provides the custom bit-shuffle algorithm used to encrypt the image bytes.

```python
"""
crypto.py: Custom cryptographic utility for the network simulation.

This implements a very simple encryption algorithm exactly as requested:
1. Flip the bits
2. Change the order of bits based on a fixed random permutation key
3. Subtract a number
4. XOR with the shared key ("something else")
"""
from common.config import AES_KEY

# The "random key" for changing the order of bits (0 to 7)
# This dictates how to assemble (encrypt) and disassemble (decrypt) the bits of each byte.
BIT_SHUFFLE_KEY = [5, 2, 7, 0, 4, 1, 6, 3]

# The number to subtract
MAGIC_NUMBER = 42

def encrypt_bytes(data: bytes) -> bytes:
    """Encrypts data using our simple bit-manipulation algorithm."""
    encrypted = bytearray()
    
    for i, byte in enumerate(data):
        # Step 1: Flip the bits (e.g. 0b10101010 becomes 0b01010101)
        b = ~byte & 0xFF
        
        # Step 2: Change the order of bits (Assemble using the random key)
        shuffled_b = 0
        for bit_idx in range(8):
            # If the original bit is a 1, place a 1 in the new shuffled position
            if (b & (1 << bit_idx)) != 0:
                new_pos = BIT_SHUFFLE_KEY[bit_idx]
                shuffled_b |= (1 << new_pos)
        b = shuffled_b
        
        # Step 3: Subtract a number (wrapping around if it goes below 0)
        b = (b - MAGIC_NUMBER) % 256
        
        # Step 4: "Then something" -> We XOR with our shared AES_KEY
        key_byte = AES_KEY[i % len(AES_KEY)]
        b = b ^ key_byte
        
        encrypted.append(b)
        
    return bytes(encrypted)

def decrypt_bytes(data: bytes) -> bytes:
    """Decrypts data encrypted with our simple bit-manipulation algorithm."""
    decrypted = bytearray()
    
    for i, byte in enumerate(data):
        # Reverse Step 4: XOR with the shared key again
        key_byte = AES_KEY[i % len(AES_KEY)]
        b = byte ^ key_byte
        
        # Reverse Step 3: Add the number back (wrapping around at 256)
        b = (b + MAGIC_NUMBER) % 256
        
        # Reverse Step 2: Change the order of bits back (Disassemble using the random key)
        unshuffled_b = 0
        for bit_idx in range(8):
            # Check the bit at the shuffled position, and put it back to its original position
            new_pos = BIT_SHUFFLE_KEY[bit_idx]
            if (b & (1 << new_pos)) != 0:
                unshuffled_b |= (1 << bit_idx)
        b = unshuffled_b
        
        # Reverse Step 1: Flip the bits back to normal
        b = ~b & 0xFF
        
        decrypted.append(b)
        
    return bytes(decrypted)
```

## 3. Fragmentation Logic (`common/fragment.py`)
Provides the `fragment` utility used to break the encrypted data into 1024-byte chunks.

```python
"""
fragment.py: This module handles the fragmentation and reassembly of byte data.
In a network, large data needs to be broken into smaller pieces (fragments) to be transmitted
within packet size limits, and reassembled in correct order at the destination.
"""
import math

def fragment(data: bytes, size: int = 1024) -> list[bytes]:
    """Split bytes into chunks of given size."""
    # Slices the input byte data into smaller byte arrays of 'size' length
    return [data[i:i + size] for i in range(0, len(data), size)]

def reassemble(fragments: dict[int, bytes], total: int) -> bytes:
    """Reassemble fragments in order, given a dictionary mapping chunk_sequence -> payload."""
    # Ensure that all expected fragments have been received before reassembling
    if len(fragments) != total:
        raise ValueError(f"Expected {total} fragments, got {len(fragments)}")
        
    result = bytearray()
    # Iterate through chunks in their correct sequence (from 0 to total - 1)
    for i in range(total):
        if i not in fragments:
            raise ValueError(f"Missing fragment {i}")
        # Append each fragment's payload in sequential order
        result.extend(fragments[i])
        
    return bytes(result)
```

## 4. Packet Header & Serialization (`common/packet.py`)
Provides the `Packet` class to attach custom headers to each chunk.

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
