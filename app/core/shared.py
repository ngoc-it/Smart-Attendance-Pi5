import threading
last_frame = None
last_results = []
frame_lock = threading.Lock()

enroll_state = {
    "status": "idle", # idle, processing, success, error
    "progress": 0,
    "message": ""
}
enroll_lock = threading.Lock()