# Reviewer Q&A Prep: Encrypted Image Flooding Network

This document compiles a list of anticipated questions that a technical reviewer, professor, or peer might ask during a code review or project defense. It covers architecture, networking, security, and edge cases.

## 1. Architecture & General Design

**Q: Why did you use individual TCP connections per packet instead of UDP?**
*Expected Answer:* While UDP is traditionally used for flooding, we opted for TCP to ensure reliable transmission between node hops in this simulation. By establishing and immediately closing a new TCP connection for each packet, we avoid complex stream-framing logic while maintaining the packet-based feel of the datagram architecture.

**Q: How does the network prevent infinite loops during flooding?**
*Expected Answer:* We use two mechanisms:
1. **Time-To-Live (TTL):** Every packet starts with a default TTL. Each intermediate node decrements the TTL before forwarding it. If TTL reaches 0, the packet is dropped.
2. **Duplicate Detection:** Each node maintains a `seen_packets` set. If a node receives a packet with an ID it has already processed, it drops the packet instead of forwarding it.

**Q: Why are you using Python's `struct` module for packet headers instead of JSON?**
*Expected Answer:* Network bandwidth is limited. `struct` allows us to pack the packet header into a compact, fixed-size byte array (binary format) just like real network protocols (e.g., IPv4 headers). JSON is text-based, much larger in size, and slower to serialize/deserialize, which is inefficient for high-frequency packet transmission.

## 2. Networking & Reliability

**Q: What happens if a packet is lost in transit?**
*Expected Answer:* Because we use UDP without an explicit Automatic Repeat reQuest (ARQ) or acknowledgment mechanism, a lost packet means the receiver will never get that specific chunk. If the total received chunks do not match the expected `total_chunks`, the receiver will fail to reconstruct the image.

**Q: Can your receiver handle fragments arriving out of order?**
*Expected Answer:* Yes. The `Packet` header includes a `chunk_sequence` ID. The receiver stores incoming chunks in a dictionary keyed by this sequence ID. When reassembling, it iterates sequentially from `0` to `total_chunks - 1`, ensuring the payload is stitched back together in the exact original order.

**Q: How does the network handle large images?**
*Expected Answer:* Large images are fragmented into smaller chunks defined by `FRAGMENT_SIZE` (e.g., 1024 bytes) before transmission. However, if the image is extremely large, the `seen_packets` set in each node will grow significantly, potentially causing memory bloat.

## 3. Cryptography & Security

**Q: Why did you build a custom Bit-Shuffle encryption algorithm?**
*Expected Answer:* To strictly comply with the assignment constraint against using industry-standard algorithms (like AES, DES, or RSA). This custom algorithm demonstrates byte-level bit manipulation, permutation, and XOR operations in a simple, straightforward implementation.

**Q: How is the AES key managed?**
*Expected Answer:* Currently, the key (`AES_KEY`) is hardcoded in `config.py` as a shared symmetric key across all nodes. In a production environment, this is insecure. We would need a secure key exchange mechanism, such as Diffie-Hellman or RSA-based public key cryptography, to safely distribute the symmetric key.

**Q: What happens if an intermediate node maliciously alters the packet header?**
*Expected Answer:* The current implementation is vulnerable to header manipulation. While there is a `magic` byte (`IMGF`) for a basic sanity check, there is no cryptographic integrity check (like an HMAC or digital signature) over the packet header. An attacker could easily change the `dest_id` or `ttl` without detection.

**Q: Are replay attacks possible in this network?**
*Expected Answer:* The `seen_packets` set mitigates short-term replay attacks because nodes will drop packets with IDs they've already processed. However, because this set is held in volatile memory and resets when a node restarts, a delayed replay attack across restarts could potentially succeed. Incorporating a timestamp or cryptographic nonce would provide stronger defense.

## 4. Edge Cases & Implementation Details

**Q: What happens if an intermediate node (e.g., Node C) crashes during transmission?**
*Expected Answer:* Because the network uses a flooding topology, Node B and Node D will still forward the packets to Node E. As long as there is at least one active path from Sender A to Receiver E, the image will still be successfully transmitted.

**Q: Why is there a `magic` byte in the packet header?**
*Expected Answer:* The `magic` byte acts as a protocol identifier. If a random application accidentally opens a TCP connection to our node's port and sends junk data, the node can instantly reject the packet because the first 4 bytes won't match `b"IMGF"`.

**Q: Why does `process_packet` catch generic exceptions during unpacking?**
*Expected Answer:* If a packet arrives corrupted (e.g., truncated data smaller than the expected header size, or malformed bytes), `struct.unpack` will raise an error. Catching the exception ensures the node simply drops the bad packet and continues listening, preventing a single corrupted packet from crashing the entire router node.
