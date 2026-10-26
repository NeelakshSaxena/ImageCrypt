import pytest
from common.packet import Packet, MAGIC

def test_packet_pack_unpack():
    original = Packet(
        src_id=0,
        dest_id=4,
        packet_id=123456,
        chunk_sequence=0,
        total_chunks=10,
        ttl=8,
        payload=b"test payload 123"
    )
    
    packed = original.pack()
    assert len(packed) == 17 + len(b"test payload 123")
    
    unpacked = Packet.unpack(packed)
    
    assert unpacked.magic == MAGIC
    assert unpacked.src_id == 0
    assert unpacked.dest_id == 4
    assert unpacked.packet_id == 123456
    assert unpacked.chunk_sequence == 0
    assert unpacked.total_chunks == 10
    assert unpacked.ttl == 8
    assert unpacked.payload == b"test payload 123"

def test_packet_edge_values():
    original = Packet(
        src_id=255,
        dest_id=255,
        packet_id=4294967295,
        chunk_sequence=65535,
        total_chunks=65535,
        ttl=0,
        payload=b"A" * 1024
    )
    
    packed = original.pack()
    unpacked = Packet.unpack(packed)
    
    assert unpacked.src_id == 255
    assert unpacked.dest_id == 255
    assert unpacked.packet_id == 4294967295
    assert unpacked.chunk_sequence == 65535
    assert unpacked.total_chunks == 65535
    assert unpacked.ttl == 0
    assert unpacked.payload == b"A" * 1024

def test_invalid_magic():
    original = Packet(
        src_id=0, dest_id=4, packet_id=1, chunk_sequence=0, total_chunks=1, ttl=8, payload=b""
    )
    packed = original.pack()
    # Corrupt magic
    bad_packed = b"BADF" + packed[4:]
    with pytest.raises(ValueError, match="Invalid magic"):
        Packet.unpack(bad_packed)
