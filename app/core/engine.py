import cv2
import numpy as np
import os
import time
from ultralytics import YOLO
from insightface.app import FaceAnalysis
from config import Config
from app.core import shared

class FaceEngine:
    def __init__(self, db):
        self.db = db
        self.detector = YOLO(Config.YOLO_MODEL_PATH)
    
    # CHỈ nạp module detection và recognition để tiết kiệm 60% RAM
        self.app = FaceAnalysis(
            name='buffalo_l', 
            allowed_modules=['detection', 'recognition'], 
            providers=['CPUExecutionProvider']
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))
    
        self.known_embeddings = {}
        self.threshold = float(self.db.get_setting("match_threshold", Config.MATCH_THRESHOLD))
        self.load_database()    

    def refresh_settings(self):
        """Cap nhat lai cac cau hinh tu Database"""
        self.threshold = float(self.db.get_setting("match_threshold", Config.MATCH_THRESHOLD))

    def load_database(self):
        """Nap tat ca vector mau tu thu muc data/embeddings vao RAM"""
        if not os.path.exists(Config.EMBEDDINGS_DIR):
            os.makedirs(Config.EMBEDDINGS_DIR)
        
        self.known_embeddings = {}
        for file in os.listdir(Config.EMBEDDINGS_DIR):
            if file.endswith(".npy"):
                student_id = file.replace(".npy", "")
                try:
                    self.known_embeddings[student_id] = np.load(os.path.join(Config.EMBEDDINGS_DIR, file))
                except Exception as e:
                    print(f"Loi khi tai embedding {file}: {e}")

    def recognize(self, frame):
        """Nhan dien khuon mat tren mot khung hinh"""
        # Su dung InsightFace truc tiep de lay ca Box va Embedding
        faces = self.app.get(frame)
        output = []
        
        for face in faces:
            # Trich xuat toa do va embedding da chuan hoa
            x1, y1, x2, y2 = face.bbox.astype(int)
            emb = face.normed_embedding
            
            best_id = "Unknown"
            max_sim = -1.0
            
            # So sanh Cosine Similarity (Dot Product) voi database
            for student_id, known_emb in self.known_embeddings.items():
                sim = np.dot(emb, known_emb)
                if sim > max_sim:
                    max_sim = sim
                    best_id = student_id
            
            # Phan loai dua tren nguong (Threshold) tu cau hinh
            if max_sim > self.threshold:
                output.append({
                    "id": best_id,
                    "box": (x1, y1, x2, y2),
                    "confidence": float(max_sim)
                })
            else:
                output.append({
                    "id": "Unknown",
                    "box": (x1, y1, x2, y2),
                    "confidence": float(max_sim)
                })
        return output

    def enroll_session_worker(self, student_id):
        """Worker background để lấy 30 ảnh và chống trùng khuôn mặt"""
        
        # Đồng bộ hóa RAM với ổ cứng trước khi bắt đầu (đề phòng xóa file thủ công)
        self.load_database()
        
        with shared.enroll_lock:
            shared.enroll_state["status"] = "processing"
            shared.enroll_state["progress"] = 0
            shared.enroll_state["message"] = "Bắt đầu thu thập khuôn mặt..."
        
        valid_embeddings = []
        max_images = 30
        timeout_seconds = 30
        start_time = time.time()
        
        while len(valid_embeddings) < max_images:
            if time.time() - start_time > timeout_seconds:
                with shared.enroll_lock:
                    shared.enroll_state["status"] = "error"
                    shared.enroll_state["message"] = "Hết thời gian (Timeout). Không tìm thấy đủ khuôn mặt."
                return
            
            # Đọc frame mới nhất
            frame = None
            with shared.frame_lock:
                if shared.last_frame is not None:
                    frame = shared.last_frame.copy()
            
            if frame is None:
                time.sleep(0.1)
                continue
            
            # Detect
            faces = self.app.get(frame)
            if len(faces) == 0:
                with shared.enroll_lock:
                    shared.enroll_state["message"] = "Không tìm thấy khuôn mặt..."
                time.sleep(0.1)
                continue
            
            if len(faces) > 1:
                with shared.enroll_lock:
                    shared.enroll_state["message"] = "Có quá nhiều người trong khung hình!"
                time.sleep(0.1)
                continue
                
            emb = faces[0].normed_embedding
            
            # Ở frame hợp lệ đầu tiên, kiểm tra xem mặt này đã được đăng ký chưa
            if len(valid_embeddings) == 0:
                is_duplicate = False
                for known_id, known_emb in self.known_embeddings.items():
                    sim = np.dot(emb, known_emb)
                    if sim > self.threshold:
                        is_duplicate = True
                        break
                
                if is_duplicate:
                    with shared.enroll_lock:
                        shared.enroll_state["status"] = "error"
                        shared.enroll_state["message"] = "Lỗi: Khuôn mặt này đã được đăng ký cho sinh viên khác!"
                    return
            
            # Thêm vào mảng và cập nhật tiến độ
            valid_embeddings.append(emb)
            with shared.enroll_lock:
                shared.enroll_state["progress"] = len(valid_embeddings)
                shared.enroll_state["message"] = f"Đang chụp: {len(valid_embeddings)}/30"
                
            time.sleep(0.05) # Delay ngắn để tránh lấy các frame quá giống nhau
            
        # Xử lý sau khi đủ 30 ảnh
        try:
            mean_emb = np.mean(valid_embeddings, axis=0)
            # Chuẩn hóa lại vector sau khi tính trung bình (L2 normalization)
            mean_emb = mean_emb / np.linalg.norm(mean_emb)
            
            save_path = os.path.join(Config.EMBEDDINGS_DIR, f"{student_id}.npy")
            np.save(save_path, mean_emb)
            
            self.load_database() # Load lại vào RAM
            
            with shared.enroll_lock:
                shared.enroll_state["status"] = "success"
                shared.enroll_state["message"] = f"Đã đăng ký thành công MSSV: {student_id}"
        except Exception as e:
            with shared.enroll_lock:
                shared.enroll_state["status"] = "error"
                shared.enroll_state["message"] = f"Lỗi hệ thống: {str(e)}"

    def verify_attendance(self, frame):
        """Dùng cho màn hình cảm ứng: Kiểm tra duy nhất 1 khuôn mặt và trả về ID nếu nhận diện thành công"""
        faces = self.app.get(frame)
        
        if len(faces) == 0:
            return False, "Không tìm thấy khuôn mặt nào!", None
            
        if len(faces) > 1:
            return False, "Phát hiện nhiều người! Chỉ 1 người được phép điểm danh.", None
            
        # Có duy nhất 1 khuôn mặt
        face = faces[0]
        x1, y1, x2, y2 = face.bbox.astype(int)
        emb = face.normed_embedding
        
        best_id = "Unknown"
        max_sim = -1.0
        
        for student_id, known_emb in self.known_embeddings.items():
            sim = np.dot(emb, known_emb)
            if sim > max_sim:
                max_sim = sim
                best_id = student_id
                
        if max_sim > self.threshold:
            return True, f"Nhận diện thành công: {best_id}", best_id
        else:
            return False, "Khuôn mặt chưa được đăng ký!", None