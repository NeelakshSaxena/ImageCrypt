# Project Explanation: Encrypted Image Flooding Network

## 1. Introduction
This project simulates a secure, packet-switched network that transmits an image using a "flooding" routing algorithm. Instead of finding a single optimal path from a sender to a receiver, the network blasts the data across all available connections. The project demonstrates core computer networking concepts including fragmentation, TCP connection transmission, packet deduplication, Time-To-Live (TTL) limits, and payload encryption.

## 2. Network Topology
The simulated network consists of 5 logical nodes running on local TCP ports:
* **Node A (Sender):** The origin point. It takes an input image, processes it, and transmits it to its direct neighbors (B, C, and D).
* **Nodes B, C, D (Intermediate Routers):** The backbone of the network. They receive packets from Node A and forward them to Node E. Because they act purely as routers, they cannot read the encrypted contents of the packets.
* **Node E (Receiver):** The destination. It listens for incoming packets from B, C, and D, reassembles them, decrypts the payload, and outputs the final image.

## 3. Data Processing Flow (Node A)
When an image is sent, Node A performs the following operations:
1. **Byte Conversion:** The image file is read as raw binary data.
2. **Encryption:** The data is encrypted using a Custom Bit-Shuffle Algorithm. It flips bits, shuffles them according to a static permutation key, subtracts a magic number, and XORs the result with the shared config key.
3. **Fragmentation:** Because the encrypted image is typically larger than a standard network packet, it is chopped up into smaller chunks (exactly 1024 bytes each).
4. **Header Encapsulation:** A 17-byte custom header is attached to the front of every chunk.

## 4. The Packet Header
To ensure the receiver knows how to handle the incoming fragments, the 17-byte header contains strict routing instructions (packed using Python's `struct` in network-byte order):
* `magic` (4 bytes): A sanity check (`b"IMGF"`) to ensure the packet is valid.
* `src_id` (1 byte) & `dest_id` (1 byte): Identifies Node A as sender and Node E as receiver.
* `packet_id` (4 bytes): A unique identifier for the specific chunk. Used by routers to detect duplicates.
* `chunk_sequence` (2 bytes) & `total_chunks` (2 bytes): Tells Node E exactly where this piece fits into the puzzle.
* `ttl` (1 byte): Time-To-Live. Decrements at every hop to prevent infinite network loops.
* `payload_length` (2 bytes): Specifies exactly how large the encrypted chunk is.

## 5. Routing Logic (Flooding & Deduplication)
When Node A transmits a chunk, it sends a copy to Node B, Node C, and Node D simultaneously. 

When an intermediate node (B, C, or D) receives the packet:
1. It reads the header and checks the `packet_id`. 
2. It looks at its internal "seen" memory. If it has processed this ID before, it drops the packet to prevent network congestion.
3. It subtracts 1 from the `ttl`. If `ttl` reaches 0, the packet is killed.
4. If the packet is fresh and alive, it forwards it to Node E.

## 6. Reassembly (Node E)
Because of the flooding algorithm, Node E will receive **three copies** of every single chunk (one from B, one from C, and one from D).
1. **Deduplication:** Node E actively monitors the incoming `packet_id`s and instantly drops the duplicate arrivals.
2. **Buffering:** Network packets do not always arrive in order. Node E stores each chunk in memory based on its `chunk_sequence` number.
3. **Reconstruction:** Once Node E detects that it has received all chunks (e.g., 6 out of 6), it stitches the binary payloads back together in the correct sequence.
4. **Decryption:** The stitched binary is decrypted using the custom inverse Bit-Shuffle operations, revealing the original image file which is then saved to the disk.

## 7. The Graphical User Interface (GUI)
The included `gui.py` provides a 3-panel visualizer for this entire flow:
* **Panel 1 (Node A Preview):** Shows the image you are about to send.
* **Panel 2 (Intermediate Network):** Shows exactly what Nodes B, C, and D see. Because the data is heavily encrypted and split up, it visually renders as unreadable "static noise", proving the transmission is secure.
* **Panel 3 (Node E):** Shows the final, successfully reconstructed image after the network routing and decryption phases are complete.
