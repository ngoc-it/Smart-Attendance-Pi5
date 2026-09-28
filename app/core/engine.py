import cv2
import numpy as np
import os
import time
from insightface.app import FaceAnalysis
from insightface.app.common import Face
from config import Config
from app.core import shared

class FaceEngine:
    def __init__(self, db):
        self.db = db
    # CHỈ nạp module detection và recognition để tiết kiệm 60% RAM
        self.app = FaceAnalysis(
            name='buffalo_l', 
            allowed_modules=['detection', 'recognition'], 
            providers=[('CPUExecutionProvider', {'intra_op_num_threads': 2, 'inter_op_num_threads': 2})]
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))
    
        self.known_embeddings = {}
        self.threshold = float(self.db.get_setting("match_threshold", Config.MATCH_THRESHOLD))
        
        # Khởi tạo bộ chống giả mạo liveness
        from app.core.antispoof import AntiSpoofDetector
        self.liveness_detector = AntiSpoofDetector()
        self.liveness_threshold = float(self.db.get_setting("liveness_threshold", 0.6))
        
        self.load_database()    

    def refresh_settings(self):
        """Cap nhat lai cac cau hinh tu Database"""
        self.threshold = float(self.db.get_setting("match_threshold", Config.MATCH_THRESHOLD))
        self.liveness_threshold = float(self.db.get_setting("liveness_threshold", 0.6))


    def load_database(self):
        """Nạp vector mẫu của các sinh viên ĐANG HOẠT ĐỘNG (is_active = 1) từ thư mục data/embeddings vào RAM"""
        if not os.path.exists(Config.EMBEDDINGS_DIR):
            os.makedirs(Config.EMBEDDINGS_DIR)
        
        # Lấy danh sách MSSV đang active từ DB
        active_student_ids = set()
        try:
            with self.db._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM students WHERE COALESCE(is_active, 1) = 1")
                rows = cursor.fetchall()
                active_student_ids = {row[0] for row in rows}
        except Exception as db_err:
            print(f"Engine: Lỗi truy vấn danh sách sinh viên active: {db_err}")

        self.known_embeddings = {}
        for file in os.listdir(Config.EMBEDDINGS_DIR):
            if file.endswith(".npy"):
                student_id = file.replace(".npy", "")
                # Chỉ nạp vào RAM nếu sinh viên đang active (hoặc nếu chưa lọc được DB)
                if active_student_ids and student_id not in active_student_ids:
                    continue
                try:
                    self.known_embeddings[student_id] = np.load(os.path.join(Config.EMBEDDINGS_DIR, file))
                except Exception as e:
                    print(f"Lỗi khi tải embedding {file}: {e}")

    def recognize(self, frame):
        """Nhan dien khuon mat tren mot khung hinh (Luồng tối ưu tách biệt Liveness)"""
        output = []
        bboxes, kpss = self.app.models['detection'].detect(frame, max_num=0, metric='default')
        if bboxes.shape[0] == 0:
            return output
            
        for i in range(bboxes.shape[0]):
            bbox = bboxes[i, 0:4]
            det_score = bboxes[i, 4]
            kps = kpss[i] if kpss is not None else None
            x1, y1, x2, y2 = bbox.astype(int)
            
            # 1. Chạy chống giả mạo (Anti-Spoofing) TRƯỚC
            is_real, liveness_score, liveness_label = self.liveness_detector.predict(
                frame, [x1, y1, x2, y2], threshold=self.liveness_threshold
            )
            
            # Nếu giả mạo, bỏ qua bước trích xuất đặc trưng cực nặng
            if not is_real:
                output.append({
                    "id": "Unknown",
                    "box": (x1, y1, x2, y2),
                    "confidence": 0.0,
                    "liveness": liveness_label,
                    "is_real": is_real
                })
                continue
                
            # 2. Nếu người thật, MỚI chạy ArcFace trích xuất vector
            face = Face(bbox=bbox, kps=kps, det_score=det_score)
            self.app.models['recognition'].get(frame, face)
            emb = face.normed_embedding
            
            best_id = "Unknown"
            max_sim = -1.0
            
            # So sanh Cosine Similarity
            for student_id, known_emb in self.known_embeddings.items():
                sim = float(np.dot(emb, known_emb))
                if sim > max_sim:
                    max_sim = sim
                    best_id = student_id
            
            # Phan loai dua tren nguong (Threshold) tu cau hinh
            if max_sim > self.threshold:
                output.append({
                    "id": best_id,
                    "box": (x1, y1, x2, y2),
                    "confidence": float(max_sim),
                    "liveness": liveness_label,
                    "is_real": is_real
                })
            else:
                output.append({
                    "id": "Unknown",
                    "box": (x1, y1, x2, y2),
                    "confidence": float(max_sim),
                    "liveness": liveness_label,
                    "is_real": is_real
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

    def verify_attendance(self, frame, return_meta=False):
        """Dùng cho màn hình cảm ứng: Kiểm tra duy nhất 1 khuôn mặt và trả về ID nếu nhận diện thành công"""
        t0 = time.time()
        
        meta = {
            "liveness_score": 0.0,
            "liveness_threshold": self.liveness_threshold,
            "liveness_result": False,
            "liveness_label": "Unknown",
            "attack_type": None,
            "similarity_score": -1.0,
            "match_threshold": self.threshold,
            "recognition_accepted": False,
            "recognition_result": "ERROR",
            "predicted_identity": None,
            "latency_face_recognition_ms": 0.0,
            "latency_liveness_ms": 0.0,
            "latency_matching_ms": 0.0
        }

        # 1. Detection via InsightFace (RetinaFace)
        t_det_start = time.time()
        bboxes, kpss = self.app.models['detection'].detect(frame, max_num=1, metric='default')
        
        if bboxes.shape[0] == 0:
            meta["recognition_result"] = "NO_FACE"
            meta["latency_face_recognition_ms"] = (time.time() - t_det_start) * 1000.0
            msg = "Không tìm thấy khuôn mặt nào!"
            return (False, msg, None, meta) if return_meta else (False, msg, None)
            
        if bboxes.shape[0] > 1:
            meta["recognition_result"] = "MULTIPLE_FACES"
            meta["latency_face_recognition_ms"] = (time.time() - t_det_start) * 1000.0
            msg = "Phát hiện nhiều người! Chỉ 1 người được phép điểm danh."
            return (False, msg, None, meta) if return_meta else (False, msg, None)
            
        # Có duy nhất 1 khuôn mặt
        bbox = bboxes[0, 0:4]
        det_score = bboxes[0, 4]
        kps = kpss[0] if kpss is not None else None
        x1, y1, x2, y2 = bbox.astype(int)
        
        # 2. Anti-Spoofing Check (MiniFASNetV2) TRƯỚC KHI trích xuất đặc trưng
        t_live_start = time.time()
        is_real, liveness_score, liveness_label = self.liveness_detector.predict(
            frame, [x1, y1, x2, y2], threshold=self.liveness_threshold
        )
        t_live_end = time.time()
        meta["latency_liveness_ms"] = (t_live_end - t_live_start) * 1000.0
        meta["liveness_score"] = float(liveness_score)
        meta["liveness_result"] = bool(is_real)
        meta["liveness_label"] = str(liveness_label)
        
        if not is_real:
            # Nếu giả mạo, ta bỏ qua phần ArcFace, do đó latency chỉ tốn cho Detection
            meta["latency_face_recognition_ms"] = (t_live_start - t_det_start) * 1000.0
            attack_type = "Ảnh chụp/Giấy in" if liveness_label == "Print-attack" else "Màn hình điện thoại/Video"
            meta["attack_type"] = liveness_label
            meta["recognition_result"] = "SPOOF_ATTACK"
            msg = f"Cảnh báo giả mạo! Phát hiện {attack_type} (độ tin cậy: {liveness_score:.2%})"
            return (False, msg, None, meta) if return_meta else (False, msg, None)
            
        # 3. Vector Feature Extraction (ArcFace) & Cosine Similarity Matching
        face = Face(bbox=bbox, kps=kps, det_score=det_score)
        t_rec_start = time.time()
        self.app.models['recognition'].get(frame, face)
        t_rec_end = time.time()
        
        # Tổng thời gian Face Recognition = thời gian Detection + thời gian Recognition
        meta["latency_face_recognition_ms"] = ((t_rec_end - t_rec_start) + (t_live_start - t_det_start)) * 1000.0
        
        emb = face.normed_embedding
        best_id = "Unknown"
        max_sim = -1.0
        
        t_match_start = time.time()
        for student_id, known_emb in self.known_embeddings.items():
            sim = float(np.dot(emb, known_emb))
            if sim > max_sim:
                max_sim = sim
                best_id = student_id
        t_match_end = time.time()
        meta["latency_matching_ms"] = (t_match_end - t_match_start) * 1000.0
        meta["similarity_score"] = float(max_sim)
        meta["predicted_identity"] = best_id
                
        if max_sim > self.threshold:
            meta["recognition_accepted"] = True
            meta["recognition_result"] = "SUCCESS"
            msg = f"Nhận diện thành công: {best_id}"
            return (True, msg, best_id, meta) if return_meta else (True, msg, best_id)
        else:
            meta["recognition_accepted"] = False
            meta["recognition_result"] = "UNREGISTERED"
            msg = "Khuôn mặt chưa được đăng ký!"
            return (False, msg, None, meta) if return_meta else (False, msg, None)