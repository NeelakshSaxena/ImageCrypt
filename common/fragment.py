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
