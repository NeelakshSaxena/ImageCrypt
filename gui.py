"""
gui.py: Modern Desktop GUI Suite for the Encrypted Image Flooding Network Lab (lab_network.py).

Provides a comprehensive control center for the Computer Networks Lab:
  1. Controls and manages lab_network.py subprocesses (All-in-One, Sender, Intermediate, Receiver).
  2. One-click Web Dashboard launcher (http://localhost:8080).
  3. Interactive TCP Socket link tester across all intermediate routers and receiver.
  4. Real-time 3-panel visualization:
     - Node A: Input Image Preview & Metadata.
     - Intermediate Nodes B/C/D: Bit-Shuffle Encrypted Ciphertext Noise Preview.
     - Node E: Decrypted Reconstructed Image Preview with SHA-256 Verification Badge.
  5. Multi-path flooding transmission trigger with live streaming console logs.
"""

import os
import sys
import time
import math
import json
import socket
import shutil
import hashlib
import threading
import subprocess
import webbrowser
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Project imports
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

from common.config import AES_KEY, TTL_DEFAULT, FRAGMENT_SIZE, NODE_PORTS
from common.packet import Packet
from common.crypto import encrypt_bytes, decrypt_bytes
from common.fragment import fragment, reassemble

# Safe PIL import with fallback
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Ensure necessary directories exist
os.makedirs(os.path.join(BASE_DIR, 'output'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'assets'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)


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
        return "127.0.0.1"


def probe_socket(ip: str, port: int, timeout: float = 0.8) -> tuple[bool, str]:
    """Tests if a TCP endpoint is actively listening."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, port))
        s.close()
        return True, "ONLINE"
    except socket.timeout:
        return False, "TIMEOUT"
    except ConnectionRefusedError:
        return False, "REFUSED"
    except Exception as e:
        return False, str(e)


class LabNetworkGUI:
    """Modern Desktop GUI Controller for lab_network.py and Image Flooding simulation."""

    def __init__(self, master):
        self.master = master
        master.title("ImageCrypt — Computer Networks Lab GUI Suite")
        master.geometry("1180x860")
        master.minsize(980, 720)

        # Style & Color Palette (Dark modern theme matching the Lab Web Dashboard)
        self.colors = {
            "bg": "#0b0f19",
            "card_bg": "#111827",
            "card_border": "#1f2937",
            "text": "#f9fafb",
            "text_muted": "#9ca3af",
            "accent_cyan": "#06b6d4",
            "accent_emerald": "#10b981",
            "accent_blue": "#3b82f6",
            "accent_purple": "#8b5cf6",
            "accent_amber": "#f59e0b",
            "accent_rose": "#ef4444",
            "console_bg": "#030712",
            "console_fg": "#4ade80"
        }

        master.configure(bg=self.colors["bg"])

        # State tracking
        self.processes = []
        self.python_exe = sys.executable or "python"
        self.selected_file_path = os.path.join(BASE_DIR, 'assets', 'input_image.png')
        self.local_ip = get_local_ip()
        self.web_port = 8080
        self.is_running = False
        self.poll_active = False

        self._build_header()
        self._build_lab_control_bar()
        self._build_pipeline_bar()
        self._build_preview_panels()
        self._build_log_console()

        # Load default asset image if present
        if os.path.exists(self.selected_file_path):
            self._load_input_preview(self.selected_file_path)

        self.log("[SYSTEM] ImageCrypt Lab GUI initialized. Ready to launch lab_network.py.", "info")

    # --------------------------------------------------------------------------
    # UI BUILDERS
    # --------------------------------------------------------------------------

    def _build_header(self):
        """Builds top system info banner showing IP, Hostname, and status."""
        header_frame = tk.Frame(self.master, bg=self.colors["card_bg"], pady=10, padx=16, highlightbackground=self.colors["card_border"], highlightthickness=1)
        header_frame.pack(fill=tk.X, padx=12, pady=(10, 6))

        # Title & Subtitle
        left_box = tk.Frame(header_frame, bg=self.colors["card_bg"])
        left_box.pack(side=tk.LEFT)

        title_lbl = tk.Label(left_box, text="IMAGECRYPT LAB CONTROL SUITE", fg=self.colors["accent_cyan"], bg=self.colors["card_bg"], font=("Segoe UI", 13, "bold"))
        title_lbl.pack(anchor=tk.W)

        sub_lbl = tk.Label(left_box, text=f"Multi-Path Flooding Simulation  •  Local IP: {self.local_ip}  •  Host: {socket.gethostname()}", fg=self.colors["text_muted"], bg=self.colors["card_bg"], font=("Segoe UI", 9))
        sub_lbl.pack(anchor=tk.W)

        # Status badge
        right_box = tk.Frame(header_frame, bg=self.colors["card_bg"])
        right_box.pack(side=tk.RIGHT)

        self.status_badge = tk.Label(right_box, text="● LAB OFFLINE", fg=self.colors["accent_rose"], bg=self.colors["card_bg"], font=("Segoe UI", 10, "bold"))
        self.status_badge.pack(side=tk.RIGHT, padx=6)

    def _build_lab_control_bar(self):
        """Builds configuration bar for selecting role and starting lab_network.py."""
        bar_frame = tk.LabelFrame(self.master, text="  Lab Network Deployment (lab_network.py)  ", bg=self.colors["card_bg"], fg=self.colors["text"], font=("Segoe UI", 9, "bold"), padx=12, pady=8, highlightbackground=self.colors["card_border"], highlightthickness=1)
        bar_frame.pack(fill=tk.X, padx=12, pady=4)

        # Row 1: Role Selection & Port
        row1 = tk.Frame(bar_frame, bg=self.colors["card_bg"])
        row1.pack(fill=tk.X, pady=2)

        tk.Label(row1, text="Deployment Role:", fg=self.colors["text"], bg=self.colors["card_bg"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 6))

        self.role_var = tk.StringVar(value="all_in_one")
        role_options = [
            ("All-in-One Simulation (All Nodes + Web Lab)", "all_in_one"),
            ("Sender Station (Master Coordinator)", "sender"),
            ("Intermediate Router (B/C/D)", "intermediate"),
            ("Receiver Station (Sink/Decryption)", "receiver"),
            ("Legacy Standalone Nodes (nodes/ folder)", "legacy")
        ]
        self.role_combo = ttk.Combobox(row1, textvariable=self.role_var, values=[r[0] for r in role_options], state="readonly", width=42)
        self.role_combo.current(0)
        self.role_combo.pack(side=tk.LEFT, padx=6)

        # Web Port Entry
        tk.Label(row1, text="Web Port:", fg=self.colors["text"], bg=self.colors["card_bg"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(14, 4))
        self.web_port_entry = tk.Entry(row1, width=7, bg="#1e293b", fg=self.colors["text"], insertbackground=self.colors["text"], font=("Segoe UI", 9))
        self.web_port_entry.insert(0, "8080")
        self.web_port_entry.pack(side=tk.LEFT)

        # Intermediate ID Spinbox
        tk.Label(row1, text="Node ID (If Interm.):", fg=self.colors["text_muted"], bg=self.colors["card_bg"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(14, 4))
        self.node_id_spin = tk.Spinbox(row1, from_=1, to=6, width=4, bg="#1e293b", fg=self.colors["text"], insertbackground=self.colors["text"])
        self.node_id_spin.pack(side=tk.LEFT)

        # Row 2: Action Buttons
        row2 = tk.Frame(bar_frame, bg=self.colors["card_bg"])
        row2.pack(fill=tk.X, pady=(8, 2))

        self.btn_start_lab = tk.Button(row2, text="🚀 1. Start Lab Network", command=self.start_lab_network, bg=self.colors["accent_emerald"], fg="#052e16", activebackground="#34d399", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4, cursor="hand2")
        self.btn_start_lab.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop_lab = tk.Button(row2, text="🛑 Stop Lab", command=self.stop_lab_network, bg=self.colors["accent_rose"], fg="#ffffff", activebackground="#f87171", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4, state=tk.DISABLED, cursor="hand2")
        self.btn_stop_lab.pack(side=tk.LEFT, padx=6)

        self.btn_open_web = tk.Button(row2, text="🌐 Open Web Dashboard", command=self.open_web_dashboard, bg=self.colors["accent_cyan"], fg="#082f49", activebackground="#38bdf8", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4, cursor="hand2")
        self.btn_open_web.pack(side=tk.LEFT, padx=6)

        self.btn_test_links = tk.Button(row2, text="🔌 Probe Socket Links", command=self.test_socket_connections, bg=self.colors["accent_amber"], fg="#451a03", activebackground="#fbbf24", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4, cursor="hand2")
        self.btn_test_links.pack(side=tk.LEFT, padx=6)

    def _build_pipeline_bar(self):
        """Builds action buttons for image selection, encryption, and transmission."""
        pipe_frame = tk.LabelFrame(self.master, text="  Transmission Pipeline Controls  ", bg=self.colors["card_bg"], fg=self.colors["text"], font=("Segoe UI", 9, "bold"), padx=12, pady=8, highlightbackground=self.colors["card_border"], highlightthickness=1)
        pipe_frame.pack(fill=tk.X, padx=12, pady=4)

        box = tk.Frame(pipe_frame, bg=self.colors["card_bg"])
        box.pack(fill=tk.X)

        self.btn_select_img = tk.Button(box, text="📁 2. Select Image", command=self.select_image, bg=self.colors["accent_blue"], fg="#ffffff", activebackground="#60a5fa", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4, cursor="hand2")
        self.btn_select_img.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_encrypt_img = tk.Button(box, text="🔒 3. Bit-Shuffle Encrypt", command=self.encrypt_image, bg=self.colors["accent_purple"], fg="#ffffff", activebackground="#a78bfa", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4, cursor="hand2")
        self.btn_encrypt_img.pack(side=tk.LEFT, padx=8)

        self.btn_flood_send = tk.Button(box, text="⚡ 4. Flood Multi-Path (Transmit)", command=self.send_image, bg="#ec4899", fg="#ffffff", activebackground="#f472b6", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=12, pady=4, cursor="hand2")
        self.btn_flood_send.pack(side=tk.LEFT, padx=8)

        # Info label
        self.pipe_info_lbl = tk.Label(box, text="Ready for transmission", fg=self.colors["text_muted"], bg=self.colors["card_bg"], font=("Segoe UI", 9, "italic"))
        self.pipe_info_lbl.pack(side=tk.RIGHT, padx=6)

    def _build_preview_panels(self):
        """Builds the 3 preview panels for Node A, Intermediate B/C/D, and Node E."""
        panels_frame = tk.Frame(self.master, bg=self.colors["bg"])
        panels_frame.pack(fill=tk.BOTH, expand=False, padx=12, pady=6)

        # 1. Panel Node A (Input Preview)
        self.panel_a = tk.LabelFrame(panels_frame, text="  Node A: Original Input  ", bg=self.colors["card_bg"], fg=self.colors["accent_blue"], font=("Segoe UI", 9, "bold"), padx=6, pady=6, highlightbackground=self.colors["card_border"], highlightthickness=1)
        self.panel_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        self.lbl_img_a = tk.Label(self.panel_a, text="No Image Loaded", bg="#1e293b", fg=self.colors["text_muted"], width=32, height=13)
        self.lbl_img_a.pack(fill=tk.BOTH, expand=True)

        self.lbl_meta_a = tk.Label(self.panel_a, text="Source: None", bg=self.colors["card_bg"], fg=self.colors["text_muted"], font=("Segoe UI", 8))
        self.lbl_meta_a.pack(anchor=tk.W, pady=(4, 0))

        # 2. Panel Intermediate B/C/D (Ciphertext Noise)
        self.panel_bcd = tk.LabelFrame(panels_frame, text="  Nodes B/C/D: Wire Ciphertext  ", bg=self.colors["card_bg"], fg=self.colors["accent_purple"], font=("Segoe UI", 9, "bold"), padx=6, pady=6, highlightbackground=self.colors["card_border"], highlightthickness=1)
        self.panel_bcd.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        self.lbl_img_bcd = tk.Label(self.panel_bcd, text="Waiting for Encryption...", bg="#1e293b", fg=self.colors["text_muted"], width=32, height=13)
        self.lbl_img_bcd.pack(fill=tk.BOTH, expand=True)

        self.lbl_meta_bcd = tk.Label(self.panel_bcd, text="Cipher: Invert → Shuffle → Sub 42 → XOR", bg=self.colors["card_bg"], fg=self.colors["text_muted"], font=("Segoe UI", 8))
        self.lbl_meta_bcd.pack(anchor=tk.W, pady=(4, 0))

        # 3. Panel Node E (Reconstructed & Decrypted)
        self.panel_e = tk.LabelFrame(panels_frame, text="  Node E: Decrypted Output  ", bg=self.colors["card_bg"], fg=self.colors["accent_emerald"], font=("Segoe UI", 9, "bold"), padx=6, pady=6, highlightbackground=self.colors["card_border"], highlightthickness=1)
        self.panel_e.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        self.lbl_img_e = tk.Label(self.panel_e, text="Waiting for Flooded Chunks...", bg="#1e293b", fg=self.colors["text_muted"], width=32, height=13)
        self.lbl_img_e.pack(fill=tk.BOTH, expand=True)

        self.lbl_meta_e = tk.Label(self.panel_e, text="Integrity: Pending Transmission", bg=self.colors["card_bg"], fg=self.colors["text_muted"], font=("Segoe UI", 8))
        self.lbl_meta_e.pack(anchor=tk.W, pady=(4, 0))

    def _build_log_console(self):
        """Builds terminal log console with auto-scroll and clear button."""
        console_frame = tk.LabelFrame(self.master, text="  Live Network Stream & Diagnostics  ", bg=self.colors["card_bg"], fg=self.colors["text"], font=("Segoe UI", 9, "bold"), padx=8, pady=4, highlightbackground=self.colors["card_border"], highlightthickness=1)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 10))

        top_ctrl = tk.Frame(console_frame, bg=self.colors["card_bg"])
        top_ctrl.pack(fill=tk.X, pady=(0, 4))

        tk.Label(top_ctrl, text="Terminal Output & Routing Events", bg=self.colors["card_bg"], fg=self.colors["text_muted"], font=("Segoe UI", 8)).pack(side=tk.LEFT)

        btn_clear = tk.Button(top_ctrl, text="Clear Console", command=self.clear_logs, bg="#374151", fg="#ffffff", font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=1, cursor="hand2")
        btn_clear.pack(side=tk.RIGHT)

        # Text Widget + Scrollbar
        text_frame = tk.Frame(console_frame, bg=self.colors["console_bg"])
        text_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(text_frame, bg=self.colors["console_bg"], fg=self.colors["console_fg"], insertbackground=self.colors["console_fg"], font=("Consolas", 9), yscrollcommand=scrollbar.set, wrap=tk.WORD, height=8)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Color Tags for Log Highlighting
        self.log_text.tag_config("info", foreground="#38bdf8")
        self.log_text.tag_config("success", foreground="#4ade80")
        self.log_text.tag_config("warn", foreground="#facc15")
        self.log_text.tag_config("error", foreground="#f87171")
        self.log_text.tag_config("dim", foreground="#6b7280")

    # --------------------------------------------------------------------------
    # LOGGING UTILITIES
    # --------------------------------------------------------------------------

    def log(self, message: str, tag: str = "dim"):
        """Appends a timestamped line to the live console."""
        timestamp = time.strftime("[%H:%M:%S] ")
        self.log_text.insert(tk.END, timestamp, "dim")
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.master.update_idletasks()

    def clear_logs(self):
        """Clears the console text."""
        self.log_text.delete('1.0', tk.END)

    # --------------------------------------------------------------------------
    # LAB NETWORK PROCESS CONTROL
    # --------------------------------------------------------------------------

    def start_lab_network(self):
        """Launches lab_network.py with the selected role and ports."""
        selected_role_label = self.role_combo.get()
        role_map = {
            "All-in-One Simulation (All Nodes + Web Lab)": "all_in_one",
            "Sender Station (Master Coordinator)": "sender",
            "Intermediate Router (B/C/D)": "intermediate",
            "Receiver Station (Sink/Decryption)": "receiver",
            "Legacy Standalone Nodes (nodes/ folder)": "legacy"
        }
        role = role_map.get(selected_role_label, "all_in_one")

        try:
            self.web_port = int(self.web_port_entry.get().strip() or "8080")
        except ValueError:
            self.web_port = 8080

        node_id = int(self.node_id_spin.get().strip() or "1")

        # Clean previous output artifacts
        for f in ['lab_received_image.png', 'received_image.png']:
            p = os.path.join(BASE_DIR, 'output', f)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        self.lbl_img_e.config(image='', text="Waiting for Flooded Chunks...")
        self.lbl_meta_e.config(text="Integrity: Pending Transmission", fg=self.colors["text_muted"])

        if role == "legacy":
            self._start_legacy_nodes()
            return

        # Build command line for lab_network.py
        script_path = os.path.join(BASE_DIR, 'lab_network.py')
        cmd = [self.python_exe, script_path, '--role', role, '--web-port', str(self.web_port)]

        if role == "intermediate":
            cmd.extend(['--id', str(node_id), '--port', str(5000 + node_id)])
        elif role == "receiver":
            cmd.extend(['--port', '5004'])
        elif role == "sender":
            cmd.extend(['--port', '5000'])

        self.log(f"=> Spawning lab_network.py [{role.upper()}] on web port {self.web_port}...", "info")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            self.processes.append(proc)
            self.is_running = True

            # Start streaming stdout
            threading.Thread(target=self._stream_process_output, args=(proc,), daemon=True).start()

            # Update UI state
            self.status_badge.config(text=f"● ONLINE ({role.upper()})", fg=self.colors["accent_emerald"])
            self.btn_start_lab.config(state=tk.DISABLED)
            self.btn_stop_lab.config(state=tk.NORMAL)
            self.pipe_info_lbl.config(text=f"Network active on port {self.web_port}", fg=self.colors["accent_emerald"])

            self.log(f"[SUCCESS] lab_network.py active. Access Web Dashboard at http://localhost:{self.web_port}", "success")

        except Exception as e:
            self.log(f"[ERROR] Failed to launch lab_network.py: {e}", "error")

    def _start_legacy_nodes(self):
        """Starts independent processes for B, C, D, E from nodes/ folder."""
        nodes_dir = os.path.join(BASE_DIR, 'nodes')
        self.log("=> Starting standalone legacy nodes (B, C, D, E)...", "info")
        try:
            pe = subprocess.Popen([self.python_exe, os.path.join(nodes_dir, 'receiver_e.py')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            pb = subprocess.Popen([self.python_exe, os.path.join(nodes_dir, 'intermediate_bcd.py'), '--id', '1'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            pc = subprocess.Popen([self.python_exe, os.path.join(nodes_dir, 'intermediate_bcd.py'), '--id', '2'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            pd = subprocess.Popen([self.python_exe, os.path.join(nodes_dir, 'intermediate_bcd.py'), '--id', '3'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            self.processes.extend([pe, pb, pc, pd])
            for p in [pe, pb, pc, pd]:
                threading.Thread(target=self._stream_process_output, args=(p,), daemon=True).start()

            self.is_running = True
            self.status_badge.config(text="● ONLINE (LEGACY NODES)", fg=self.colors["accent_emerald"])
            self.btn_start_lab.config(state=tk.DISABLED)
            self.btn_stop_lab.config(state=tk.NORMAL)
            self.log("[SUCCESS] Legacy nodes B (5001), C (5002), D (5003), E (5004) online.", "success")
        except Exception as e:
            self.log(f"[ERROR] Failed to start legacy nodes: {e}", "error")

    def _stream_process_output(self, proc):
        """Reads stdout lines from a subprocess and displays them in the console."""
        try:
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
                clean = line.rstrip()
                if clean:
                    tag = "dim"
                    if "ERROR" in clean.upper() or "FAIL" in clean.upper():
                        tag = "error"
                    elif "SUCCESS" in clean.upper() or "ONLINE" in clean.upper() or "VERIFIED" in clean.upper():
                        tag = "success"
                    elif "RECEIVE" in clean.upper() or "FORWARD" in clean.upper() or "DISPATCH" in clean.upper():
                        tag = "info"
                    elif "DROP" in clean.upper():
                        tag = "warn"
                    self.log(clean, tag)
        except Exception:
            pass

    def stop_lab_network(self):
        """Terminates all running lab subprocesses cleanly."""
        if not self.processes:
            return

        self.log("=> Terminating all active lab network processes...", "warn")
        for p in self.processes:
            try:
                p.terminate()
                p.wait(timeout=1.0)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

        self.processes = []
        self.is_running = False

        self.status_badge.config(text="● LAB OFFLINE", fg=self.colors["accent_rose"])
        self.btn_start_lab.config(state=tk.NORMAL)
        self.btn_stop_lab.config(state=tk.DISABLED)
        self.pipe_info_lbl.config(text="Lab stopped", fg=self.colors["text_muted"])
        self.log("[INFO] All network subprocesses stopped.", "info")

    def open_web_dashboard(self):
        """Opens default browser to the lab web dashboard."""
        try:
            port = int(self.web_port_entry.get().strip() or "8080")
        except ValueError:
            port = 8080
        url = f"http://localhost:{port}"
        self.log(f"Opening browser to {url}...", "info")
        webbrowser.open(url)

    def test_socket_connections(self):
        """Performs live TCP socket probes on intermediate routers and receiver."""
        self.log("\n========================================================", "dim")
        self.log("          STARTING TCP SOCKET LINK PROBE TEST", "info")
        self.log("========================================================", "dim")

        targets = [
            ("Intermediate 1 (Node B)", "127.0.0.1", 5001),
            ("Intermediate 2 (Node C)", "127.0.0.1", 5002),
            ("Intermediate 3 (Node D)", "127.0.0.1", 5003),
            ("Receiver System (Node E)", "127.0.0.1", 5004)
        ]

        def run_probes():
            all_ok = True
            for name, ip, port in targets:
                ok, status = probe_socket(ip, port, timeout=1.0)
                if ok:
                    self.log(f"  [PASS] {name:<26} -> {ip}:{port} [ONLINE]", "success")
                else:
                    self.log(f"  [FAIL] {name:<26} -> {ip}:{port} [{status}]", "error")
                    all_ok = False
                time.sleep(0.05)

            if all_ok:
                self.log("=> ALL NETWORK LINKS VERIFIED AND HEALTHY!", "success")
            else:
                self.log("=> Some endpoints are offline. Click '1. Start Lab Network' first.", "warn")

        threading.Thread(target=run_probes, daemon=True).start()

    # --------------------------------------------------------------------------
    # IMAGE PIPELINE ACTIONS
    # --------------------------------------------------------------------------

    def select_image(self):
        """Opens file dialog and loads the selected image into Panel A."""
        file_path = filedialog.askopenfilename(
            title="Select Image to Encrypt & Transmit",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        self.selected_file_path = file_path
        self._load_input_preview(file_path)

        # Copy to assets/input_image.png so lab_network.py uses it
        asset_target = os.path.join(BASE_DIR, 'assets', 'input_image.png')
        try:
            if os.path.abspath(file_path) != os.path.abspath(asset_target):
                shutil.copy(file_path, asset_target)
        except Exception as e:
            self.log(f"Note copying image to assets: {e}", "dim")

        self.pipe_info_lbl.config(text=f"Loaded: {os.path.basename(file_path)}", fg=self.colors["accent_blue"])
        self.log(f"[IMAGE] Selected input file: {file_path}", "info")

    def _load_input_preview(self, file_path: str):
        """Renders input image thumbnail in Panel A."""
        if not HAS_PIL:
            self.lbl_img_a.config(text=f"[PIL Not Installed]\n{os.path.basename(file_path)}")
            return

        try:
            img = Image.open(file_path)
            w, h = img.size
            size_kb = round(os.path.getsize(file_path) / 1024, 1)

            img.thumbnail((260, 260))
            self.photo_a = ImageTk.PhotoImage(img)
            self.lbl_img_a.config(image=self.photo_a, text="")
            self.lbl_meta_a.config(text=f"{os.path.basename(file_path)} • {w}x{h}px • {size_kb} KB")
        except Exception as e:
            self.lbl_img_a.config(text=f"Error loading image:\n{e}")

    def encrypt_image(self):
        """Executes the Bit-Shuffle cipher and renders ciphertext noise in Panel B."""
        if not self.selected_file_path or not os.path.exists(self.selected_file_path):
            messagebox.showwarning("No Image", "Please select an image first.")
            return

        self.log("\n=> Commencing Custom Bit-Shuffle Symmetric Encryption...", "info")
        self.log("  [Step 1] Invert 8 bits: ~b & 0xFF", "dim")
        self.log("  [Step 2] Permute bits with key: [5, 2, 7, 0, 4, 1, 6, 3]", "dim")
        self.log("  [Step 3] Subtract MAGIC_NUMBER (42) mod 256", "dim")
        self.log("  [Step 4] XOR with shared AES_KEY bytes", "dim")

        try:
            with open(self.selected_file_path, 'rb') as f:
                clear_bytes = f.read()

            encrypted_bytes = encrypt_bytes(clear_bytes)
            num_chunks = math.ceil(len(encrypted_bytes) / FRAGMENT_SIZE)

            # Generate Grayscale Noise Visualization
            side = int(math.ceil(math.sqrt(len(encrypted_bytes))))
            padded = encrypted_bytes + os.urandom(side * side - len(encrypted_bytes))
            noise_img = Image.frombytes('L', (side, side), padded)
            resample_filter = getattr(Image, 'Resampling', Image).NEAREST
            noise_img = noise_img.resize((260, 260), resample=resample_filter)

            # Save noise artifact
            noise_path = os.path.join(BASE_DIR, 'output', 'encrypted_noise.png')
            noise_img.save(noise_path)

            if HAS_PIL:
                self.photo_bcd = ImageTk.PhotoImage(noise_img)
                self.lbl_img_bcd.config(image=self.photo_bcd, text="")
                self.lbl_meta_bcd.config(text=f"Ciphertext: {len(encrypted_bytes)} bytes • {num_chunks} fragments")

            self.pipe_info_lbl.config(text=f"Encrypted ({num_chunks} Chunks Ready)", fg=self.colors["accent_purple"])
            self.log(f"[SUCCESS] Encryption complete! Generated {num_chunks} fragments of 1024-byte payloads.", "success")

        except Exception as e:
            self.log(f"[ERROR] Encryption failed: {e}", "error")

    def send_image(self):
        """Floods encrypted fragments to intermediate nodes via lab_network or direct dispatch."""
        if not self.selected_file_path or not os.path.exists(self.selected_file_path):
            messagebox.showwarning("No Image", "Please select an image first.")
            return

        self.lbl_img_e.config(image='', text="Collecting Flooded Fragments...")
        self.lbl_meta_e.config(text="Integrity: Collecting & Decrypting...", fg=self.colors["accent_amber"])

        # Try API trigger if lab_network web server is active
        def run_transmission():
            self.log("=> Dispatching multi-path flooding transmission...", "info")
            api_success = False

            # Check if web dashboard API is alive
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{self.web_port}/api/transmit", data=b'', method='POST')
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    if resp.status == 200:
                        self.log("[API] Triggered transmission via lab_network.py REST endpoint (/api/transmit).", "success")
                        api_success = True
            except Exception:
                api_success = False

            # If web server not online, run standalone sender fallback
            if not api_success:
                self.log("[FALLBACK] Web API not reachable. Dispatched via direct multi-path socket flooding...", "dim")
                self._direct_flooding_dispatch()

            # Start monitoring receiver reconstruction
            self.master.after(500, self._start_output_polling)

        threading.Thread(target=run_transmission, daemon=True).start()

    def _direct_flooding_dispatch(self):
        """Direct socket flooding fallback if lab web server is not running."""
        try:
            with open(self.selected_file_path, 'rb') as f:
                clear_bytes = f.read()

            encrypted_bytes = encrypt_bytes(clear_bytes)
            chunks = fragment(encrypted_bytes, size=FRAGMENT_SIZE)
            total = len(chunks)

            targets = [("127.0.0.1", 5001), ("127.0.0.1", 5002), ("127.0.0.1", 5003)]

            sent = 0
            for seq, payload in enumerate(chunks):
                pkt = Packet(
                    src_id=0,
                    dest_id=4,
                    packet_id=1000 + seq,
                    chunk_sequence=seq,
                    total_chunks=total,
                    ttl=TTL_DEFAULT,
                    payload=payload
                )
                data = pkt.pack()
                for ip, port in targets:
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(1.0)
                        s.connect((ip, port))
                        s.sendall(data)
                        s.close()
                        sent += 1
                    except Exception:
                        pass
                time.sleep(0.01)

            self.log(f"[SENDER] Flooded {total} fragments ({sent} packets) across routers.", "success")
        except Exception as e:
            self.log(f"[ERROR] Direct dispatch failed: {e}", "error")

    # --------------------------------------------------------------------------
    # OUTPUT MONITOR & VERIFICATION
    # --------------------------------------------------------------------------

    def _start_output_polling(self):
        """Polls for the receiver's output image for up to 10 seconds."""
        if self.poll_active:
            return
        self.poll_active = True
        self.log("=> Monitoring Node E for completed image reconstruction...", "dim")

        def poll():
            candidates = [
                os.path.join(BASE_DIR, 'output', 'lab_received_image.png'),
                os.path.join(BASE_DIR, 'output', 'received_image.png')
            ]
            for _ in range(25):  # Check for up to 12.5 seconds
                for p in candidates:
                    if os.path.exists(p) and os.path.getsize(p) > 0:
                        time.sleep(0.3)  # Allow file write to flush completely
                        self.master.after(0, lambda target=p: self._render_received_image(target))
                        self.poll_active = False
                        return
                time.sleep(0.5)

            self.log("[TIMEOUT] No reconstructed image file detected yet. Check router logs.", "warn")
            self.lbl_meta_e.config(text="Timeout: Incomplete fragments", fg=self.colors["accent_rose"])
            self.poll_active = False

        threading.Thread(target=poll, daemon=True).start()

    def _render_received_image(self, image_path: str):
        """Displays reassembled image and verifies byte-for-byte SHA-256 match."""
        if not HAS_PIL:
            self.lbl_img_e.config(text=f"[Reconstructed File Created]\n{os.path.basename(image_path)}")
            return

        try:
            # Read bytes to verify hash against original
            with open(image_path, 'rb') as f:
                rec_bytes = f.read()
            rec_sha = hashlib.sha256(rec_bytes).hexdigest()

            orig_sha = None
            if self.selected_file_path and os.path.exists(self.selected_file_path):
                with open(self.selected_file_path, 'rb') as f:
                    orig_sha = hashlib.sha256(f.read()).hexdigest()

            # Render in panel
            img = Image.open(image_path)
            w, h = img.size
            img.thumbnail((260, 260))
            self.photo_e = ImageTk.PhotoImage(img)
            self.lbl_img_e.config(image=self.photo_e, text="")

            if orig_sha and rec_sha == orig_sha:
                status_text = f"✔ 100% BYTE-EXACT MATCH\nSHA-256: {rec_sha[:16]}..."
                self.lbl_meta_e.config(text=status_text, fg=self.colors["accent_emerald"])
                self.log(f"[VERIFIED] SHA-256 matches original: {rec_sha}", "success")
                self.pipe_info_lbl.config(text="Reconstruction 100% Verified!", fg=self.colors["accent_emerald"])
            else:
                status_text = f"Image Reassembled • {w}x{h}px\nSHA-256: {rec_sha[:16]}..."
                self.lbl_meta_e.config(text=status_text, fg=self.colors["text"])
                self.log(f"[RECEIVER] Reassembled image written to {image_path}", "info")

        except Exception as e:
            self.log(f"[ERROR] Loading received image: {e}", "error")

    # --------------------------------------------------------------------------
    # WINDOW CLOSE HANDLER
    # --------------------------------------------------------------------------

    def on_closing(self):
        """Gracefully shuts down all subprocesses on window close."""
        self.stop_lab_network()
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LabNetworkGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
