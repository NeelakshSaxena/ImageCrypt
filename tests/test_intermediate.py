import pytest
from common.packet import Packet
from nodes.intermediate_bcd import IntermediateNode

def test_intermediate_node_logic():
    node = IntermediateNode(1)
    
    # Normal packet
    pkt = Packet(src_id=0, dest_id=4, packet_id=1, chunk_sequence=0, total_chunks=1, ttl=8, payload=b"test")
    forwarded = node.process_packet(pkt.pack())
    assert forwarded is not None
    
    forwarded_pkt = Packet.unpack(forwarded)
    assert forwarded_pkt.ttl == 7
    
    # Duplicate packet
    forwarded_dup = node.process_packet(pkt.pack())
    assert forwarded_dup is None # Should be dropped
    
    # TTL = 1 packet (will become 0 and drop)
    pkt2 = Packet(src_id=0, dest_id=4, packet_id=2, chunk_sequence=1, total_chunks=2, ttl=1, payload=b"test")
    forwarded_ttl0 = node.process_packet(pkt2.pack())
    assert forwarded_ttl0 is None # Should be dropped
