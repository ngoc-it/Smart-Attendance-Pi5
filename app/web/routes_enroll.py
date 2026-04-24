from flask import Blueprint, render_template, request, jsonify, session
import cv2
import os
import threading
# Import cac thanh phan he thong
from app.core import shared
from app import ai_engine, db
from app.core.auth_utils import login_required, lecturer_required
from app.core.importer import ExcelImporter

# Dinh nghia Blueprint cho chuc nang dang ky
enroll_bp = Blueprint('enroll', __name__)

@enroll_bp.route('/enroll', methods=['GET'])
@lecturer_required
def enroll_page():
    """Hàm trả về giao diện HTML cho Laptop truy cập"""
    user_role = session.get('role')
    user_id = session.get('user_id')
    
    if user_role == 'admin':
        classes = db.get_all_classes()
        # Admin thấy 50 sinh viên mới nhất
        students = db.get_all_students(per_page=50)
    else:
        # Giảng viên chỉ thấy lớp mình được gán để đăng ký
        classes = db.get_user_classes(user_id)
        students = db.get_all_students(user_id=user_id, per_page=100) # Lấy 100 sv của GV
        
    # Kiểm tra trạng thái đăng ký khuôn mặt
    student_ids = [s[0] for s in students]
    face_status = db.get_face_registration_status(student_ids)
    
    return render_template('enroll.html', 
                           classes=classes, 
                           students=students, 
                           face_status=face_status)

@enroll_bp.route('/api/enroll/import', methods=['POST'])
@lecturer_required
def enroll_import():
    """Import danh sách sinh viên từ file Excel"""
    user_id = session.get('user_id')
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Không tìm thấy file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "Tên file trống"}), 400
        
    # Lưu tạm file
    temp_path = os.path.join("/tmp", file.filename)
    file.save(temp_path)
    
    try:
        data = ExcelImporter.parse_student_list(temp_path)
        if not data:
            return jsonify({"status": "error", "message": "Lỗi định dạng file Excel"}), 400
            
        count = 0
        target_class = data.get('class_section') or data['students'][0]['class'] if data['students'] else "Imported Class"
        
        # 1. Đảm bảo lớp học (Lớp học phần) tồn tại và được gán cho GV
        all_classes = {c[1]: c[0] for c in db.get_all_classes(per_page=1000)}
        if target_class not in all_classes:
            db.create_class(target_class)
            all_classes = {c[1]: c[0] for c in db.get_all_classes(per_page=1000)}
        
        class_id = all_classes.get(target_class)
        if class_id:
            db.assign_class_to_user(user_id, class_id)
            
        # 2. Lưu/Cập nhật sinh viên vào DB với lớp học phần này
        for s in data['students']:
            is_new = not db.check_student_exists(s['id'])
            # Luôn cập nhật thông tin và lớp mới nhất từ Excel
            db.enroll_student(s['id'], s['name'], s['dob'], target_class)
            if is_new:
                count += 1
        
        os.remove(temp_path)
        total_in_file = len(data['students'])
        return jsonify({
            "status": "success", 
            "message": f"Xử lý xong {total_in_file} sinh viên. (Thêm mới: {count})"
        })
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        return jsonify({"status": "error", "message": str(e)}), 500

@enroll_bp.route('/api/enroll/start', methods=['POST'])
@lecturer_required
def enroll_start():
    """Bắt đầu quá trình đăng ký (chạy background)"""
    try:
        data = request.get_json() if request.is_json else request.form
        s_id = data.get('mssv')
        s_name = data.get('name')
        s_dob = data.get('dob', '')
        s_class = data.get('student_class', '')
        
        if not s_id or not s_name:
            return jsonify({"status": "error", "message": "Thiếu MSSV hoặc Họ tên"}), 400
            
        # Kiểm tra trùng MSSV
        if db.check_student_exists(s_id):
            return jsonify({"status": "error", "message": "MSSV này đã tồn tại trong hệ thống!"}), 400
            
        # Kiểm tra tiến trình đăng ký đang chạy
        with shared.enroll_lock:
            if shared.enroll_state.get("status") == "processing":
                return jsonify({"status": "error", "message": "Hệ thống đang bận đăng ký cho người khác."}), 409
        
        # Bắt đầu thread
        def worker():
            ai_engine.enroll_session_worker(s_id)
            with shared.enroll_lock:
                if shared.enroll_state["status"] == "success":
                    # Lưu vào db sau khi AI hoàn tất
                    db.enroll_student(s_id, s_name, s_dob, s_class)
                    
                    # Reset trạng thái về idle sau 3 giây (để UI kịp đọc)
                    def reset():
                        import time
                        time.sleep(3)
                        with shared.enroll_lock:
                            if shared.enroll_state["status"] == "success":
                                shared.enroll_state["status"] = "idle"
                                shared.enroll_state["progress"] = 0
                                shared.enroll_state["message"] = ""
                    threading.Thread(target=reset).start()

        t = threading.Thread(target=worker)
        t.start()
        
        return jsonify({"status": "success", "message": "Đã bắt đầu thu thập khuôn mặt."})

    except Exception as e:
        print(f"CRITICAL ERROR TẠI /api/enroll/start: {str(e)}")
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500

@enroll_bp.route('/api/enroll/status', methods=['GET'])
@lecturer_required
def enroll_status():
    """Lấy trạng thái quá trình đăng ký"""
    with shared.enroll_lock:
        return jsonify({
            "status": shared.enroll_state.get("status", "idle"),
            "progress": shared.enroll_state.get("progress", 0),
            "message": shared.enroll_state.get("message", "")
        })