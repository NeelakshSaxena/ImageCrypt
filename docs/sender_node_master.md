# Master Document: Sender Node (Node A) & Encryption

This document serves as the master reference for the operations, pipeline, and encryption logic executed by **Node A (The Sender)** in the Encrypted Image Flooding Network simulation.

---

## 1. The Sender Pipeline

**Yes**, Node A strictly follows the exact pipeline you outlined. Here is the step-by-step breakdown of how that is implemented in `nodes/sender_a.py`:

1. **Loads an image file & Converts to byte array:** 
   The script locates `assets/input_image.png` and opens it in `rb` (read-binary) mode, pulling the entire image into memory as a raw byte string.
2. **Encrypts bytes:** 
   It passes this raw byte string to `encrypt_bytes()` (located in `common/crypto.py`), which applies the custom Bit-Shuffle encryption algorithm.
3. **Breaks encrypted bytes into 1024-byte fragments:** 
   It calls the `fragment()` utility function to split the massive ciphertext byte array into manageable chunks. (The `FRAGMENT_SIZE` is defined as `1024` in `common/config.py`).
4. **Attaches custom header to each fragment:** 
   For every chunk, it instantiates a `Packet` object. This object automatically prepends a 17-byte `struct`-packed header containing routing info (src, dest, packet_id, sequence, TTL).
5. **Floods packets to neighbors:** 
   Instead of choosing one path, Node A loops through its neighbors (Nodes B, C, and D), opens a fresh TCP connection to each, and transmits the packet. It does this for *every single fragment*, executing a true network flood.

---

## 2. The Custom Encryption (Bit-Shuffle)

Because the project strictly prohibits industry-standard algorithms (like AES, DES, RSA), the data is encrypted using a custom, byte-level symmetric cipher called **Bit-Shuffle**. 

It operates natively on the raw bytes of the image, processing them one by one.

### The Encryption Steps
For each byte of the image, the following 4 operations are applied in order:

1. **Bit Flip (Inversion):** 
   Using the bitwise NOT operator `~`, every `1` becomes a `0`, and every `0` becomes a `1`. 
   *(e.g., `10101010` → `01010101`)*
2. **Bit Permutation (The Shuffle):** 
   The bits within the byte are physically rearranged based on a static assembly key: `[5, 2, 7, 0, 4, 1, 6, 3]`. This means the bit originally sitting at index 0 is moved to index 5, the bit at index 1 moves to 2, etc.
3. **Subtraction (Magic Number):** 
   A magic number (`42`) is subtracted from the byte's numerical value. Because it is modulo 256 arithmetic, if the value drops below 0, it wraps around to the top of the byte range.
4. **XOR with Shared Key:** 
   Finally, the byte is XOR'ed (`^`) against a byte from the shared configuration key (`AES_KEY`). This ensures the encryption is tied to the project's secret configuration.

### The Decryption Steps (Executed at Node E)
When Node E finally rebuilds the chunks, it runs `decrypt_bytes()`, which reverses the exact flow above:
1. **Reverse XOR:** XOR with the shared configuration key again.
2. **Reverse Subtraction:** Add the magic number (`42`) back to the byte.
3. **Reverse Permutation:** Read the shuffled bits and place them back into their original indices.
4. **Reverse Bit Flip:** Apply the bitwise NOT operator `~` one last time to reveal the raw, original image byte.

---

## 3. Why This Design?

- **Why fragment?** A typical image is far too large to send across a network in a single packet. Fragmenting mimics real Transmission Control Protocol / Internet Protocol (TCP/IP) behavior.
- **Why custom encryption?** To demonstrate a fundamental understanding of bitwise cryptography (substitution, permutation, and XOR operations) without leaning on pre-built `Crypto` libraries.
- **Why flooding?** Flooding guarantees that as long as at least *one* path to Node E exists, the packet will arrive. It creates purposeful network redundancy (which Node E must handle by dropping duplicates).
