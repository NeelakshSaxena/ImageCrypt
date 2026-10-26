import pytest
import os
import random
from common.fragment import fragment, reassemble
from common.crypto import encrypt_bytes, decrypt_bytes
from common.config import FRAGMENT_SIZE

def test_fragmentation_round_trip():
    # Read the actual test image
    image_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'input_image.png')
    with open(image_path, 'rb') as f:
        original_data = f.read()
        
    # Encrypt
    encrypted_data = encrypt_bytes(original_data)
    
    # Fragment
    fragments_list = fragment(encrypted_data, size=FRAGMENT_SIZE)
    total_chunks = len(fragments_list)
    
    # Shuffle to simulate out-of-order network arrival
    indices = list(range(total_chunks))
    random.shuffle(indices)
    
    # Reassemble dict
    fragments_dict = {}
    for i in indices:
        fragments_dict[i] = fragments_list[i]
        
    # Reassemble
    reassembled_encrypted = reassemble(fragments_dict, total_chunks)
    
    # Decrypt
    decrypted_data = decrypt_bytes(reassembled_encrypted)
    
    # Assert
    assert decrypted_data == original_data

def test_reassemble_missing_fragment():
    fragments_dict = {0: b"123", 2: b"789"}
    with pytest.raises(ValueError, match="Expected 3 fragments, got 2"):
        reassemble(fragments_dict, 3)
        
    fragments_dict = {0: b"123", 1: b"456", 3: b"abc"}
    with pytest.raises(ValueError, match="Missing fragment 2"):
        reassemble(fragments_dict, 3)
