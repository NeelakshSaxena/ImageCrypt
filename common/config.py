"""
config.py: This module contains the configuration settings for the Encrypted Image Flooding Network Simulation.
It defines node ports, default Time-To-Live (TTL), packet fragment sizes, and the AES encryption key.
"""
# Configuration for Encrypted Image Flooding-Network Simulation

# Ports for each node in the network simulation
NODE_PORTS = {
    0: 5000, # A (Sender Node)
    1: 5001, # B (Intermediate Node)
    2: 5002, # C (Intermediate Node)
    3: 5003, # D (Intermediate Node)
    4: 5004  # E (Receiver Node)
}

# Default Time-To-Live (TTL) to prevent packets from circulating endlessly in the network
TTL_DEFAULT = 8

# Maximum payload size in bytes for each packet fragment
FRAGMENT_SIZE = 1024

# Simulation key, not production-secure, used for AES encryption/decryption of the payload
AES_KEY = b"simulation_key_for_lab_123456789"
