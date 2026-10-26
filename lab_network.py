"""
lab_network.py: Encrypted Image Flooding Simulation for Computer Networks Lab.

This script runs on any lab system (out of 70+ networked PCs).
Features:
  1. Interactive questionnaire to configure Sender, Receiver, and 3-6 Intermediates.
  2. Automated connection testing across all endpoints.
  3. Embedded HTML/CSS/JS web server with live WebSocket/REST synchronization.
  4. Specialized screens for:
     - Sender Station: Bit-Shuffle encryption, fragmentation, multi-path flooding.
     - Intermediate Stations: Wire-level packet inspection, raw hex dump stream,
       duplicate loop detection, and TTL decrement/forwarding.
     - Receiver Station: Fragment collection buffer matrix, in-order reassembly,
       inverse Bit-Shuffle decryption, and side-by-side verification.
  5. Shows local system IP and assigned ports on every screen.
"""

import os
import sys
import time
import math
import json
import socket
import select
import struct
import hashlib
import logging
import argparse
import threading
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add root directory to sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

# Project imports
from common.config import AES_KEY, TTL_DEFAULT, FRAGMENT_SIZE
from common.packet import Packet, MAGIC, HEADER_SIZE
from common.crypto import encrypt_bytes, decrypt_bytes
from common.fragment import fragment, reassemble

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Ensure output & assets directories exist
os.makedirs(os.path.join(BASE_DIR, 'output'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'assets'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# Global Application State
APP_STATE = {
    "role": "sender",
    "system_ip": "127.0.0.1",
    "transport_port": 5000,
    "web_port": 8080,
    "config": {
        "sender": {"ip": "127.0.0.1", "port": 5000},
        "receiver": {"ip": "127.0.0.1", "port": 5004},
        "intermediates": [
            {"id": 1, "name": "Intermediate 1 (Node B)", "ip": "127.0.0.1", "port": 5001},
            {"id": 2, "name": "Intermediate 2 (Node C)", "ip": "127.0.0.1", "port": 5002},
            {"id": 3, "name": "Intermediate 3 (Node D)", "ip": "127.0.0.1", "port": 5003}
        ]
    },
    "stats": {
        "packets_sent": 0,
        "bytes_sent": 0,
        "packets_received": 0,
        "packets_forwarded": 0,
        "duplicates_dropped": 0,
        "ttl_dropped": 0,
        "total_chunks": 0,
        "chunks_received": 0,
        "received_chunk_indices": [],
        "reassembled": False,
        "sha256": None,
        "image_size_kb": 0,
        "image_dimensions": "-- x --",
        "intermediates": {}
    },
    "events": [],
    "raw_packets": {}  # node_id -> list of packet records
}

STATE_LOCK = threading.Lock()


def get_local_ip() -> str:
    """Discovers the active LAN IP of this system."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return '127.0.0.1'


def add_event(event_type: str, message: str, node: str = "system", details: dict = None):
    """Logs an event and makes it available to the web dashboard."""
    with STATE_LOCK:
        event = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "type": event_type,
            "node": node,
            "message": message,
            "details": details or {}
        }
        APP_STATE["events"].append(event)
        if len(APP_STATE["events"]) > 500:
            APP_STATE["events"].pop(0)


def generate_hexdump(data: bytes, max_bytes: int = 128) -> str:
    """Formats bytes into standard 16-bytes per line hex dump with ASCII representation."""
    lines = []
    chunk = data[:max_bytes]
    for i in range(0, len(chunk), 16):
        line_bytes = chunk[i:i + 16]
        hex_part = ' '.join(f'{b:02x}' for b in line_bytes)
        hex_part = hex_part.ljust(48)
        ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in line_bytes)
        lines.append(f"{i:04x}  {hex_part}  |{ascii_part}|")
    if len(data) > max_bytes:
        lines.append(f"... (+ {len(data) - max_bytes} more bytes)")
    return '\n'.join(lines)


# ==============================================================================
# 1. INTERACTIVE QUESTIONNAIRE & CONFIGURATION WIZARD
# ==============================================================================

def select_port(title: str, options: list[int], default_idx: int = 0) -> int:
    """Presents a numbered menu for selecting ports with custom entry option."""
    print(f"\nSelect port for {title}:")
    for idx, p in enumerate(options, 1):
        def_tag = " (Default)" if idx == default_idx + 1 else ""
        print(f"  [{idx}] Port {p}{def_tag}")
    custom_idx = len(options) + 1
    print(f"  [{custom_idx}] Custom Port Number")

    while True:
        choice = input(f"Enter option [1-{custom_idx}, Default={default_idx + 1}]: ").strip()
        if not choice:
            return options[default_idx]
        try:
            val = int(choice)
            if 1 <= val <= len(options):
                return options[val - 1]
            elif val == custom_idx:
                while True:
                    c_port = input("Enter custom port (1024 - 65535): ").strip()
                    try:
                        p = int(c_port)
                        if 1024 <= p <= 65535:
                            return p
                        print("Port must be between 1024 and 65535.")
                    except ValueError:
                        print("Please enter a valid numeric port.")
            else:
                print(f"Enter a number between 1 and {custom_idx}.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def run_configuration_wizard(local_ip: str) -> dict:
    """Runs the step-by-step interactive questionnaire requested by user."""
    print("\n" + "=" * 76)
    print("       ENCRYPTED IMAGE FLOODING — LAB TOPOLOGY SETUP WIZARD")
    print("=" * 76)
    print(f"Detected System IP: {local_ip}")
    print("Please answer the following configuration steps for your lab setup.\n")

    # Step 1: Sender System
    print("-" * 76)
    print("[1/3] SENDER SYSTEM CONFIGURATION")
    print("-" * 76)
    sender_ip = input(f"Enter IP of Sender System [Default: {local_ip}]: ").strip() or local_ip
    sender_port = select_port("Sender System", [5000, 5050, 8000, 8080], default_idx=0)

    # Step 2: Receiver System
    print("\n" + "-" * 76)
    print("[2/3] RECEIVER SYSTEM CONFIGURATION")
    print("-" * 76)
    receiver_ip = input(f"Enter IP of Receiver System [Default: {local_ip}]: ").strip() or local_ip
    receiver_port = select_port("Receiver System", [5004, 5054, 8004, 9004], default_idx=0)

    # Step 3: Intermediate Systems (Min 3, Max 6)
    print("\n" + "-" * 76)
    print("[3/3] INTERMEDIATE SYSTEMS CONFIGURATION")
    print("-" * 76)
    while True:
        count_str = input("How many intermediate systems do you need? (Min: 3, Max: 6) [Default: 3]: ").strip()
        if not count_str:
            num_intermediates = 3
            break
        try:
            n = int(count_str)
            if 3 <= n <= 6:
                num_intermediates = n
                break
            print("Error: Minimum is 3 intermediate systems, maximum is 6.")
        except ValueError:
            print("Please enter a valid integer between 3 and 6.")

    letter_names = ['B', 'C', 'D', 'F', 'G', 'H']
    intermediates = []

    for i in range(num_intermediates):
        letter = letter_names[i] if i < len(letter_names) else f"Node-{i+1}"
        node_name = f"Intermediate {i+1} (Node {letter})"
        print(f"\n--- {node_name} ---")
        int_ip = input(f"Enter IP for {node_name} [Default: {local_ip}]: ").strip() or local_ip
        std_port = 5001 + i
        alt_port = 6001 + i
        int_port = select_port(f"{node_name}", [std_port, alt_port], default_idx=0)
        intermediates.append({
            "id": i + 1,
            "name": node_name,
            "ip": int_ip,
            "port": int_port
        })

    config = {
        "sender": {"ip": sender_ip, "port": sender_port},
        "receiver": {"ip": receiver_ip, "port": receiver_port},
        "intermediates": intermediates
    }

    # Save to lab_config.json for quick reuse
    try:
        with open(os.path.join(BASE_DIR, 'lab_config.json'), 'w') as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass

    return config


# ==============================================================================
# 2. CONNECTION TESTING ENGINE
# ==============================================================================

def probe_socket(ip: str, port: int, timeout: float = 2.0) -> tuple[bool, str]:
    """Tests if a remote socket endpoint is actively listening."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True, "Connection established"
    except ConnectionRefusedError:
        return False, "Connection refused (node not yet listening)"
    except socket.timeout:
        return False, "Connection timed out"
    except Exception as e:
        return False, str(e)


def run_connection_test(config: dict, is_sender_local: bool = True) -> bool:
    """Executes socket reachability test across all configured nodes."""
    print("\n" + "=" * 76)
    print("                    TESTING NETWORK CONNECTIONS")
    print("=" * 76)
    print("Probing configured systems before continuing...")

    all_passed = True
    failed_nodes = []

    # 1. Sender
    sender = config["sender"]
    print(f"  * Sender ({sender['ip']}:{sender['port']})...", end=" ", flush=True)
    if is_sender_local:
        # Check local bind capability
        try:
            test_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_s.bind(('0.0.0.0', sender['port']))
            test_s.close()
            print("[READY] (Local port bind OK)")
        except Exception as e:
            print(f"[WARNING] Local bind error: {e}")
    else:
        ok, msg = probe_socket(sender['ip'], sender['port'])
        if ok:
            print("[CONNECTED]")
        else:
            print(f"[FAILED] ({msg})")
            all_passed = False
            failed_nodes.append(f"Sender ({sender['ip']}:{sender['port']})")

    # 2. Intermediates
    for node in config["intermediates"]:
        print(f"  * {node['name']} ({node['ip']}:{node['port']})...", end=" ", flush=True)
        ok, msg = probe_socket(node['ip'], node['port'])
        if ok:
            print("[CONNECTED]")
        else:
            print(f"[WAITING] ({msg})")
            all_passed = False
            failed_nodes.append(f"{node['name']} ({node['ip']}:{node['port']})")

    # 3. Receiver
    receiver = config["receiver"]
    print(f"  * Receiver ({receiver['ip']}:{receiver['port']})...", end=" ", flush=True)
    ok, msg = probe_socket(receiver['ip'], receiver['port'])
    if ok:
        print("[CONNECTED]")
    else:
        print(f"[WAITING] ({msg})")
        all_passed = False
        failed_nodes.append(f"Receiver ({receiver['ip']}:{receiver['port']})")

    print("-" * 76)
    if all_passed:
        print("[SUCCESS] All connection tests PASSED! Continuing script...")
        return True
    else:
        print("[NOTICE] Some nodes could not be reached via TCP socket probe:")
        for fn in failed_nodes:
            print(f"  - {fn}")
        print("\nOptions:")
        print("  [R] Retry connection test (recommended after starting other nodes)")
        print("  [F] Force continue to Web Server anyway")
        print("  [E] Edit configurations")

        while True:
            choice = input("Enter choice [R/F/E, Default=F]: ").strip().upper()
            if not choice or choice == 'F':
                print("Continuing to web server...")
                return True
            elif choice == 'R':
                return run_connection_test(config, is_sender_local)
            elif choice == 'E':
                return False


# ==============================================================================
# 3. SENDER TRANSMISSION ENGINE (NODE A)
# ==============================================================================

def execute_flooding_transmission(image_path: str = None) -> dict:
    """
    Encrypts image with Custom Bit-Shuffle, splits into 1024B fragments,
    and floods to all configured intermediate systems over TCP.
    """
    if not image_path or not os.path.exists(image_path):
        image_path = os.path.join(BASE_DIR, 'assets', 'input_image.png')

    if not os.path.exists(image_path):
        return {"success": False, "error": f"Image file not found at {image_path}"}

    with open(image_path, 'rb') as f:
        cleartext_bytes = f.read()

    add_event("send", f"Loaded source image ({len(cleartext_bytes)} bytes)", "sender")

    # Step 1: Encrypt with custom Bit-Shuffle
    encrypted_bytes = encrypt_bytes(cleartext_bytes)
    add_event("send", "Applied Bit-Shuffle encryption (Invert -> Permute -> Sub42 -> XOR)", "sender")

    # Save encrypted noise preview image
    generate_noise_image(encrypted_bytes, os.path.join(BASE_DIR, 'output', 'encrypted_noise.png'))

    # Step 2: Fragment into 1024-byte chunks
    chunks = fragment(encrypted_bytes, size=FRAGMENT_SIZE)
    total_chunks = len(chunks)

    # Target intermediate systems
    targets = APP_STATE["config"]["intermediates"]
    packet_id_base = int(time.time() * 1000) % 100000000

    with STATE_LOCK:
        APP_STATE["stats"]["total_chunks"] = total_chunks
        APP_STATE["stats"]["packets_sent"] = 0
        APP_STATE["stats"]["bytes_sent"] = 0
        APP_STATE["stats"]["image_size_kb"] = round(len(cleartext_bytes) / 1024, 1)

    add_event("send", f"Split payload into {total_chunks} fragments. Flooding to {len(targets)} intermediate nodes...", "sender")

    # Flood all chunks
    sent_count = 0
    bytes_sent = 0

    for chunk_seq, payload in enumerate(chunks):
        packet_id = packet_id_base + chunk_seq

        pkt = Packet(
            src_id=0,
            dest_id=4,
            packet_id=packet_id,
            chunk_sequence=chunk_seq,
            total_chunks=total_chunks,
            ttl=TTL_DEFAULT,
            payload=payload
        )
        packed_data = pkt.pack()

        # Send to all intermediate neighbors
        for node in targets:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect((node['ip'], node['port']))
                s.sendall(packed_data)
                s.close()
                sent_count += 1
                bytes_sent += len(packed_data)
            except Exception as err:
                add_event("error", f"Send error to {node['name']}: {err}", "sender")

        with STATE_LOCK:
            APP_STATE["stats"]["packets_sent"] = sent_count
            APP_STATE["stats"]["bytes_sent"] = bytes_sent

        add_event("send", f"Dispatched fragment {chunk_seq + 1}/{total_chunks} (Packet #{packet_id}) to {len(targets)} nodes", "sender")
        time.sleep(0.01)  # Flow control delay

    add_event("send", f"Flooding transmission complete! Total {sent_count} packets flooded.", "sender")
    return {"success": True, "total_chunks": total_chunks, "packets_sent": sent_count}


def generate_noise_image(data: bytes, output_path: str):
    """Renders raw encrypted bytes as a visual grayscale noise image."""
    if not HAS_PIL:
        return
    try:
        side = int(math.ceil(math.sqrt(len(data))))
        padded = data + os.urandom(side * side - len(data))
        img = Image.frombytes('L', (side, side), padded)
        resample = Image.Resampling.NEAREST if hasattr(Image, 'Resampling') else Image.NEAREST
        img = img.resize((300, 300), resample=resample)
        img.save(output_path)
    except Exception as e:
        print(f"Noise image error: {e}")


# ==============================================================================
# 4. INTERMEDIATE ROUTER & RAW PACKET INSPECTOR
# ==============================================================================

class IntermediateService:
    """Runs the intermediate forwarding router and intercepts raw packet bytes."""
    def __init__(self, node_id: int, listen_port: int, receiver_ip: str, receiver_port: int):
        self.node_id = node_id
        self.listen_port = listen_port
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port
        self.seen_packets = set()
        self.running = True
        self.stats = {
            "received": 0,
            "forwarded": 0,
            "duplicates_dropped": 0,
            "ttl_dropped": 0
        }

    def start(self):
        t = threading.Thread(target=self._run_server, daemon=True)
        t.start()

    def _run_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('0.0.0.0', self.listen_port))
            sock.listen(10)
        except Exception as e:
            print(f"[Intermediate {self.node_id}] Bind error on port {self.listen_port}: {e}")
            return

        sock.settimeout(1.0)
        print(f"[Intermediate {self.node_id}] Listening on port {self.listen_port} (Forwarding to {self.receiver_ip}:{self.receiver_port})...")

        while self.running:
            try:
                conn, addr = sock.accept()
                data = b''
                while True:
                    chunk = conn.recv(2048)
                    if not chunk:
                        break
                    data += chunk
                conn.close()

                if len(data) < HEADER_SIZE:
                    continue

                self._process_packet(data)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Intermediate {self.node_id}] Socket error: {e}")

    def _process_packet(self, data: bytes):
        self.stats["received"] += 1
        pkt = None
        action = "UNKNOWN"

        try:
            pkt = Packet.unpack(data)
        except Exception as e:
            print(f"[Intermediate {self.node_id}] Unpack error: {e}")
            return

        # Check loop / duplicate
        if pkt.packet_id in self.seen_packets:
            self.stats["duplicates_dropped"] += 1
            action = "DROPPED_DUPLICATE"
        else:
            self.seen_packets.add(pkt.packet_id)
            pkt.ttl -= 1
            if pkt.ttl == 0:
                self.stats["ttl_dropped"] += 1
                action = "DROPPED_TTL"
            else:
                action = "FORWARDED"
                # Forward to Receiver
                try:
                    fwd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    fwd_sock.settimeout(2.0)
                    fwd_sock.connect((self.receiver_ip, self.receiver_port))
                    fwd_sock.sendall(pkt.pack())
                    fwd_sock.close()
                    self.stats["forwarded"] += 1
                except Exception as fe:
                    print(f"[Intermediate {self.node_id}] Forwarding error to receiver: {fe}")

        # Record for web raw data stream
        record = {
            "packet_id": pkt.packet_id,
            "chunk_sequence": pkt.chunk_sequence,
            "total_chunks": pkt.total_chunks,
            "ttl": pkt.ttl,
            "src_id": pkt.src_id,
            "dest_id": pkt.dest_id,
            "payload_length": len(pkt.payload),
            "action": action,
            "time": time.strftime("%H:%M:%S"),
            "hexdump": generate_hexdump(data, max_bytes=128)
        }

        with STATE_LOCK:
            if self.node_id not in APP_STATE["raw_packets"]:
                APP_STATE["raw_packets"][self.node_id] = []
            APP_STATE["raw_packets"][self.node_id].append(record)
            if len(APP_STATE["raw_packets"][self.node_id]) > 200:
                APP_STATE["raw_packets"][self.node_id].pop(0)

            if "intermediates" not in APP_STATE["stats"]:
                APP_STATE["stats"]["intermediates"] = {}
            APP_STATE["stats"]["intermediates"][self.node_id] = self.stats


# ==============================================================================
# 5. RECEIVER REASSEMBLER & DECRYPTOR (NODE E)
# ==============================================================================

class ReceiverService:
    """Collects incoming chunks, handles flooding duplicates, and decrypts the final image."""
    def __init__(self, listen_port: int):
        self.listen_port = listen_port
        self.seen_packets = set()
        self.received_chunks = {}
        self.total_chunks = None
        self.running = True

    def start(self):
        t = threading.Thread(target=self._run_server, daemon=True)
        t.start()

    def _run_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('0.0.0.0', self.listen_port))
            sock.listen(10)
        except Exception as e:
            print(f"[Receiver] Bind error on port {self.listen_port}: {e}")
            return

        sock.settimeout(1.0)
        print(f"[Receiver] Listening on port {self.listen_port}...")

        while self.running:
            try:
                conn, addr = sock.accept()
                data = b''
                while True:
                    chunk = conn.recv(2048)
                    if not chunk:
                        break
                    data += chunk
                conn.close()

                if len(data) >= HEADER_SIZE:
                    self._process_packet(data)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Receiver] Socket error: {e}")

    def _process_packet(self, data: bytes):
        try:
            pkt = Packet.unpack(data)
        except Exception:
            return

        # Handle duplicate arrivals (from multi-path flooding)
        if pkt.packet_id in self.seen_packets:
            with STATE_LOCK:
                APP_STATE["stats"]["duplicates_dropped"] += 1
            return

        self.seen_packets.add(pkt.packet_id)

        if self.total_chunks is None:
            self.total_chunks = pkt.total_chunks

        self.received_chunks[pkt.chunk_sequence] = pkt.payload

        with STATE_LOCK:
            APP_STATE["stats"]["chunks_received"] = len(self.received_chunks)
            APP_STATE["stats"]["received_chunk_indices"] = sorted(list(self.received_chunks.keys()))

        add_event("receive", f"Stored fragment #{pkt.chunk_sequence} ({len(self.received_chunks)}/{self.total_chunks})", "receiver")

        # Check if all chunks have arrived
        if len(self.received_chunks) == self.total_chunks:
            self._reassemble_and_decrypt()

    def _reassemble_and_decrypt(self):
        add_event("reassemble", "All fragments collected! Starting in-order reassembly...", "receiver")
        try:
            encrypted_data = reassemble(self.received_chunks, self.total_chunks)
            decrypted_data = decrypt_bytes(encrypted_data)

            out_path = os.path.join(BASE_DIR, 'output', 'lab_received_image.png')
            with open(out_path, 'wb') as f:
                f.write(decrypted_data)

            sha = hashlib.sha256(decrypted_data).hexdigest()

            with STATE_LOCK:
                APP_STATE["stats"]["reassembled"] = True
                APP_STATE["stats"]["sha256"] = sha

            add_event("reassembled", f"Image reconstructed successfully! SHA-256: {sha[:16]}...", "receiver")
            print(f"[Receiver] SUCCESS: Image written to {out_path} (SHA-256: {sha})")

            # Reset chunk buffer for potential next run
            self.received_chunks = {}
            self.total_chunks = None
        except Exception as e:
            add_event("error", f"Reassembly error: {e}", "receiver")
            self.received_chunks = {}
            self.total_chunks = None


# ==============================================================================
# 6. HTTP SERVER & REST API (HTML / CSS / JS)
# ==============================================================================

class LabHttpHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler serving the web UI and REST API."""
    def __init__(self, *args, **kwargs):
        web_dir = os.path.join(BASE_DIR, 'web')
        super().__init__(*args, directory=web_dir, **kwargs)

    def log_message(self, format, *args):
        # Silence routine static file logs
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == '/api/status':
            self._send_json(APP_STATE)
        elif path == '/api/events':
            since = float(query.get('since', [0])[0])
            with STATE_LOCK:
                filtered = [ev for ev in APP_STATE["events"] if ev["timestamp"] > since]
            self._send_json({"events": filtered})
        elif path == '/api/raw_packets':
            node_id = int(query.get('node_id', [1])[0])
            with STATE_LOCK:
                packets = APP_STATE["raw_packets"].get(node_id, [])
            self._send_json({"node_id": node_id, "packets": packets})
        elif path == '/api/image/original':
            self._serve_file(os.path.join(BASE_DIR, 'assets', 'input_image.png'), 'image/png')
        elif path == '/api/image/encrypted':
            noise_path = os.path.join(BASE_DIR, 'output', 'encrypted_noise.png')
            if not os.path.exists(noise_path):
                # Generate if missing
                sample = os.path.join(BASE_DIR, 'assets', 'input_image.png')
                if os.path.exists(sample):
                    with open(sample, 'rb') as f:
                        generate_noise_image(encrypt_bytes(f.read()), noise_path)
            self._serve_file(noise_path, 'image/png')
        elif path == '/api/image/reconstructed':
            self._serve_file(os.path.join(BASE_DIR, 'output', 'lab_received_image.png'), 'image/png')
        else:
            # Fallback to static web files
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/transmit':
            # Run transmission in background thread
            t = threading.Thread(target=execute_flooding_transmission)
            t.start()
            self._send_json({"success": True, "message": "Transmission initiated"})
        elif path == '/api/use_sample':
            sample_path = os.path.join(BASE_DIR, 'assets', 'input_image.png')
            if os.path.exists(sample_path):
                with open(sample_path, 'rb') as f:
                    data = f.read()
                generate_noise_image(encrypt_bytes(data), os.path.join(BASE_DIR, 'output', 'encrypted_noise.png'))
            self._send_json({"success": True})
        elif path == '/api/test_connections':
            results = []
            cfg = APP_STATE["config"]
            # Sender
            results.append({"node": "Sender (A)", "target": f"{cfg['sender']['ip']}:{cfg['sender']['port']}", "status": "OK"})
            # Intermediates
            for n in cfg["intermediates"]:
                ok, msg = probe_socket(n['ip'], n['port'], timeout=1.0)
                results.append({"node": n['name'], "target": f"{n['ip']}:{n['port']}", "status": "OK" if ok else "FAIL", "error": msg})
            # Receiver
            ok, msg = probe_socket(cfg['receiver']['ip'], cfg['receiver']['port'], timeout=1.0)
            results.append({"node": "Receiver (E)", "target": f"{cfg['receiver']['ip']}:{cfg['receiver']['port']}", "status": "OK" if ok else "FAIL", "error": msg})
            self._send_json({"results": results})
        elif path == '/api/clear_raw':
            query = parse_qs(parsed.query)
            node_id = int(query.get('node_id', [1])[0])
            with STATE_LOCK:
                APP_STATE["raw_packets"][node_id] = []
            self._send_json({"success": True})
        elif path == '/api/upload':
            # Handle multipart file upload
            self._handle_upload()
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_upload(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            # Simple boundary parse
            boundary = self.headers.get_boundary()
            if boundary:
                parts = body.split(f"--{boundary}".encode())
                for part in parts:
                    if b'filename="' in part:
                        header_end = part.find(b"\r\n\r\n")
                        file_data = part[header_end + 4:].rstrip(b"\r\n--")
                        dest = os.path.join(BASE_DIR, 'assets', 'input_image.png')
                        with open(dest, 'wb') as f:
                            f.write(file_data)
                        generate_noise_image(encrypt_bytes(file_data), os.path.join(BASE_DIR, 'output', 'encrypted_noise.png'))
                        chunks = fragment(encrypt_bytes(file_data), size=FRAGMENT_SIZE)
                        self._send_json({"success": True, "total_chunks": len(chunks)})
                        return
            self._send_json({"success": False, "error": "No valid file parsed"})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _send_json(self, data: dict):
        encoded = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _serve_file(self, file_path: str, content_type: str):
        if not os.path.exists(file_path):
            self.send_error(404, f"File not found: {file_path}")
            return
        with open(file_path, 'rb') as f:
            content = f.read()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(content)


def start_web_server(port: int = 8080) -> int:
    """Finds available port and starts ThreadingHTTPServer in a background daemon thread."""
    current_port = port
    while current_port < port + 20:
        try:
            httpd = ThreadingHTTPServer(('0.0.0.0', current_port), LabHttpHandler)
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            return current_port
        except OSError:
            current_port += 1
    raise RuntimeError(f"Could not bind web server on ports {port}-{current_port}")


# ==============================================================================
# 7. MAIN ENTRYPOINT & LAB RUNNER
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Encrypted Image Flooding - Computer Networks Lab")
    parser.add_argument('--role', choices=['sender', 'intermediate', 'receiver', 'all_in_one'], help="Node role")
    parser.add_argument('--id', type=int, default=1, help="Intermediate node index (1 to 6)")
    parser.add_argument('--port', type=int, help="Transport listening port")
    parser.add_argument('--web-port', type=int, default=8080, help="Web dashboard port")
    parser.add_argument('--no-browser', action='store_true', help="Do not auto-open browser")
    args = parser.parse_args()

    local_ip = get_local_ip()

    print("\n" + "=" * 76)
    print("      IMAGE CRYPT — ENCRYPTED IMAGE FLOODING NETWORKS LAB")
    print("=" * 76)
    print(f"Local System IP: {local_ip}")
    print(f"Hostname:        {socket.gethostname()}")

    role = args.role

    # If no CLI role passed, ask the user
    if not role:
        print("\nSelect the role for THIS computer in the lab:")
        print("  [1] Sender / Master Coordinator  (Full Setup, Link Test, Transmission)")
        print("  [2] Intermediate System           (Forwarding Router & Raw Data Stream)")
        print("  [3] Receiver System               (Fragment Buffer & Decryption)")
        print("  [4] All-in-One Multi-Node Simulation (Run all nodes locally for testing)")

        while True:
            c = input("\nEnter choice [1-4, Default=1]: ").strip()
            if not c or c == '1':
                role = 'sender'
                break
            elif c == '2':
                role = 'intermediate'
                break
            elif c == '3':
                role = 'receiver'
                break
            elif c == '4':
                role = 'all_in_one'
                break
            print("Please enter 1, 2, 3, or 4.")

    APP_STATE["role"] = role
    APP_STATE["system_ip"] = local_ip

    # --------------------------------------------------------------------------
    # MODE 1: SENDER / MASTER COORDINATOR
    # --------------------------------------------------------------------------
    if role == 'sender':
        config = run_configuration_wizard(local_ip)
        APP_STATE["config"] = config
        APP_STATE["transport_port"] = config["sender"]["port"]

        # Connection testing step:
        # "then test connection
        #  if it works
        #  we continue the script"
        run_connection_test(config, is_sender_local=True)

        # Switch to simple HTML, CSS, JS server
        web_port = start_web_server(args.web_port)
        APP_STATE["web_port"] = web_port

        local_url = f"http://localhost:{web_port}"
        net_url = f"http://{local_ip}:{web_port}"

        print("\n" + "=" * 76)
        print("               SWITCHED TO HTML, CSS, JS SERVER")
        print("=" * 76)
        print(f"Current System IP:     {local_ip}")
        print(f"Assigned Sender Port:  {config['sender']['port']}")
        print(f"Web Dashboard Port:    {web_port}")
        print(f"Local Access URL:      {local_url}")
        print(f"LAN Access URL:        {net_url}")
        print("=" * 76)

        if not args.no_browser:
            print("Launching web dashboard in browser...")
            webbrowser.open(local_url)

        print("\n[Sender Station active] Press Ctrl+C in this terminal to shut down.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down Sender...")

    # --------------------------------------------------------------------------
    # MODE 2: INTERMEDIATE NODE
    # --------------------------------------------------------------------------
    elif role == 'intermediate':
        node_id = args.id
        if not args.id:
            while True:
                id_str = input("Which Intermediate Node is this? (1 to 6) [Default=1]: ").strip()
                if not id_str:
                    node_id = 1
                    break
                try:
                    nid = int(id_str)
                    if 1 <= nid <= 6:
                        node_id = nid
                        break
                except ValueError:
                    pass

        default_listen = 5000 + node_id
        listen_port = args.port or select_port(f"Intermediate Node {node_id}", [default_listen, 6000 + node_id], 0)
        rec_ip = input("Enter Receiver System IP [Default=127.0.0.1]: ").strip() or "127.0.0.1"
        rec_port = select_port("Receiver System", [5004, 5054], 0)

        APP_STATE["role"] = f"intermediate_{node_id}"
        APP_STATE["transport_port"] = listen_port
        APP_STATE["config"] = {
            "receiver": {"ip": rec_ip, "port": rec_port},
            "intermediates": [{"id": node_id, "name": f"Intermediate Node {node_id}", "ip": local_ip, "port": listen_port}]
        }

        # Start router
        router = IntermediateService(node_id, listen_port, rec_ip, rec_port)
        router.start()

        # Start web dashboard
        web_port = start_web_server(args.web_port)
        APP_STATE["web_port"] = web_port

        local_url = f"http://localhost:{web_port}"
        print(f"\n[Intermediate Node {node_id}] Listening on {local_ip}:{listen_port}")
        print(f"Web Dashboard: {local_url}")
        if not args.no_browser:
            webbrowser.open(f"{local_url}/#intermediate-screen")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            router.running = False
            print("\nShutting down Intermediate Node...")

    # --------------------------------------------------------------------------
    # MODE 3: RECEIVER NODE
    # --------------------------------------------------------------------------
    elif role == 'receiver':
        listen_port = args.port or select_port("Receiver System", [5004, 5054, 8004], 0)
        APP_STATE["role"] = "receiver"
        APP_STATE["transport_port"] = listen_port
        APP_STATE["config"] = {"receiver": {"ip": local_ip, "port": listen_port}}

        # Start receiver service
        receiver = ReceiverService(listen_port)
        receiver.start()

        # Start web dashboard
        web_port = start_web_server(args.web_port)
        APP_STATE["web_port"] = web_port

        local_url = f"http://localhost:{web_port}"
        print(f"\n[Receiver Node] Listening on {local_ip}:{listen_port}")
        print(f"Web Dashboard: {local_url}")
        if not args.no_browser:
            webbrowser.open(f"{local_url}/#receiver-screen")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            receiver.running = False
            print("\nShutting down Receiver...")

    # --------------------------------------------------------------------------
    # MODE 4: ALL-IN-ONE LOCAL MULTI-NODE SIMULATION (DEMO)
    # --------------------------------------------------------------------------
    elif role == 'all_in_one':
        print("\nStarting All-in-One Multi-Node Lab Simulation...")
        APP_STATE["role"] = "all_in_one"
        APP_STATE["transport_port"] = 5000

        config = {
            "sender": {"ip": "127.0.0.1", "port": 5000},
            "receiver": {"ip": "127.0.0.1", "port": 5004},
            "intermediates": [
                {"id": 1, "name": "Intermediate 1 (Node B)", "ip": "127.0.0.1", "port": 5001},
                {"id": 2, "name": "Intermediate 2 (Node C)", "ip": "127.0.0.1", "port": 5002},
                {"id": 3, "name": "Intermediate 3 (Node D)", "ip": "127.0.0.1", "port": 5003}
            ]
        }
        APP_STATE["config"] = config

        # 1. Start Receiver
        receiver = ReceiverService(5004)
        receiver.start()

        # 2. Start Intermediates (B, C, D)
        for node in config["intermediates"]:
            router = IntermediateService(node["id"], node["port"], "127.0.0.1", 5004)
            router.start()

        time.sleep(0.5)

        # 3. Connection Test
        run_connection_test(config, is_sender_local=True)

        # 4. Start Web Server
        web_port = start_web_server(args.web_port)
        APP_STATE["web_port"] = web_port
        local_url = f"http://localhost:{web_port}"

        print("\n" + "=" * 76)
        print("          ALL-IN-ONE MULTI-NODE LAB SIMULATION ONLINE")
        print("=" * 76)
        print(f"Web Dashboard: {local_url}")
        print("=" * 76)

        if not args.no_browser:
            webbrowser.open(local_url)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down All-in-One Simulation...")


if __name__ == '__main__':
    main()
