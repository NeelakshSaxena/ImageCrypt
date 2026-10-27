# Encrypted Image Flooding-Network Simulation

A network simulation and lab demonstration suite of a secure, flooding-based network topology carrying encrypted image fragments across distributed systems (or localhost sockets).

- **Node A (Sender):** Loads an image, encrypts it using a custom Bit-Shuffle symmetric cipher, fragments it into 1024-byte payloads, prepends a 17-byte `struct`-packed header (`!4sBBIHHBH`), and floods all fragments to intermediate nodes.
- **Intermediate Nodes (B, C, D... up to 6 nodes):** Intercept headers on the wire, detect loops by tracking seen `packet_id`s (dropping duplicates), decrement Time-To-Live (TTL), drop expired packets (TTL=0), and forward unmodified payloads to the receiver.
- **Node E (Receiver):** Receives packets from multiple redundant flooding paths, safely drops duplicates, buffers in-order fragments, reassembles the complete payload, decrypts the image, and writes the byte-exact output to disk.

---

## 🌟 Computer Networks Lab Suite (`lab_network.py`)

> [!TIP]
> **Allotted 3 physical PCs in the lab?** Check out the dedicated step-by-step setup guide: [**`lab_how_to.md`**](./lab_how_to.md).

Designed for **Computer Networks Labs with up to 70 networked PCs**, this standalone script allows students and instructors to deploy the simulation across multiple physical systems communicating over LAN via IP addresses and TCP sockets, complete with an interactive web dashboard.

### Key Features
1. **Interactive Setup Questionnaire**:
   - Asks for the **Sender System IP** (with local IP auto-detection) and port selection (`5000`, `5050`, `8000`, or custom).
   - Asks for the **Receiver System IP** and port selection (`5004`, `5054`, `8004`, or custom).
   - Asks for the **number of Intermediate systems** (flexible between **1 and 6**, minimum 1).
   - For each intermediate system, prompts for its IP address and port options (`5001`, `5002`, `5003`...).

2. **Automated Socket Connection Test**:
   - Automatically probes all configured endpoints via TCP sockets prior to starting.
   - Displays a clean connection status table.
   - If all connections pass, it continues automatically.
   - If any node is waiting or unreachable, provides interactive options: `[R] Retry`, `[F] Force continue`, or `[E] Edit configurations`.

3. **Built-in HTML, CSS & JavaScript Web Server**:
   - Launches a lightweight web server (default port `8080`) and automatically opens the browser.
   - **Persistent System Info Banner on every screen**:
     - Current System Role (`SENDER SYSTEM`, `INTERMEDIATE SYSTEM`, or `RECEIVER SYSTEM`)
     - Current System Local IP Address
     - Assigned Data Transport Port
     - Assigned Web Server Port
     - Network Link Status

4. **Dedicated Screen Views**:
   - **Sender Screen**:
     - Image drag-and-drop / file browser / lab sample loader.
     - Bit-Shuffle Cryptography visualizer (Invert bits `~b & 0xFF` → Permute `[5, 2, 7, 0, 4, 1, 6, 3]` → Subtract 42 → XOR with Key).
     - Generated ciphertext noise preview.
     - One-click flooding dispatcher with live progress bar and dispatch feed.
   - **Intermediate Screen (Raw Data Stream)**:
     - Shows current node credentials and forwarding destination (Receiver IP:Port).
     - **Live Raw Data Stream**: Real-time terminal feed of incoming packets on the wire.
     - **Packet Inspector & Hex Dump**: Formatted 16-byte hex dump with ASCII representation, decoded header fields (`magic`, `src_id`, `dest_id`, `packet_id`, `chunk_sequence`, `ttl`, `payload_length`), and routing decision badges (`FORWARDED`, `DROPPED_DUPLICATE`, `DROPPED_TTL`).
   - **Receiver Screen (Decryption & Reconstruction)**:
     - Dynamic **Fragment Buffer Matrix** grid illuminating chunks in emerald green as they arrive.
     - Redundant flooding duplicate filter counter.
     - Reverse Bit-Shuffle decryption and in-order byte reassembly.
     - Side-by-side comparison: Encrypted Ciphertext Noise vs Reconstructed Image with byte-exact **SHA-256 integrity match**.
     - One-click image download.
   - **Lab Topology & Diagnostics Screen**:
     - Interactive physical/virtual network graph with live socket link re-testing.

---

### How to Run `lab_network.py` in the Lab

#### Option A: Distributed Lab Mode (Across Multiple Physical PCs)

Run the script on any PC in the lab:
```bash
python lab_network.py
```

You will see the role selection menu:
```text
============================================================================
      IMAGE CRYPT — ENCRYPTED IMAGE FLOODING NETWORKS LAB
============================================================================
Local System IP: 192.168.1.15
Hostname:        LAB-PC-01

Select the role for THIS computer in the lab:
  [1] Sender / Master Coordinator  (Full Setup, Link Test, Transmission)
  [2] Intermediate System           (Forwarding Router & Raw Data Stream)
  [3] Receiver System               (Fragment Buffer & Decryption)
  [4] All-in-One Multi-Node Simulation (Run all nodes locally for testing)
```

1. **On the Receiver PC**:
   - Choose `[3] Receiver System`.
   - Confirm listening port (e.g. `5004`).
   - The Receiver starts listening and opens the Receiver Screen.

2. **On the Intermediate PCs (e.g. 3 to 6 PCs)**:
   - Choose `[2] Intermediate System`.
   - Enter node ID (1, 2, 3...), listening port (`5001`, `5002`...), and the Receiver's IP.
   - The Intermediate Router starts listening and opens the Intermediate Screen (Raw Data Stream).

3. **On the Sender PC**:
   - Choose `[1] Sender / Master Coordinator`.
   - Complete the interactive setup questionnaire.
   - The script tests connectivity to all other systems, confirms links, and opens the Sender Screen.
   - Click **"Start Network Flooding Transmission"** to flood image fragments across the network!

---

#### Option B: All-in-One Local Simulation (Single PC Testing)

To test the entire 5-node network, connection tests, and all web screens on a single computer without needing multiple PCs:

```bash
python lab_network.py --role all_in_one
```

This boots the Receiver (`5004`), 3 Intermediates (`5001`, `5002`, `5003`), runs connection tests, launches the web server on `http://localhost:8080`, and opens the dashboard in your default browser.

---

## Desktop GUI Suite for Lab Network (`gui.py`)

A modern desktop Tkinter control center is available to control and visualize `lab_network.py`:

1. **Activate the Virtual Environment**:
   ```powershell
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. **Launch the GUI**:
   ```bash
   python gui.py
   ```
3. **Features in `gui.py`**:
   - **Lab Network Deployment Control**: Launch `lab_network.py` in All-in-One simulation, Sender Station, Intermediate Router, or Receiver Station with custom web and transport ports.
   - **One-Click Web Dashboard**: Instant button to open `http://localhost:8080`.
   - **Socket Link Prober**: Interactive TCP testing across intermediate routers and receiver.
   - **3-Panel Visualizer**: Live side-by-side view of Original Image (Node A), Bit-Shuffle Encrypted Ciphertext Noise (Nodes B/C/D), and Decrypted Reconstructed Image (Node E) with byte-exact **SHA-256 verification**.

---

## Legacy CLI Mode (Manual Terminal Windows)

To run the nodes individually in separate terminals:

1. **Terminal 1 - Receiver Node E:**
   ```bash
   python nodes/receiver_e.py
   ```
2. **Terminals 2, 3, 4 - Intermediate Nodes B, C, D:**
   ```bash
   python nodes/intermediate_bcd.py --id 1
   python nodes/intermediate_bcd.py --id 2
   python nodes/intermediate_bcd.py --id 3
   ```
3. **Terminal 5 - Sender Node A:**
   ```bash
   python nodes/sender_a.py
   ```

---

## Automated Pytest Suite

To verify unit tests and integration tests programmatically:
```bash
pytest tests/ -v
```
All unit tests (`test_packet.py`, `test_crypto.py`, `test_fragmentation.py`, `test_intermediate.py`, `test_receiver.py`, `test_integration.py`) verify the pack/unpack round-trip, Bit-Shuffle symmetry, duplicate drops, TTL drops, and byte-exact SHA-256 verification.
