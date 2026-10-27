# Computer Networks Lab Setup Guide: 3-System Deployment

This guide provides step-by-step instructions for deploying the **ImageCrypt** network simulation across **3 physical lab computers** connected over LAN.

---

## Architecture Overview (3 Systems)

```
┌────────────────────────┐      ┌───────────────────────────┐      ┌────────────────────────┐
│  SYSTEM 1: SENDER (A)  │ ───> │ SYSTEM 2: INTERMEDIATE (B)│ ───> │  SYSTEM 3: RECEIVER (E)│
│  IP: e.g. 192.168.1.101│      │  IP: e.g. 192.168.1.102   │      │  IP: e.g. 192.168.1.103│
│  Port: 5000            │      │  Port: 5001               │      │  Port: 5004            │
└────────────────────────┘      └───────────────────────────┘      └────────────────────────┘
```

---

## Phase 0: Pre-Flight Check (Crucial for Lab Networks)

Before launching any code, ensure all 3 computers can communicate over the local network:

1. **Find each computer's IP address**:
   Open **PowerShell** or **Command Prompt** on each system and run:
   ```powershell
   ipconfig
   ```
   Look for the **IPv4 Address** under your active Ethernet or Wi-Fi adapter (e.g., `192.168.1.X`). Note them down:
   * **System 1 (Sender) IP:** `_________________`
   * **System 2 (Intermediate) IP:** `_________________`
   * **System 3 (Receiver) IP:** `_________________`

2. **Verify connectivity via `ping`**:
   From **System 1**, test reachability to the other two systems:
   ```powershell
   ping <System-2-IP>
   ping <System-3-IP>
   ```
   *(If ping requests time out, ensure all 3 PCs are connected to the same Wi-Fi/switch subnet, or temporarily set Windows Firewall to allow ICMP echo).*

---

## Phase 1: Download & Install (Perform on ALL 3 Systems)

Run these setup steps on **System 1, System 2, and System 3**:

### 1. Download the Codebase
**Option A — Using Git:**
```powershell
git clone https://github.com/NeelakshSaxena/ImageCrypt.git
cd ImageCrypt
```

**Option B — Direct Download (No Git installed):**
1. Download the project ZIP from GitHub and extract it to `C:\ImageCrypt` or Desktop.
2. Open PowerShell and navigate into the folder:
   ```powershell
   cd C:\path\to\ImageCrypt
   ```

### 2. Setup Python Environment & Dependencies
```powershell
# 1. Create a Python virtual environment
python -m venv venv

# 2. Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# Note: In standard Command Prompt (cmd), run: venv\Scripts\activate.bat

# 3. Install dependencies (Pillow, PyCryptodome, Pytest)
pip install -r requirements.txt
```

> [!IMPORTANT]
> **Windows Firewall Alert:** When running Python network scripts for the first time, Windows Defender will prompt: *"Windows Firewall has blocked some features of this app"*. **Check both "Private networks" and "Public networks" checkboxes, then click "Allow access".**

---

## Phase 2: Starting the Nodes (Order Matters!)

In networking, **listeners/servers must always be active before senders/clients initiate connections**. Start the computers in this exact sequence:

```
Start System 3 (Receiver) ➔ Start System 2 (Intermediate) ➔ Start System 1 (Sender)
```

---

### Step 1: Start SYSTEM 3 (Receiver Station)

On **System 3**, open PowerShell in the project directory with `venv` activated and run:
```powershell
python lab_network.py --role receiver --port 5004
```

* **What happens:**
  * Binds to TCP port `5004` and begins listening for incoming image fragments.
  * Launches the Receiver Web Dashboard in your browser (`http://localhost:8080/#receiver-screen`).
  * The **Fragment Buffer Matrix** will display on screen, waiting for incoming packets.

---

### Step 2: Start SYSTEM 2 (Intermediate Router)

On **System 2**, choose one of the following deployment options:

#### Option A: Single Intermediate Router (Simplest for 3 PCs)
Run:
```powershell
python lab_network.py --role intermediate --id 1 --port 5001
```
* **Interactive Prompts:**
  1. `Enter Receiver System IP`: Type **System 3's IP** (e.g. `192.168.1.103`).
  2. `Receiver Port`: Press **Enter** (defaults to `5004`).
* **What happens:**
  * Listens on port `5001`, decrements TTL, drops duplicate loops, and forwards packets to System 3.
  * Opens the **Packet Inspector & Wire-Level Hex Dump** dashboard.

#### Option B: Multi-Path Simulation (3 Virtual Routers on 1 PC)
If your instructor requires simulating 3 distinct routing paths (Nodes B, C, and D), open **3 separate PowerShell tabs** on System 2:
* **Tab 1 (Node B):** `python lab_network.py --role intermediate --id 1 --port 5001`
* **Tab 2 (Node C):** `python lab_network.py --role intermediate --id 2 --port 5002`
* **Tab 3 (Node D):** `python lab_network.py --role intermediate --id 3 --port 5003`

---

### Step 3: Start SYSTEM 1 (Sender / Master Coordinator)

On **System 1**, run:
```powershell
python lab_network.py --role sender
```

The interactive configuration wizard will prompt you:

| Prompt | What to Enter / Do |
| :--- | :--- |
| **Sender IP** | Press **Enter** (auto-detects System 1's local IP) |
| **Sender Port** | Press **Enter** (default: `5000`) |
| **Receiver IP** | Type **System 3's IP** (e.g. `192.168.1.103`) |
| **Receiver Port** | Press **Enter** (default: `5004`) |
| **How many intermediate systems?** | Type `1` (if using Option A) or `3` (if using Option B) |
| **Intermediate 1 IP** | Type **System 2's IP** (e.g. `192.168.1.102`), Port: `5001` |

#### Automated Link Test:
System 1 will automatically test socket connections to System 2 and System 3 before proceeding:
```text
============================================================================
              AUTOMATED SOCKET CONNECTION & LINK TEST REPORT
============================================================================
  Intermediate 1 (Node B) -> 192.168.1.102:5001   [ ONLINE - Socket Reachable ]
  Receiver System (Node E)-> 192.168.1.103:5004   [ ONLINE - Socket Reachable ]
============================================================================
  All endpoints successfully reachable! Transitioning to Web Dashboard...
```
System 1's browser will automatically open the Sender Web Dashboard at `http://localhost:8080`.

---

## Phase 3: Transmitting the Encrypted Image

Once all 3 nodes are online:

1. **On System 1 (Sender Dashboard):**
   * Drag & drop any image file (or click **"Use Lab Sample Image"**).
   * Observe the **Bit-Shuffle Cryptography visualizer**:
     $$\text{Invert Bits } (\sim b) \longrightarrow \text{Permute Bits } [5,2,7,0,4,1,6,3] \longrightarrow \text{Subtract } 42 \longrightarrow \text{XOR with Key}$$
   * Click **🚀 Start Flooding Dispatch**.

2. **On System 2 (Intermediate Router Dashboard):**
   * Watch incoming packets stream in real time.
   * Inspect the formatted **16-byte raw hex dump** and decoded header fields (`magic: IMGF`, `chunk_sequence`, `ttl`).
   * Notice TTL decrementing ($8 \to 7$) and duplicate packets being safely dropped.

3. **On System 3 (Receiver Dashboard):**
   * Watch the **Fragment Buffer Matrix** illuminate cells in emerald green as chunks arrive.
   * Once 100% of chunks arrive, Node E executes:
     $$\text{Reassemble Chunks } \longrightarrow \text{Reverse Bit-Shuffle Decryption} \longrightarrow \text{SHA-256 Checksum}$$
   * The reconstructed image renders with a green **`✔ 100% BYTE-EXACT MATCH`** badge.

---

## Alternative: Native Desktop GUI Mode (`gui.py`)

If you prefer a desktop application over web browser tabs:
On any system, activate `venv` and run:
```powershell
python gui.py
```
* Select your role from the dropdown (`Sender`, `Intermediate`, or `Receiver`).
* Click **🚀 1. Start Lab Network**.
* Use the **📁 Select Image** $\to$ **🔒 Bit-Shuffle Encrypt** $\to$ **⚡ Flood Multi-Path** buttons to run the entire flow directly in the desktop interface.

---

## Common Lab Troubleshooting & Gotchas

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| `ConnectionRefusedError` | Target node is not yet listening | Ensure **System 3 (Receiver)** is started first, then **System 2 (Intermediate)**, then **System 1 (Sender)**. |
| Connection probe shows `TIMEOUT` | Windows Firewall blocking incoming ports | On the listening PC, temporarily allow ports `5001`, `5004`, and `8080` through Windows Defender Firewall, or allow `python.exe`. |
| `ping` works but TCP fails | System on "Public" network profile with strict firewall rules | Change network profile to "Private" in Windows Settings, or run PowerShell as Administrator: `Set-NetConnectionProfile -NetworkCategory Private`. |
| Port already in use (`OSError: [Errno 98]`) | Previous simulation run left in background | Close previous PowerShell terminal windows, or run `Get-Process python \| Stop-Process -Force` in PowerShell. |
