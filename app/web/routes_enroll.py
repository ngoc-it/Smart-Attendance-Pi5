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
    page = request.args.get('page', 1, type=int)
    per_page = 10
    user_role = session.get('role')
    user_id = session.get('user_id')
    
    class_id = request.args.get('class_id', type=int)
    student_id = request.args.get('student_id')
    student_data = None
    if student_id:
        student_data = db.get_student_by_id(student_id)
    
    if user_role == 'admin':
        classes = db.get_all_classes(per_page=100)
        students = db.get_all_students(class_id=class_id, page=page, per_page=per_page)
        total_students = db.get_student_count(class_id=class_id)
    else:
        # Giảng viên chỉ thấy lớp mình được gán
        classes = db.get_user_classes(user_id)
        # Nếu chưa chọn lớp, lấy lớp đầu tiên của GV (nếu có)
        if not class_id and classes:
            class_id = classes[0][0]
            
        students = db.get_all_students(user_id=user_id, class_id=class_id, page=page, per_page=per_page)
        total_students = db.get_student_count(user_id=user_id, class_id=class_id)
        
    # Kiểm tra trạng thái đăng ký khuôn mặt
    student_ids = [s[0] for s in students]
    face_status = db.get_face_registration_status(student_ids)
    
    pagination = {
        "current": page,
        "total_pages": (total_students + per_page - 1) // per_page,
        "has_next": page * per_page < total_students,
        "has_prev": page > 1
    }
    
    return render_template('enroll.html', 
                           classes=classes, 
                           students=students,
                           face_status=face_status,
                           selected_class_id=class_id,
                           pagination=pagination,
                           student=student_data)

@enroll_bp.route('/api/enroll/import', methods=['POST'])
@lecturer_required
def enroll_import():
    """Import danh sách sinh viên từ file Excel"""
    user_id = session.get('user_id')
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Không tìm thấy file"}), 400
    
    file = request.files['file']
    ui_class_id = request.form.get('class_id')
    
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
        
        # 1. Xác định lớp học đích (Ưu tiên từ UI, sau đó từ Excel)
        if ui_class_id:
            class_id = int(ui_class_id)
        else:
            # Logic lấy từ Excel như cũ
            course_display_name = data.get('course_name') or "Lớp mới"
            class_section = data.get('class_section') or course_display_name
            target_class_name = f"{course_display_name} ({class_section})" if class_section != course_display_name else course_display_name
            
            all_classes = {c[1]: c[0] for c in db.get_all_classes(per_page=1000)}
            if target_class_name not in all_classes:
                db.create_class(target_class_name)
                all_classes = {c[1]: c[0] for c in db.get_all_classes(per_page=1000)}
            class_id = all_classes.get(target_class_name)
        if class_id:
            db.assign_class_to_user(user_id, class_id)
            
        # 2. Lưu/Cập nhật sinh viên vào DB với lớp học phần này
        for s in data['students']:
            is_new = not db.check_student_exists(s['id'])
            # Link sinh viên tới lớp học phần (course_class_id) và lưu lớp cố định (s['class'])
            db.enroll_student(s['id'], s['name'], s['dob'], s['class'], course_class_id=class_id)
            if is_new:
                count += 1
        
        os.remove(temp_path)
        total_in_file = len(data['students'])
        return jsonify({
            "status": "success", 
            "message": f"Xử lý xong {total_in_file} sinh viên. (Thêm mới: {count})",
            "class_id": class_id
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
        s_class = data.get('student_class', '') # Lớp cố định (VD: XD25D01)
        course_class_id = data.get('course_class_id') # Lớp học phần ID (VD: 1)
        
        if not s_id or not s_name:
            return jsonify({"status": "error", "message": "Thiếu MSSV hoặc Họ tên"}), 400
            
        # Không chặn nếu MSSV đã tồn tại (vì có thể đã import từ Excel hoặc muốn nạp lại khuôn mặt)
        # Hệ thống sẽ tự động cập nhật thông tin và ghi đè khuôn mặt mới.
        
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
                    db.enroll_student(s_id, s_name, s_dob, s_class, course_class_id=course_class_id)
                    
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
@enroll_bp.route('/api/enroll/clear_class', methods=['POST'])
@lecturer_required
def clear_class():
    data = request.json
    class_id = data.get('class_id')
    if not class_id:
        return jsonify({"status": "error", "message": "Thiếu Class ID"}), 400
        
    db.remove_all_students_from_class(class_id)
    return jsonify({"status": "success", "message": "Đã xóa toàn bộ sinh viên khỏi danh sách lớp này."})
