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

@kiosk_bp.route('/api/kiosk/check', methods=['POST'])
def kiosk_check():
    """Xử lý điểm danh khi sinh viên bấm nút"""
    try:
        # 1. Lấy frame mới nhất từ shared memory
        with shared.frame_lock:
            if shared.last_frame is None:
                return jsonify({"status": "error", "message": "Camera chưa sẵn sàng!"}), 503
            frame = shared.last_frame.copy()
            
        # 2. Xử lý AI
        success, msg, student_id = ai_engine.verify_attendance(frame)
        
        if not success:
            return jsonify({"status": "error", "message": msg}), 400
            
        # 3. Lấy thông tin sinh viên từ DB
        students = db.get_all_students()
        student_name = "Unknown"
        current_status = "OUT"
        
        for s in students:
            if s[0] == student_id:
                student_name = s[1]
                current_status = s[4]
                break
                
        # 4. Quyết định hành động (IN / OUT)
        # Tự động đảo ngược trạng thái. Nếu là REGISTERED hoặc OUT thì thành IN. Nếu IN thì thành OUT.
        new_action = "OUT" if current_status == "IN" else "IN"
        
        # 5. Lưu ảnh điểm danh
        if not os.path.exists(Config.LOG_IMAGES_DIR):
            os.makedirs(Config.LOG_IMAGES_DIR)
            
        timestamp = datetime.now().strftime("%Y%md_%H%M%S")
        image_filename = f"{student_id}_{new_action}_{timestamp}.jpg"
        image_path = os.path.join(Config.LOG_IMAGES_DIR, image_filename)
        
        # Vẽ một khung xanh báo hiệu lên ảnh lưu trữ
        save_frame = frame.copy()
        cv2.putText(save_frame, f"{student_id} - {new_action}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imwrite(image_path, save_frame)
        
        # 6. Lưu vào DB
        db.update_status(student_id, student_name, new_action, image_filename)
        
        # 7. Phản hồi
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
    # Sử dụng pkill để đóng tất cả các tiến trình chromium
    # Điều này sẽ khiến script launch_kiosk.sh kết thúc hoặc quay về desktop
    os.system("pkill chromium")
    return jsonify({"status": "success", "message": "Exiting..."})
