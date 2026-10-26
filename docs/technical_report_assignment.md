# Technical Report & Assignment: Innovative Practice

**Course:** Computer Networks Lab | **Name:** Neelaksh Saxena | **Reg. No:** 24BCE2059  
**Topic:** Multi-Path Encrypted Image Flooding Network Simulation  

---

### 1. Understanding of Problem Statement *(1 Mark)*
* **Objective:** Simulate a packet-switched network securely transmitting an image over a 5-node flooding topology ($A \to B, C, D \to E$) using raw TCP sockets on `localhost`.
* **Sender (Node A):** Reads image $\to$ encrypts bytes using a custom cipher $\to$ fragments into 1024B MTU chunks $\to$ attaches 17B custom binary header $\to$ floods to B, C, and D.
* **Routers ($B, C, D$):** Zero-knowledge intermediate relays. Parse headers, drop duplicates via `packet_id`, decrement TTL (drop if 0), and forward to Node E without decrypting.
* **Receiver (Node E):** Sinks packets, drops duplicates, buffers by `chunk_sequence`, reassembles chunks, decrypts payload, and verifies image via SHA-256.

---

### 2. Concepts Behind the Questions *(1 Mark)*
1. **Flooding Routing:** Broadcast mechanism replicating packets across all outgoing links for fault tolerance and delivery assurance.
2. **Packet Switching & MTU:** Breaking large data into 1024-byte chunks with sequence numbers for out-of-order reassembly.
3. **Binary Header Encapsulation:** Packing 17-byte metadata in Network Byte Order (`!4sBBIHHBH`) to eliminate JSON overhead.
4. **Loop Mitigation:** Combining Time-To-Live (TTL) hop limits and a `seen_packets` set to stop broadcast storms.
5. **Custom Symmetric Cipher:** SPN cipher combining bit-flip (NOT), P-box permutation, modulo-256 subtraction, and key XOR.

---

### 3. Flow Diagram and Pseudo Code *(1 Mark)*

#### Flow Diagram
```
[Node A: Sender] -> (Encrypt -> Slice 1024B -> Attach 17B Header)
       |------------------------+------------------------|
       v (Port 5001)            v (Port 5002)            v (Port 5003)
  [Node B: Router]         [Node C: Router]         [Node D: Router]
  (Drop Dup/TTL=0 -> Relay)(Drop Dup/TTL=0 -> Relay)(Drop Dup/TTL=0 -> Relay)
       |------------------------+------------------------|
                                v (Port 5004)
                    [Node E: Receiver]
  (Dedup -> Buffer by Seq -> Reassemble -> Decrypt -> Save Image)
```

#### Compact Pseudo Code
```pascal
// Custom Cipher:
Encrypt(b, k) = ((Permute(~b & 0xFF, KEY=[5,2,7,0,4,1,6,3]) - 42) % 256) ^ k
Decrypt(c, k) = ~InvPermute(((c ^ k) + 42) % 256, KEY) & 0xFF

// Node A (Sender):
FOR seq, chunk IN Slice(Encrypt(Read("img.png")), 1024):
    pkt = Pack("!4sBBIHHBH", "IMGF", 0, 4, GenID(), seq, total, TTL=8, LEN(chunk)) + chunk
    FOR port IN [5001, 5002, 5003]: SendTCP(port, pkt)

// Nodes B, C, D (Routers):
ON Receive(pkt):
    hdr, data = Unpack(pkt)
    IF hdr.id IN seen OR --hdr.ttl <= 0: DROP
    seen.ADD(hdr.id)
    SendTCP(5004, Pack(hdr) + data)

// Node E (Receiver):
ON Receive(pkt):
    hdr, data = Unpack(pkt)
    IF hdr.id NOT IN seen:
        seen.ADD(hdr.id); buf[hdr.seq] = data
        IF LEN(buf) == hdr.total: Write("out.png", Decrypt(Stitch(buf)))
```

---

### 4. Libraries and Modules Used *(1 Mark)*

* **`socket`:** TCP IPC over localhost (`AF_INET`, `SOCK_STREAM`, `bind`, `listen`, `connect`, `sendall`, `recv`). *(C: `<sys/socket.h>`)*
* **`struct`:** Packed 17-byte binary header with format `!4sBBIHHBH` (Big-Endian). *(C: `__attribute__((__packed__)) struct`)*
* **`dataclasses` (`@dataclass`):** Strongly-typed `Packet` structure.
* **`PIL` & `tkinter`:** Image verification and 3-panel simulation GUI dashboard.
* **`logging` & `subprocess`:** Hop-by-hop event logging and asynchronous node process management.
* **`hashlib`:** Verification via `SHA-256(Input) == SHA-256(Output)`.

---

### 5. Module Explanation & ISO/OSI Layer Mapping *(1 Mark)*

* **Modules:** `config.py` (ports 5000–5004, TTL=8), `packet.py` (17B header), `crypto.py` (cipher), `fragment.py` (MTU slicer), `sender_a.py` (Sender), `intermediate_bcd.py` (Routers), `receiver_e.py` (Receiver), `gui.py` (GUI).
* **OSI Layer Mapping:**
  * **Layer 7 (Application):** Image file I/O, Tkinter GUI.
  * **Layer 6 (Presentation):** Bit-Shuffle encryption/decryption, `struct` binary serialization.
  * **Layer 5 (Session):** Socket connection establishment and teardown per packet.
  * **Layer 4 (Transport):** TCP stream transfer, ports (5000–5004), sequence reassembly.
  * **Layer 3 (Network):** Custom 17B header (`src_id`, `dest_id`), Flooding routing, TTL loop drop.
  * **Layer 2 (Data Link):** Packet framing, 1024-byte MTU payload fragmentation.
  * **Layer 1 (Physical):** Localhost loopback interface (`127.0.0.1`) bit transmission.

---

### 6. Issues Faced, Debugging & Logical Errors *(1 Mark)*

1. **TCP Stream Boundary Coalescing:** Consecutive packets merged in stream buffers.  
   *Fix:* Added `payload_length` to header; read exactly 17 header bytes first, then payload.
2. **Socket Race Condition:** Node A connected before intermediate nodes finished `bind()`.  
   *Fix:* Added `SO_REUSEADDR` and connection retry backoff in Node A.
3. **Python Negative Bitwise NOT:** `~byte` produced negative two's complement numbers.  
   *Fix:* Applied 8-bit masks: `b = ~byte & 0xFF` and `(b - 42) % 256`.
4. **Inverse Permutation Bug:** Decryption scrambled bytes by using forward shuffle positions.  
   *Fix:* Inverted lookup: mapped shuffled bit positions back to original indices.

---

### 7. AI / Agentic AI Tools Used & Autonomy Level *(1 Mark)*

* **Tool:** **Claude Code / Antigravity IDE**
* **Autonomy Level:** **Level 3 Agentic AI (Collaborative Autonomous Tool-Using Agent)** on the 0–5 scale:
  * *L0:* Static tools/compilers.
  * *L1:* Conversational autocomplete (Copilot).
  * *L2:* Single-script generation.
  * *L3 (Used):* Multi-file contextual reasoning, autonomous terminal execution (`pytest`), and error diagnosis.
  * *L4/L5:* Fully autonomous self-directed engineer without human oversight.
* **Role:** Handled boilerplate scaffolding, automated test runs, and socket race debugging, while the student defined the architecture, cipher math, and verification.

---

### 8. Options to Expand for Core Networking Projects *(1 Mark)*

1. **Dynamic Routing (OSPF/RIP):** Replace flooding with Dijkstra's SPF or Bellman-Ford using dynamic link-cost tables.
2. **Sliding Window ARQ (UDP):** Switch to raw UDP with Selective Repeat ARQ (ACK/NACK, flow control, AIMD).
3. **Security Hardening:** Implement Ephemeral Diffie-Hellman (ECDH) key exchange and HMAC-SHA256 header signatures.
4. **Network Virtualization:** Deploy nodes in Mininet/Docker containers with real delay, jitter, and packet drop rates.
5. **Erasure Coding:** Use Reed-Solomon coding to recover dropped packets without retransmission.

---

### 9. Academic Integrity and Non-AI Declaration *(2 Marks)*

> **Declaration:**  
> I declare that this assignment report reflects my independent work and conceptual understanding of computer networking principles, socket programming, custom cryptographic design, and the ISO/OSI model. The write-up and diagrams are prepared for handwritten submission.  
>  
> **Signature:** Neelaksh Saxena &nbsp;|&nbsp; **Reg. No:** 24BCE2059 &nbsp;|&nbsp; **Date:** 25th October 2026
