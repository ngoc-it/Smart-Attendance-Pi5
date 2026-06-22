from flask import Blueprint, render_template, request, jsonify
import cv2
import os
import time
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
    try:
        # --- QUY TẮC SENIOR: KIỂM TRA ĐIỀU KIỆN TRƯỚC (FAIL FAST) ---
        
        # 1. Kiểm tra Session hiện tại (Nếu không có tiết, không chạy AI)
        active_session = db.get_active_session()
        if not active_session:
            return jsonify({
                "status": "error", 
                "message": "Hiện không có ca học nào đang diễn ra. Vui lòng quay lại vào đúng giờ học!"
            }), 403
            
        class_id = active_session['class_id']

        # 2. Lấy frame từ shared memory
        with shared.frame_lock:
            if shared.last_frame is None:
                return jsonify({"status": "error", "message": "Camera chưa sẵn sàng!"}), 503
            frame = shared.last_frame.copy()
            
        # 3. Xử lý AI (Nhận diện khuôn mặt)
        try:
            success, msg, student_id = ai_engine.verify_attendance(frame)
        except Exception as ai_err:
            return jsonify({"status": "error", "message": f"Lỗi AI: {str(ai_err)}"}), 500
        
        if not success:
            return jsonify({"status": "error", "message": msg}), 400
            
        # 4. Kiểm tra danh sách lớp (Sinh viên có thuộc lớp này không?)
        try:
            students = db.get_all_students(class_id=class_id, per_page=1000)
            student_data = next((s for s in students if s[0] == student_id), None)
            
            if not student_data:
                return jsonify({
                    "status": "error", 
                    "message": f"Bạn không có trong danh sách lớp {active_session['class_name']}!"
                }), 403
                
            student_name = student_data[1]
            current_status = student_data[4]
        except Exception as db_err:
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
            return jsonify({"status": "error", "message": f"Lỗi cập nhật điểm danh: {str(upd_err)}"}), 500
        
        # 8. Phản hồi
        welcome_msg = f"Xin chào, {student_name}!" if new_action == "IN" else f"Tạm biệt, {student_name}!"
        return jsonify({
            "status": "success",
            "message": f"{welcome_msg} Bạn đã Check-{new_action} thành công.",
            "action": new_action,
            "student_name": student_name,
            "student_id": student_id
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}), 500

@kiosk_bp.route('/api/kiosk/exit', methods=['POST'])
def exit_kiosk():
    """Thoát ứng dụng bằng cách đóng trình duyệt Chromium"""
    import os
    os.system("pkill chromium")
    return jsonify({"status": "success", "message": "Exiting..."})
