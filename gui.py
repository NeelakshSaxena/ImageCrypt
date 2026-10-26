"""
gui.py: This module provides a Tkinter-based Graphical User Interface (GUI)
for visualizing the Encrypted Image Flooding Network Simulation.
It allows the user to start/stop nodes, select an image to transmit, 
and observe the states (preview, encrypted intermediate, decrypted output).
"""
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import sys
import os
import time
import shutil
import math
from PIL import Image, ImageTk

# We can import crypto to generate the encrypted preview directly in GUI
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from common.crypto import encrypt_bytes

class SimulationGUI:
    """Main application class for the Simulation GUI."""
    def __init__(self, master):
        self.master = master
        master.title("Encrypted Image Flooding Network Simulation")
        master.geometry("1100x750")

        # Track subprocesses for the network nodes so we can terminate them
        self.processes = []
        self.python_exe = sys.executable
        self.selected_file_path = None

        # Layout top frame for buttons and controls
        self.top_frame = tk.Frame(master, pady=10)
        self.top_frame.pack(fill=tk.X)

        self.btn_start = tk.Button(self.top_frame, text="1. Start Network Nodes (B,C,D,E)", command=self.start_nodes, bg="#ccffcc", font=("Arial", 10, "bold"))
        self.btn_start.pack(side=tk.LEFT, padx=10)

        self.btn_stop = tk.Button(self.top_frame, text="Stop Network Nodes", command=self.stop_nodes, bg="#ffcccc", state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

        self.btn_select = tk.Button(self.top_frame, text="2. Select Image (Preview)", command=self.select_image, bg="#ffebcc", font=("Arial", 10, "bold"), state=tk.DISABLED)
        self.btn_select.pack(side=tk.LEFT, padx=10)

        self.btn_encrypt = tk.Button(self.top_frame, text="3. Encrypt Image", command=self.encrypt_image, bg="#e6ccff", font=("Arial", 10, "bold"), state=tk.DISABLED)
        self.btn_encrypt.pack(side=tk.LEFT, padx=10)

        self.btn_send = tk.Button(self.top_frame, text="4. Send Image (Node A)", command=self.send_image, bg="#cceeff", font=("Arial", 10, "bold"), state=tk.DISABLED)
        self.btn_send.pack(side=tk.LEFT, padx=10)

        # Images Frame (Side by side previews)
        self.img_frame = tk.Frame(master, pady=10)
        self.img_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Node A preview panel (shows original image)
        self.panel_a = tk.LabelFrame(self.img_frame, text="Node A (Input Preview)", width=330, height=330)
        self.panel_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.lbl_img_a = tk.Label(self.panel_a, text="No image selected")
        self.lbl_img_a.pack(expand=True)

        # Nodes B/C/D preview panel (shows what intermediate nodes see - random noise)
        self.panel_bcd = tk.LabelFrame(self.img_frame, text="Nodes B/C/D (Encrypted payload)", width=330, height=330)
        self.panel_bcd.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.lbl_img_bcd = tk.Label(self.panel_bcd, text="Waiting for transmission...")
        self.lbl_img_bcd.pack(expand=True)

        # Node E preview panel (shows the reconstructed output image)
        self.panel_e = tk.LabelFrame(self.img_frame, text="Node E (Decrypted Output)", width=330, height=330)
        self.panel_e.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.lbl_img_e = tk.Label(self.panel_e, text="Waiting for packets...")
        self.lbl_img_e.pack(expand=True)

        # Layout bottom frame for application logs
        self.log_frame = tk.LabelFrame(master, text="Simulation Logs", padx=10, pady=5)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(self.log_frame, height=10, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log("GUI Initialized. Click 'Start Network Nodes' to begin.")

    def log(self, message):
        """Helper to print logs to the GUI text area."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.master.update_idletasks()

    def start_nodes(self):
        """Spawns subprocesses for the intermediate routers (B,C,D) and receiver (E)."""
        nodes_dir = os.path.join(os.path.dirname(__file__), 'nodes')
        
        try:
            # Clear output image if exists from a previous run
            out_path = os.path.join(os.path.dirname(__file__), 'output', 'received_image.png')
            if os.path.exists(out_path):
                os.remove(out_path)
            self.lbl_img_e.config(image='', text="Waiting for packets...")
            self.lbl_img_bcd.config(image='', text="Waiting for transmission...")
            
            # Stream logs helper function
            def stream_output(process):
                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.log(line.strip())

            # Start Receiver E and Intermediate nodes B, C, D as independent processes, capturing their stdout
            pe = subprocess.Popen([self.python_exe, os.path.join(nodes_dir, 'receiver_e.py')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            pb = subprocess.Popen([self.python_exe, os.path.join(nodes_dir, 'intermediate_bcd.py'), '--id', '1'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            pc = subprocess.Popen([self.python_exe, os.path.join(nodes_dir, 'intermediate_bcd.py'), '--id', '2'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            pd = subprocess.Popen([self.python_exe, os.path.join(nodes_dir, 'intermediate_bcd.py'), '--id', '3'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            self.processes.extend([pe, pb, pc, pd])
            
            # Start background threads to stream their outputs to the GUI
            for p in self.processes:
                threading.Thread(target=stream_output, args=(p,), daemon=True).start()
            
            self.log("=> Started Receiver Node E on port 5004.")
            self.log("=> Started Intermediate Nodes B, C, D on ports 5001, 5002, 5003.")
            self.log("=> Network is ready to receive packets.")
            
            # Update button states
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.btn_select.config(state=tk.NORMAL)
            self.btn_encrypt.config(state=tk.DISABLED)
            self.btn_send.config(state=tk.DISABLED)
            
        except Exception as e:
            self.log(f"Error starting nodes: {e}")

    def stop_nodes(self):
        """Terminates all running subprocesses for the network nodes."""
        for p in self.processes:
            p.terminate()
        self.processes = []
        self.log("=> Stopped all network nodes.")
        # Re-enable the start button and disable others
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_select.config(state=tk.DISABLED)
        self.btn_encrypt.config(state=tk.DISABLED)
        self.btn_send.config(state=tk.DISABLED)

    def select_image(self):
        """Opens a file dialog to choose an image for transmission."""
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if not file_path:
            return
            
        self.selected_file_path = file_path
        self.log(f"Selected image: {file_path}")
        
        # Display the selected image in the Node A preview panel
        try:
            img = Image.open(file_path)
            img.thumbnail((300, 300))
            self.photo_a = ImageTk.PhotoImage(img)
            self.lbl_img_a.config(image=self.photo_a, text="")
            # Enable encryption now that an image is loaded
            self.btn_encrypt.config(state=tk.NORMAL)
            self.btn_send.config(state=tk.DISABLED)

        except Exception as e:
            self.log(f"Error loading preview: {e}")

    def encrypt_image(self):
        """Encrypts the selected image and generates the preview."""
        if not self.selected_file_path:
            return
            
        self.log("\n=> Starting Custom Bit-Shuffle Encryption...")
        self.log("  [Step 1] Reading raw image bytes...")
        self.log("  [Step 2] Flipping bits (~byte & 0xFF)...")
        self.log("  [Step 3] Shuffling bits using permutation key...")
        self.log("  [Step 4] Subtracting MAGIC_NUMBER (42) and XORing with AES_KEY...")
        
        # Trigger the visual preview generation
        self.generate_encrypted_preview()
        
        self.log("=> Encryption complete! Preview rendered as static noise in the middle panel.\n")
        
        # Enable sending now
        self.btn_send.config(state=tk.NORMAL)

    def generate_encrypted_preview(self):
        """Simulates what intermediate nodes see by rendering the encrypted bytes as a noise image."""
        try:
            with open(self.selected_file_path, 'rb') as f:
                data = f.read()
            # Encrypt the raw data
            encrypted = encrypt_bytes(data)
            
            # Create a square grayscale image from the encrypted bytes (visualizing the noise)
            side = int(math.ceil(math.sqrt(len(encrypted))))
            # Pad with random bytes to make a perfect square
            padded = encrypted + os.urandom(side*side - len(encrypted))
            img = Image.frombytes('L', (side, side), padded)
            # Resize exactly to 300x300 using nearest neighbor so the noise pixels are large and visible
            resample_filter = Image.Resampling.NEAREST if hasattr(Image, 'Resampling') else Image.NEAREST
            img = img.resize((300, 300), resample=resample_filter)
            
            # Display in the intermediate nodes panel
            self.photo_bcd = ImageTk.PhotoImage(img)
            self.lbl_img_bcd.config(image=self.photo_bcd, text="")
        except Exception as e:
            self.log(f"Error generating encrypted preview: {e}")

    def send_image(self):
        """Executes Node A to fragment and broadcast the image."""
        if not self.selected_file_path:
            return
            
        asset_path = os.path.join(os.path.dirname(__file__), 'assets', 'input_image.png')
        # Copy the selected image to the assets folder so sender_a.py can read it
        if os.path.abspath(self.selected_file_path) != os.path.abspath(asset_path):
            shutil.copy(self.selected_file_path, asset_path)
            
        # Clean up any previous output
        out_path = os.path.join(os.path.dirname(__file__), 'output', 'received_image.png')
        if os.path.exists(out_path):
            os.remove(out_path)
            
        self.lbl_img_e.config(image='', text="Receiving and decrypting...")

        
        self.log("=> Starting Node A (Sender)...")
        
        nodes_dir = os.path.join(os.path.dirname(__file__), 'nodes')
        
        def run_a():
            """Runs the sender process in a background thread to prevent UI freezing."""
            pa = subprocess.Popen([self.python_exe, os.path.join(nodes_dir, 'sender_a.py')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            # Stream the sender's stdout to the GUI logs
            for line in pa.stdout:
                self.log(line.strip())
            pa.wait()
            self.log("=> Node A finished transmitting.")
            # Once transmission finishes, start polling for the receiver's output
            self.check_for_output()
            
        threading.Thread(target=run_a, daemon=True).start()
        
    def check_for_output(self):
        """Polls the output directory waiting for Node E to reconstruct the image."""
        out_path = os.path.join(os.path.dirname(__file__), 'output', 'received_image.png')
        self.log("=> Waiting for Node E to reconstruct image...")
        for _ in range(15): # check for up to 7.5 seconds
            if os.path.exists(out_path):
                self.log("=> SUCCESS: Received image file constructed!")
                self.master.after(500, self.view_image) # call in main thread safely to update UI
                return
            time.sleep(0.5)
        self.log("=> Timeout: No image constructed. Check receiver logs.")
            
    def view_image(self):
        """Loads the reassembled output image into the Node E preview panel."""
        out_path = os.path.join(os.path.dirname(__file__), 'output', 'received_image.png')
        if not os.path.exists(out_path):
            return
            
        try:
            img = Image.open(out_path)
            img.thumbnail((300, 300)) 
            self.photo_e = ImageTk.PhotoImage(img)
            self.lbl_img_e.config(image=self.photo_e, text="")
        except Exception as e:
            self.log(f"Error loading received image: {e}")

    def on_closing(self):
        """Cleans up processes when the application window is closed."""
        self.stop_nodes()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    gui = SimulationGUI(root)
    # Ensure processes are killed if the window is closed with the 'X' button
    root.protocol("WM_DELETE_WINDOW", gui.on_closing)
    root.mainloop()
