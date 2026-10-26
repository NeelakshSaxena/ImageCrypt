import os
import pytest
from common.packet import Packet
from common.crypto import encrypt_bytes
from common.fragment import fragment
from nodes.receiver_e import ReceiverNode

def test_receiver_node_reassembly():
    # Remove existing output file if present
    out_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'received_image.png')
    if os.path.exists(out_path):
        os.remove(out_path)
        
    # Read actual image data
    image_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'input_image.png')
    with open(image_path, 'rb') as f:
        original_data = f.read()
        
    encrypted_data = encrypt_bytes(original_data)
    fragments = fragment(encrypted_data, size=1024)
    total_chunks = len(fragments)
    
    node = ReceiverNode()
    
    import random
    indices = list(range(total_chunks))
    random.shuffle(indices)
    
    # Feed all but the last one
    for i in indices[:-1]:
        pkt = Packet(src_id=0, dest_id=4, packet_id=1000+i, chunk_sequence=i, total_chunks=total_chunks, ttl=7, payload=fragments[i])
        res = node.process_packet(pkt.pack())
        assert res is False
        
        # Send duplicate
        res_dup = node.process_packet(pkt.pack())
        assert res_dup is False
        
    # Feed the last one
    last_i = indices[-1]
    pkt = Packet(src_id=0, dest_id=4, packet_id=1000+last_i, chunk_sequence=last_i, total_chunks=total_chunks, ttl=7, payload=fragments[last_i])
    res = node.process_packet(pkt.pack())
    assert res is True
    
    # Verify file content
    assert os.path.exists(out_path)
    with open(out_path, 'rb') as f:
        received_data = f.read()
        
    assert received_data == original_data
