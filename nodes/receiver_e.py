"""
receiver_e.py: This module implements Node E, the final receiver in the simulation.
It listens for incoming UDP packets, reassembles fragments based on sequence IDs,
decrypts the complete payload, and saves the resulting image to disk.
"""
import os
import sys
import socket
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import NODE_PORTS
from common.packet import Packet, HEADER_SIZE
from common.fragment import reassemble
from common.crypto import decrypt_bytes

# Ensure necessary directories exist
os.makedirs('logs', exist_ok=True)
os.makedirs('output', exist_ok=True)

# Configure logging for Node E
logger = logging.getLogger("NodeE")
logger.setLevel(logging.INFO)
fh = logging.FileHandler("logs/receiver_e.log")
sh = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - NodeE - %(message)s')
fh.setFormatter(formatter)
sh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(sh)

class ReceiverNode:
    """Class representing the final destination node that reassembles the image."""
    def __init__(self):
        # Track processed packet IDs to drop duplicates
        self.seen_packets = set()
        # Dictionary to store received chunks by their sequence number
        self.received_chunks = {}
        # Expected total number of chunks (discovered from the first received packet)
        self.total_chunks = None
        
    def process_packet(self, data: bytes) -> bool:
        """Processes a packet. Returns True if the image is successfully reassembled, False otherwise."""
        try:
            # Unpack the received raw bytes into a Packet object
            pkt = Packet.unpack(data)
        except Exception as e:
            logger.warning(f"Failed to unpack packet: {e}")
            return False
            
        # Check for and drop duplicate packets to handle network flooding redundancy
        if pkt.packet_id in self.seen_packets:
            logger.info(f"Dropped duplicate {pkt.header_info}")
            return False
            
        # Mark packet as seen
        self.seen_packets.add(pkt.packet_id)
        
        # Initialize total_chunks on the first valid packet received
        if self.total_chunks is None:
            self.total_chunks = pkt.total_chunks
            
        # Store the chunk payload at its correct sequence index
        self.received_chunks[pkt.chunk_sequence] = pkt.payload
        logger.info(f"Received {pkt.header_info} progress=({len(self.received_chunks)}/{self.total_chunks})")
        
        # Check if we have received all parts of the image
        if len(self.received_chunks) == self.total_chunks:
            logger.info("All chunks received! Reassembling...")
            try:
                # Reassemble the encrypted data from the ordered chunks
                encrypted_data = reassemble(self.received_chunks, self.total_chunks)
                # Decrypt the complete data to recover the original image
                decrypted_data = decrypt_bytes(encrypted_data)
                
                # Write the decrypted image to the output directory
                out_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'received_image.png')
                with open(out_path, 'wb') as f:
                    f.write(decrypted_data)
                logger.info(f"Successfully saved image to {out_path}")
                
                # Reset chunk tracking for the next potential image transmission
                # (keep seen_packets to avoid old duplicates from delayed packets)
                self.received_chunks = {}
                self.total_chunks = None
                return True
            except Exception as e:
                logger.error(f"Error during reassembly/decryption: {e}")
                # Reset state on failure so it can try again
                self.received_chunks = {}
                self.total_chunks = None
                
        return False

def run_receiver():
    """Main execution loop for the receiver node."""
    port = NODE_PORTS[4] # Port for Node E
    
    # Initialize TCP socket for listening
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', port))
    sock.listen(5)
    
    node = ReceiverNode()
    logger.info(f"Started listening on port {port}...")
    
    # Set a timeout so the while loop can periodically check for KeyboardInterrupt
    sock.settimeout(1.0)
    
    try:
        while True: # Run continuously to process incoming connections
            try:
                conn, addr = sock.accept()
                
                data = b''
                while True:
                    chunk = conn.recv(2048)
                    if not chunk:
                        break
                    data += chunk
                conn.close()
                
                # Ensure the packet is at least the size of the header before processing
                if len(data) >= HEADER_SIZE:
                    node.process_packet(data)
            except socket.timeout:
                # Timeout is expected, just continue the loop
                continue
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == "__main__":
    run_receiver()
