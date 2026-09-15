import os

class Config:
    # Lay duong dan tuyet doi den thu muc goc cua du an
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Cau hinh Database
    DB_PATH = os.path.join(BASE_DIR, "data/database/attendance.db")
    
    # Cau hinh AI
    YOLO_MODEL_PATH = os.path.join(BASE_DIR, "models/yolov11n-face.pt")
    EMBEDDINGS_DIR = os.path.join(BASE_DIR, "data/embeddings")
    LOG_IMAGES_DIR = os.path.join(BASE_DIR, "data/log_images")
    FAILED_LOG_IMAGES_DIR = os.path.join(BASE_DIR, "data/failed_log_images")
    MATCH_THRESHOLD = 0.65
    
    # Cau hinh Firebase
    ENABLE_FIREBASE_SYNC = False  # Kich hoat dong bo Firebase 2 chieu Giua Raspi va Cloud
    FIREBASE_CREDENTIALS_PATH = os.path.join(BASE_DIR, "data/firebase/firebase-credentials.json")
    
    # Chuoi GStreamer toi uu cho Pi 5 + Camera IMX708
    # Khoi phuc chuoi mac dinh on dinh
    GST_STR = "libcamerasrc ! video/x-raw, width=640, height=480 ! videoconvert ! video/x-raw, format=BGR ! appsink drop=True"
    
    # Bao mat Session
    SECRET_KEY = "ngoc_smart_attendance_secret"
    
    # Mat khau mac dinh cho Giang vien moi khi Admin khong nhap
    DEFAULT_LECTURER_PASSWORD = "123456"
    
    # Session Management Upgrades
    from datetime import timedelta
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60) # Session expires after 60 minutes of inactivity
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True if using HTTPS in production