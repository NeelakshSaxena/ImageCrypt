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
