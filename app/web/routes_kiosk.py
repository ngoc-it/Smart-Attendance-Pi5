from flask import Blueprint, render_template, request, jsonify
import cv2
import os
import time
import psutil
from datetime import datetime
from config import Config
from app.core import shared
from app import ai_engine, db

kiosk_bp = Blueprint('kiosk', __name__)

@kiosk_bp.route('/kiosk', methods=['GET'])
def kiosk_page():
    """Giao diện Kiosk dành cho màn hình cảm ứng"""
    return render_template('kiosk.html')

@kiosk_bp.route('/api/kiosk/current_session', methods=['GET'])
def get_current_session():
    """Lấy thông tin ca học đang diễn ra hoặc sắp tới"""
    # 1. Kiểm tra ca đang diễn ra
    active = db.get_active_session()
    if active:
        return jsonify({
            "status": "active",
            "class_name": active['class_name'],
            "start_time": active['start_time'],
            "end_time": active['end_time']
        })
    
    # 2. Nếu không có ca đang diễn ra, tìm ca sắp tới
    upcoming = db.get_upcoming_session()
    if upcoming:
        return jsonify({
            "status": "upcoming",
            "class_name": upcoming['class_name'],
            "start_time": upcoming['start_time'],
            "end_time": upcoming['end_time']
        })
    
    return jsonify({"status": "idle"})

@kiosk_bp.route('/api/kiosk/check', methods=['POST'])
def kiosk_check():
    """Xử lý điểm danh: Kiểm tra tiết học trước, nhận diện sau"""
    t_req_start = time.perf_counter()
    cpu_samples = [psutil.cpu_percent(interval=None)]
    proc_mem = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    ram_samples = [proc_mem]

    active_session = None
    session_id = None
    class_id = None
    student_id = None
    student_name = None
    new_action = "NONE"
    authorization_result = False
    attendance_status = "ERROR"

    meta = {
        "liveness_score": None,
        "liveness_threshold": getattr(ai_engine, "liveness_threshold", 0.60),
        "liveness_result": False,
        "liveness_label": "Unknown",
        "attack_type": None,
        "similarity_score": None,
        "match_threshold": getattr(ai_engine, "threshold", 0.65),
        "recognition_accepted": False,
        "recognition_result": "ERROR",
        "predicted_identity": None,
        "latency_face_recognition_ms": 0.0,
        "latency_liveness_ms": 0.0,
        "latency_matching_ms": 0.0
    }

    def _safe_log_experiment(res_status):
        nonlocal attendance_status
        attendance_status = res_status
        t_req_end = time.perf_counter()
        latency_total_ms = (t_req_end - t_req_start) * 1000.0
        try:
            from app.core.experiment_logger import get_experiment_logger
            exp_logger = get_experiment_logger()
            exp_logger.log_request(
                session_id=session_id,
                class_id=class_id,
                expected_identity=None,
                predicted_identity=meta.get("predicted_identity"),
                similarity_score=meta.get("similarity_score"),
                match_threshold=meta.get("match_threshold", 0.65),
                recognition_accepted=meta.get("recognition_accepted", False),
                recognition_result=meta.get("recognition_result", "ERROR"),
                liveness_score=meta.get("liveness_score"),
                liveness_threshold=meta.get("liveness_threshold", 0.60),
                liveness_result=meta.get("liveness_result", False),
                attack_type=meta.get("attack_type"),
                authorization_result=authorization_result,
                attendance_action=new_action,
                attendance_status=attendance_status,
                latency_total_ms=latency_total_ms,
                latency_liveness_ms=meta.get("latency_liveness_ms", 0.0),
                latency_face_recognition_ms=meta.get("latency_face_recognition_ms", 0.0),
                latency_matching_ms=meta.get("latency_matching_ms", 0.0),
                cpu_samples=cpu_samples,
                ram_samples=ram_samples
            )
        except Exception as logger_err:
            print(f"[Kiosk Log Error] {logger_err}")

    def _save_failed_image_log(frame_img, category, detail_msg=""):
        """Lưu ảnh lỗi/thất bại phân loại theo thư mục riêng trong data/failed_log_images/"""
        try:
            if frame_img is None:
                return
            base_dir = getattr(Config, 'FAILED_LOG_IMAGES_DIR', os.path.join(Config.BASE_DIR, "data/failed_log_images"))
            cat_dir = os.path.join(base_dir, category)
            os.makedirs(cat_dir, exist_ok=True)
            
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S_%f")[:19]
            file_name = f"{timestamp}_{category}.jpg"
            file_path = os.path.join(cat_dir, file_name)
            
            save_frame = frame_img.copy()
            # Vẽ thanh tiêu đề thông tin lỗi ở mép trên ảnh
            cv2.rectangle(save_frame, (0, 0), (640, 36), (0, 0, 160), -1)
            info_text = f"FAIL: {category.upper()} | {detail_msg} | {now.strftime('%H:%M:%S %d/%m/%Y')}"
            cv2.putText(save_frame, info_text[:75], (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imwrite(file_path, save_frame)
        except Exception as err:
            print(f"[Save Failed Image Error]: {err}")

    try:
        # --- QUY TẮC SENIOR: KIỂM TRA ĐIỀU KIỆN TRƯỚC (FAIL FAST) ---
        
        # 1. Kiểm tra Session hiện tại (Nếu không có tiết, không chạy AI)
        active_session = db.get_active_session()
        if not active_session:
            _safe_log_experiment("NO_ACTIVE_SESSION")
            with shared.frame_lock:
                if shared.last_frame is not None:
                    _save_failed_image_log(shared.last_frame, "no_active_session", "Bấm ngoài giờ ca học")
            return jsonify({
                "status": "error", 
                "message": "Hiện không có ca học nào đang diễn ra. Vui lòng quay lại vào đúng giờ học!"
            }), 403
            
        class_id = active_session.get('class_id')
        session_id = active_session.get('session_id', active_session.get('id'))

        # 2. Lấy frame từ shared memory
        with shared.frame_lock:
            if shared.last_frame is None:
                _safe_log_experiment("CAMERA_NOT_READY")
                return jsonify({"status": "error", "message": "Camera chưa sẵn sàng!"}), 503
            frame = shared.last_frame.copy()
            
        # 3. Xử lý AI (Nhận diện khuôn mặt)
        try:
            success, msg, student_id, meta = ai_engine.verify_attendance(frame, return_meta=True)
        except Exception as ai_err:
            _safe_log_experiment("AI_ERROR")
            _save_failed_image_log(frame, "system_error", f"Loi AI: {str(ai_err)}")
            return jsonify({"status": "error", "message": f"Lỗi AI: {str(ai_err)}"}), 500
        
        if not success:
            _safe_log_experiment("REJECTED")
            rec_res = meta.get("recognition_result", "REJECTED")
            if rec_res == "SPOOF_ATTACK":
                atk = meta.get("attack_type", "Spoof")
                score = meta.get("liveness_score", 0.0)
                score_str = f"{score:.2%}" if isinstance(score, (int, float)) else str(score)
                _save_failed_image_log(frame, "spoof_attack", f"Gia mao: {atk} ({score_str})")
            elif rec_res == "NO_FACE":
                _save_failed_image_log(frame, "no_face", "Khong tim thay mat")
            elif rec_res == "MULTIPLE_FACES":
                _save_failed_image_log(frame, "multiple_faces", "Phat hien nhieu mat")
            else:
                _save_failed_image_log(frame, "rejected", msg)
            return jsonify({"status": "error", "message": msg}), 400
            
        # 4. Kiểm tra danh sách lớp (Sinh viên có thuộc lớp này không?)
        try:
            students = db.get_all_students(class_id=class_id, per_page=1000)
            student_data = next((s for s in students if s[0] == student_id), None)
            
            if not student_data:
                authorization_result = False
                _safe_log_experiment("NOT_IN_CLASS")
                _save_failed_image_log(frame, "not_in_class", f"SV {student_id} khong thuoc lop")
                return jsonify({
                    "status": "error", 
                    "message": f"Bạn không có trong danh sách lớp {active_session['class_name']}!"
                }), 403
                
            authorization_result = True
            student_name = student_data[1]
            current_status = student_data[4]
        except Exception as db_err:
            _safe_log_experiment("DB_ERROR")
            _save_failed_image_log(frame, "system_error", f"Loi DB: {str(db_err)}")
            return jsonify({"status": "error", "message": f"Lỗi dữ liệu sinh viên: {str(db_err)}"}), 500
                
        # 5. Quyết định hành động (IN / OUT)
        new_action = "OUT" if current_status == "IN" else "IN"
        
        # 6. Lưu ảnh điểm danh
        if not os.path.exists(Config.LOG_IMAGES_DIR):
            os.makedirs(Config.LOG_IMAGES_DIR)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"{student_id}_{new_action}_{timestamp}.jpg"
        image_path = os.path.join(Config.LOG_IMAGES_DIR, image_filename)
        
        save_frame = frame.copy()
        cv2.putText(save_frame, f"{student_id} - {new_action}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imwrite(image_path, save_frame)
        
        # 7. Lưu vào DB
        try:
            db.update_status(student_id, student_name, new_action, image_filename)
        except Exception as upd_err:
            _safe_log_experiment("DB_UPDATE_ERROR")
            _save_failed_image_log(frame, "system_error", f"Loi Update DB: {str(upd_err)}")
            return jsonify({"status": "error", "message": f"Lỗi cập nhật điểm danh: {str(upd_err)}"}), 500
        
        # 8. Phản hồi
        welcome_msg = f"Xin chào, {student_name}!" if new_action == "IN" else f"Tạm biệt, {student_name}!"
        _safe_log_experiment("SUCCESS")
        return jsonify({
            "status": "success",
            "message": f"{welcome_msg} Bạn đã Check-{new_action} thành công.",
            "action": new_action,
            "student_name": student_name,
            "student_id": student_id
        })
        
    except Exception as e:
        _safe_log_experiment("SYSTEM_ERROR")
        with shared.frame_lock:
            if shared.last_frame is not None:
                _save_failed_image_log(shared.last_frame, "system_error", str(e))
        return jsonify({"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}), 500

@kiosk_bp.route('/api/kiosk/exit', methods=['POST'])
def exit_kiosk():
    """Thoát ứng dụng bằng cách đóng trình duyệt Chromium"""
    import os
    os.system("pkill chromium")
    return jsonify({"status": "success", "message": "Exiting..."})
