import os
import sys
import time
import hashlib
import subprocess
import pytest
from PIL import Image

def test_full_integration():
    # Remove existing output
    out_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'received_image.png')
    if os.path.exists(out_path):
        os.remove(out_path)
        
    python_exe = sys.executable
    nodes_dir = os.path.join(os.path.dirname(__file__), '..', 'nodes')
    
    # Launch E
    proc_e = subprocess.Popen([python_exe, os.path.join(nodes_dir, 'receiver_e.py')])
    
    # Launch B, C, D
    proc_b = subprocess.Popen([python_exe, os.path.join(nodes_dir, 'intermediate_bcd.py'), '--id', '1'])
    proc_c = subprocess.Popen([python_exe, os.path.join(nodes_dir, 'intermediate_bcd.py'), '--id', '2'])
    proc_d = subprocess.Popen([python_exe, os.path.join(nodes_dir, 'intermediate_bcd.py'), '--id', '3'])
    
    # Wait for listeners to be ready
    time.sleep(2) # Make sure all listeners are bound
    
    # Launch A
    proc_a = subprocess.Popen([python_exe, os.path.join(nodes_dir, 'sender_a.py')])
    
    # Wait for A to finish transmitting
    proc_a.wait(timeout=10)
    
    # Wait for E to process everything and write output.
    timeout = 10
    start_time = time.time()
    file_written = False
    while time.time() - start_time < timeout:
        if os.path.exists(out_path):
            file_written = True
            break
        time.sleep(0.5)
        
    # Terminate background processes
    for p in [proc_e, proc_b, proc_c, proc_d]:
        p.terminate()
        p.wait()
        
    assert file_written, "Output file was not written by Node E."
    
    # Verify contents
    in_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'input_image.png')
    with open(in_path, 'rb') as f:
        in_bytes = f.read()
    with open(out_path, 'rb') as f:
        out_bytes = f.read()
        
    assert hashlib.sha256(in_bytes).hexdigest() == hashlib.sha256(out_bytes).hexdigest()
    
    # Verify valid image
    try:
        img = Image.open(out_path)
        img.verify()
    except Exception as e:
        pytest.fail(f"Image validation failed: {e}")
