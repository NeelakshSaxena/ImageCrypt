"""
intermediate_bcd.py: This module implements Intermediate Nodes (B, C, or D).
These nodes receive UDP packets, drop duplicates or packets with TTL=0,
decrement the Time-To-Live (TTL), and forward valid packets to the destination Node E.
"""
import os
import sys
import argparse
import socket
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import NODE_PORTS
from common.packet import Packet, HEADER_SIZE

class IntermediateNode:
    """Class representing an intermediate router node that forwards packets."""
    def __init__(self, node_id: int):
        self.node_id = node_id
        # Set to track IDs of packets already seen to prevent routing loops (duplicate dropping)
        self.seen_packets = set()
        self.logger = logging.getLogger(f"Node{node_id}")
        
    def process_packet(self, data: bytes) -> bytes | None:
        """Processes a received packet. Returns packed bytes to forward, or None if dropped."""
        try:
            # Unpack the received raw bytes into a Packet object
            pkt = Packet.unpack(data)
        except Exception as e:
            self.logger.warning(f"Failed to unpack packet: {e}")
            return None
            
        # Check if the packet has already been processed by this node
        if pkt.packet_id in self.seen_packets:
            self.logger.info(f"Dropped duplicate {pkt.header_info}")
            return None
            
        # Record the packet ID so it's not processed again
        self.seen_packets.add(pkt.packet_id)
        
        # Decrement the Time-To-Live (TTL) to prevent infinite loops
        pkt.ttl -= 1
        if pkt.ttl == 0:
            self.logger.info(f"Dropped due to TTL=0 {pkt.header_info}")
            return None
            
        self.logger.info(f"Forwarded {pkt.header_info} to E")
        
        # Re-pack the modified packet (with new TTL) for forwarding
        return pkt.pack()

def run_intermediate(node_id: int):
    """Main execution function for an intermediate node."""
    os.makedirs('logs', exist_ok=True)
    # Map node IDs to their letter names for logging
    node_name = {1: 'B', 2: 'C', 3: 'D'}.get(node_id, f"Node{node_id}")
    
    # Configure logging to write to both a file and standard output
    logger = logging.getLogger(f"Node{node_id}")
    logger.setLevel(logging.INFO)
    
    fh = logging.FileHandler(f"logs/intermediate_{node_name.lower()}.log")
    sh = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(f'%(asctime)s - {node_name} - %(message)s')
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    
    # Lookup the port assigned to this specific node
    port = NODE_PORTS.get(node_id)
    if not port:
        logger.error(f"Unknown node ID: {node_id}")
        return
        
    # Setup the TCP socket to listen for incoming connections
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', port))
    sock.listen(5)
    
    # Set a timeout so the loop can periodically check for KeyboardInterrupt
    sock.settimeout(1.0)
    
    # Define destination Node E parameters
    dest_ip = '127.0.0.1'
    dest_port = NODE_PORTS[4] # Node E
    
    node = IntermediateNode(node_id)
    logger.info(f"Started listening on port {port}...")
    
    try:
        # Infinite loop to continuously listen for connections
        while True:
            try:
                # Accept an incoming TCP connection
                conn, addr = sock.accept()
                
                data = b''
                # Read all data from the stream until connection closes
                while True:
                    chunk = conn.recv(2048)
                    if not chunk:
                        break
                    data += chunk
                conn.close()
                
                # Ensure the data contains at least a packet header
                if len(data) < HEADER_SIZE:
                    logger.warning("Received data too small for header, dropping.")
                    continue
                    
                # Process the packet to determine if it should be forwarded
                forward_data = node.process_packet(data)
                # If the packet is valid and TTL > 0, forward it to Node E
                if forward_data:
                    try:
                        out_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        out_sock.connect((dest_ip, dest_port))
                        out_sock.sendall(forward_data)
                        out_sock.close()
                    except ConnectionRefusedError:
                        logger.warning(f"Connection refused by destination ({dest_ip}:{dest_port})")
            except socket.timeout:
                continue

                
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == "__main__":
    # Command-line argument parsing to dynamically set the node ID
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=int, required=True, help='Node ID (1=B, 2=C, 3=D)')
    args = parser.parse_args()
    run_intermediate(args.id)
