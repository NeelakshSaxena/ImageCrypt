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
