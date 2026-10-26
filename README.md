# Encrypted Image Flooding-Network Simulation

This project simulates a secure, flooding-based network utilizing a topology of 5 logical nodes (running over localhost TCP sockets).

- **Node A (Sender):** Loads an image, encrypts it (Custom Bit-Shuffle Algorithm), fragments it into 1024-byte payloads, builds `struct` packed headers, and floods all packets to Nodes B, C, and D.
- **Nodes B, C, D (Intermediate):** Receive the flooded packets, execute de-duplication based on tracking the `packet_id`, decrement the Time-To-Live (TTL), and forward valid, non-duplicate packets to Node E.
- **Node E (Receiver):** Receives packets from multiple routes (causing duplicates which it actively drops), buffers them based on their sequence index, and finally reassembles and decrypts the completed file into `output/received_image.png`.

## Quick Start (GUI Mode) - Highly Recommended

We've provided a simple graphical interface to easily control and observe the simulation without managing 5 different terminal windows.

1. **Activate the Environment:**
   Open a terminal and ensure dependencies are installed via the virtual environment.
   ```bash
   # On Windows
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   
   # On Linux / Mac
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Launch the GUI:**
   ```bash
   python gui.py
   ```
   *(If you are not using the activated terminal, run `.\venv\Scripts\python.exe gui.py` directly).*

3. **Running the Simulation via GUI:**
   - **Step 1:** Click **"1. Start Network Nodes (B,C,D,E)"**. This quietly boots the intermediate routers and receiver in the background.
   - **Step 2:** Click **"2. Select Image (Preview)"**. A file dialog will open. Pick any image and it will appear in the Node A preview panel.
   - **Step 3:** Click **"3. Send Image (Node A)"** to encrypt and fragment the image over the network.
   - **Step 4:** The GUI will visualize the encrypted payload (as noise) that intermediate nodes handle, and finally reconstruct the decrypted image at Node E!

## Running Manually (CLI Mode)

If you prefer to run it manually to see the raw logs of each node individually, open **four separate terminals**. (Ensure the `venv` is activated in each).

1. **Start Receiver Node E:**
   ```bash
   python nodes/receiver_e.py
   ```

2. **Start Intermediate Nodes B, C, D:**
   ```bash
   python nodes/intermediate_bcd.py --id 1
   python nodes/intermediate_bcd.py --id 2
   python nodes/intermediate_bcd.py --id 3
   ```

3. **Start Sender Node A (Triggers the flood):**
   ```bash
   python nodes/sender_a.py
   ```

You will see the network traffic dynamically populate the `logs/` directory and terminal outputs. The final image will be written to `output/received_image.png`.

## Automated Test Suite
To automatically boot all 5 nodes concurrently and test the end-to-end integration (including dropped duplicates verification and SHA256 checksum tests):
```bash
pytest tests/test_integration.py -v -s
```
