import cv2
import threading
import time
import numpy as np
import os
from config import Config
from app.core import shared

def video_worker():
    """Luồng xử lý camera sử dụng GStreamer (libcamerasrc) - Tối ưu và ổn định cho Pi 5"""
    retry_count = 0
    
    # Lấy chuỗi GStreamer từ config, nếu không có dùng mặc định cho IMX708
    gst_str = getattr(Config, 'GST_STR', 
        "libcamerasrc ! video/x-raw, width=640, height=480 ! videoconvert ! video/x-raw, format=BGR ! appsink drop=True"
    )
    
    # Đảm bảo thư mục logs tồn tại
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    def log_debug(msg):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open("logs/camera_debug.log", "a") as f:
            f.write(f"[{timestamp}] {msg}\n")
        print(f"Camera Debug: {msg}")

    log_debug(f"Starting Video Worker with GStreamer Pipeline: {gst_str}")
    time.sleep(2) 
    
    while True:
        cap = None
        try:
            log_debug(f"Attempting to open camera (Trial {retry_count + 1})...")
            
            # Giải phóng các tiến trình cũ có thể đang chiếm giữ camera
            # Đặc biệt là Pipewire/Wireplumber thường gây lỗi 'Device or resource busy' trên Pi 5
            os.system("pkill -9 pipewire")
            os.system("pkill -9 wireplumber")
            os.system("pkill -9 rpicam")
            os.system("pkill -9 libcamera")
            time.sleep(1.5)

            # Khởi tạo VideoCapture với backend GSTREAMER
            cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)
            
            if not cap.isOpened():
                log_debug("Failed to open GStreamer pipeline. Checking if camera is busy or disconnected.")
                # Thử phương án dự phòng đơn giản hơn
                gst_backup = "libcamerasrc ! videoconvert ! video/x-raw, format=BGR ! appsink drop=True"
                log_debug(f"Trying backup pipeline: {gst_backup}")
                cap = cv2.VideoCapture(gst_backup, cv2.CAP_GSTREAMER)

            if not cap.isOpened():
                raise Exception("Could not open any GStreamer pipeline.")

            log_debug("Camera opened successfully. Streaming frames...")
            
            consecutive_failures = 0
            first_frame = True
            
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    consecutive_failures += 1
                    if consecutive_failures > 50: 
                        log_debug("Loss of signal from camera. Restarting pipeline...")
                        break
                    time.sleep(0.01)
                    continue
                
                consecutive_failures = 0
                if first_frame:
                    log_debug("First frame received! System is stable.")
                    first_frame = False
                    retry_count = 0
                
                # Cập nhật frame vào shared memory
                with shared.frame_lock:
                    shared.last_frame = frame
                
                time.sleep(0.01)

        except Exception as e:
            log_debug(f"Critical error in video_worker: {e}")
            
        finally:
            if cap is not None:
                cap.release()
            log_debug("Camera resource released. Waiting 3 seconds before retry...")
            
        retry_count += 1
        time.sleep(3)

def ai_worker():
    from app import ai_engine 
    print("AI: Luong nhan dien da kich hoat.")
    while True:
        temp_frame = None
        # ĐỌC TỪ BIẾN SHARED
        with shared.frame_lock:
            if shared.last_frame is not None:
                temp_frame = shared.last_frame.copy()
        
        if temp_frame is not None:
            try:
                # GHI KẾT QUẢ VÀO SHARED
                shared.last_results = ai_engine.recognize(temp_frame)
            except Exception as e:
                print(f"AI Error: {e}")
        time.sleep(0.1)