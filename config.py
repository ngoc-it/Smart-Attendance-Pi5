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
    MATCH_THRESHOLD = 0.65
    
    # Chuoi GStreamer toi uu cho Pi 5 + Camera IMX708
    # Chuoi nay ep camera phai xuat ra dinh dang RGB de OpenCV hieu duoc
    GST_STR = "libcamerasrc ! videoconvert ! video/x-raw, width=640, height=480, format=BGR ! appsink drop=True"
    
    # Bao mat Session
    SECRET_KEY = "ngoc_smart_attendance_secret"