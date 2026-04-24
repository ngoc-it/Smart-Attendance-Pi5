import sys
import os
sys.path.append(os.getcwd())
from app.core import shared
import time

print("Checking shared memory...")
for i in range(5):
    with shared.frame_lock:
        if shared.last_frame is not None:
            print(f"[{i}] Frame found! Shape: {shared.last_frame.shape}")
        else:
            print(f"[{i}] No frame in shared memory.")
    time.sleep(1)
