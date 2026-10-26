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
