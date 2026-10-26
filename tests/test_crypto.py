import pytest
import os
from common.crypto import encrypt_bytes, decrypt_bytes

def test_crypto_round_trip():
    lengths = [0, 1, 15, 16, 17, 1023, 1024, 100000]
    for length in lengths:
        original = os.urandom(length)
        encrypted = encrypt_bytes(original)
        assert len(encrypted) >= 16 + length # padding + iv
        
        decrypted = decrypt_bytes(encrypted)
        assert decrypted == original

def test_crypto_different_ivs():
    data = b"hello world"
    enc1 = encrypt_bytes(data)
    enc2 = encrypt_bytes(data)
    
    # Should use different IVs each time
    assert enc1 != enc2
    
    assert decrypt_bytes(enc1) == data
    assert decrypt_bytes(enc2) == data
