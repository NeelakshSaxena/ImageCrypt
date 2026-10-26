

**Name:** Neelaksh Saxena  
**Registration No:** 24BCE2059  

### Question: Implement your own encryption algorithm over image file (Sender Node A)

Below is the step-by-step implementation for Sender Node (A) based on the provided network simulation flow, along with the corresponding code snippets.

#### 1. Loads an image file → Converts to byte array
The sender node reads the raw image file from the disk and loads it into a byte stream. 

**Code Snippet (`nodes/sender_a.py`):**
```python
    # Read the original image data from disk
    with open(image_path, 'rb') as f:
        original_data = f.read()
```

#### 2. Encrypts bytes
The raw image bytes are passed through a custom encryption function (`encrypt_bytes`) which performs bit manipulation, shuffling, subtraction, and an XOR operation to secure the data over the network.

**Code Snippet (`nodes/sender_a.py`):**
```python
    # Encrypt the raw image data to ensure privacy over the network
    encrypted_data = encrypt_bytes(original_data)
```

**Custom Encryption Algorithm (`common/crypto.py`):**
```python
def encrypt_bytes(data: bytes) -> bytes:
    """Encrypts data using our simple bit-manipulation algorithm."""
    encrypted = bytearray()
    
    for i, byte in enumerate(data):
        # Step 1: Flip the bits
        b = ~byte & 0xFF
        
        # Step 2: Change the order of bits
        shuffled_b = 0
        for bit_idx in range(8):
            if (b & (1 << bit_idx)) != 0:
                new_pos = BIT_SHUFFLE_KEY[bit_idx]
                shuffled_b |= (1 << new_pos)
        b = shuffled_b
        
        # Step 3: Subtract a number
        b = (b - MAGIC_NUMBER) % 256
        
        # Step 4: XOR with the shared key
        key_byte = AES_KEY[i % len(AES_KEY)]
        b = b ^ key_byte
        
        encrypted.append(b)
        
    return bytes(encrypted)
```

#### 3. Breaks encrypted bytes into 1024-byte fragments
The encrypted data is fragmented into smaller, manageable chunks (defined by `FRAGMENT_SIZE = 1024`) so they can be transmitted over the network via packets.

**Code Snippet (`nodes/sender_a.py`):**
```python
    # Fragment the encrypted data into manageable packet chunks
    fragments = fragment(encrypted_data, size=FRAGMENT_SIZE)
```

#### 4. Attaches custom header to each fragment
Each fragmented chunk payload gets encapsulated into a custom `Packet` object containing metadata fields like the Source ID, Destination ID, Packet ID, TTL, etc.

**Code Snippet (`nodes/sender_a.py`):**
```python
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
```

**Header Serialization logic (`common/packet.py`):**
```python
    def pack(self) -> bytes:
        """Serializes the Packet object into a byte stream for transmission."""
        header = struct.pack(
            HEADER_FORMAT,
            self.magic,
            self.src_id,
            self.dest_id,
            self.packet_id,
            self.chunk_sequence,
            self.total_chunks,
            self.ttl,
            len(self.payload)
        )
        return header + self.payload
```

#### 5. Floods packets to neighbors
Once packed, the chunks are flooded to Node A's immediate neighbors (B, C, and D) using TCP sockets.

**Code Snippet (`nodes/sender_a.py`):**
```python
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
```

---

### Detailed Explanation: The Encryption Algorithm Explained
The algorithm shown in the snippet is a custom symmetric cipher called **Bit-Shuffle**, designed specifically to operate on the raw bytes of the image data without relying on external cryptography libraries. 

It processes the data byte-by-byte in four distinct steps:
1. **Bit Flip (`b = ~byte & 0xFF`)**: It uses a bitwise NOT operator to invert every bit in the byte. Every `1` becomes a `0` and every `0` becomes a `1` (e.g., `10101010` becomes `01010101`).
2. **Bit Permutation (`shuffled_b |= (1 << new_pos)`)**: It takes the flipped bits and scrambles their positions based on a hardcoded assembly key (`BIT_SHUFFLE_KEY`). For example, the bit at index 0 might be moved to index 5, the bit at index 1 to index 2, etc.
3. **Subtraction (`(b - MAGIC_NUMBER) % 256`)**: A specific "magic number" (in this case, `42`) is subtracted from the byte's numerical value. The modulo `256` ensures that if the value drops below zero, it wraps around properly to stay within the 8-bit byte range.
4. **XOR with Shared Key (`b = b ^ key_byte`)**: Finally, the byte is XOR'ed against a byte from a shared configuration key (`AES_KEY`). This ties the encryption securely to a shared secret that both the sender and the receiver know.

---

### Detailed Explanation: Sender Node (A) Pipeline

According to the documentation (`docs/sender_node_master.md`), Node A acts as the starting point of the network simulation. Here is the full breakdown of its pipeline:

#### Loads an image file → Converts to byte array
* **What & How:** Node A reads the target image file from the disk into memory. It opens the file in `rb` (read-binary) mode, which converts the entire image file into a raw byte string.
* **Where:** This happens at the very beginning of the `run_sender()` function in `nodes/sender_a.py`.
* **When:** Executed first, before any network or security operations begin.

#### Encrypts bytes
* **What & How:** The raw byte string from the image is passed into the `encrypt_bytes()` function, which applies the custom Bit-Shuffle algorithm described above. 
* **Where:** Triggered in `nodes/sender_a.py`, but the actual encryption logic lives in `common/crypto.py`.
* **When:** Happens immediately after the image is loaded into memory, ensuring the data is secured before being chunked or hitting the network.

#### Breaks encrypted bytes into 1024-byte fragments
* **What & How:** Because the encrypted image is too large to send in a single packet, it is passed to a `fragment()` utility. This splits the massive byte array into smaller chunks of exactly 1024 bytes (as defined by `FRAGMENT_SIZE` in the project configuration).
* **Where:** Driven by `nodes/sender_a.py`, leveraging the utility from `common/fragment.py` and the config from `common/config.py`.
* **When:** Done after encryption, mirroring how real TCP/IP fragments large payloads for network transmission.

#### Attaches custom header to each fragment
* **What & How:** Each 1024-byte chunk is encapsulated inside a custom `Packet` object. This object prepends a 17-byte packed header to the chunk payload. The header contains routing and metadata information: Source ID, Destination ID, Packet ID, Chunk Sequence, Total Chunks, and Time-To-Live (TTL).
* **Where:** The packet instantiation happens in a loop inside `nodes/sender_a.py`. The actual serialization (`struct.pack`) happens inside the `Packet.pack()` method in `common/packet.py`.
* **When:** This happens inside the transmission loop, right before a specific fragment is about to be sent.

#### Floods packets to neighbors
* **What & How:** To guarantee delivery, Node A uses a "flooding" technique. Instead of choosing a single path, it loops through all of its immediate neighbors (Nodes B, C, and D), opens a fresh TCP connection to each, and transmits the packet containing the fragment. It repeats this process for *every single fragment*.
* **Where:** Handled by the socket connection loop at the end of `nodes/sender_a.py`.
* **When:** The final step of the pipeline. Once all fragments have been flooded to all neighbors, Node A's job is complete.