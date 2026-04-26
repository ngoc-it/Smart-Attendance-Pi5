from flask import Blueprint, render_template, Response, request, session, jsonify
from datetime import datetime
import cv2
import time
import numpy as np
from app import db
from app.core import shared
from app.core.auth_utils import login_required, lecturer_required

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/')
@lecturer_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    class_id = request.args.get('class_id', type=int)
    
    # Lấy danh sách lớp của GV hoặc tất cả nếu là admin
    user_role = session.get('role')
    user_id = session.get('user_id')
    if user_role == 'admin':
        classes = db.get_all_classes(per_page=100)
    else:
        classes = db.get_user_classes(user_id)
        if not class_id and classes:
            class_id = classes[0][0]
            
    # Dữ liệu chính
    students = db.get_all_students(user_id=user_id, class_id=class_id, page=page, per_page=per_page)
    total_students = db.get_student_count(user_id=user_id, class_id=class_id)
    
    # Thời khóa biểu & Nghỉ phép
    schedule = db.get_user_schedule(user_id)
    leave_requests = db.get_leave_requests(user_id)
    
    # Kiểm tra trạng thái khuôn mặt
    student_ids = [s[0] for s in students]
    face_status = db.get_face_registration_status(student_ids)
    
    pagination = {
        "current": page,
        "total_pages": (total_students + per_page - 1) // per_page,
        "total_items": total_students,
        "has_next": page * per_page < total_students,
        "has_prev": page > 1
    }
    
    return render_template('index.html', 
                           students=students, 
                           pagination=pagination,
                           total_students=total_students,
                           schedule=schedule,
                           leave_requests=leave_requests,
                           face_status=face_status,
                           classes=classes,
                           selected_class_id=class_id)

@attendance_bp.route('/leave/update', methods=['POST'])
@lecturer_required
def update_leave():
    data = request.json
    db.update_leave_status(data['request_id'], data['status'])
    return jsonify({"status": "success"})

@attendance_bp.route('/reports')
@lecturer_required
def reports():
    from flask import request, session
    date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    class_id = request.args.get('class_id', type=int)
    class_name_legacy = request.args.get('class', None)
    
    # Lọc danh sách lớp dựa trên GV
    user_role = session.get('role')
    user_id = session.get('user_id')
    
    if user_role == 'admin':
        classes = db.get_all_classes(per_page=1000)
    else:
        # Giảng viên chỉ thấy lớp mình được gán
        classes = db.get_user_classes(user_id)
    
    detailed_report = []
    stats = None
    current_class_name = ""
    
    # Ưu tiên class_id, nếu không có thử dùng class_name (tương thích cũ)
    target_class = class_id or class_name_legacy
    
    if target_class:
        # Kiểm tra quyền truy cập lớp này nếu là GV
        if user_role == 'lecturer':
            if class_id:
                allowed_ids = [c[0] for c in classes]
                if class_id not in allowed_ids:
                    return "Bạn không có quyền xem lớp này", 403
            elif class_name_legacy:
                allowed_names = [c[1] for c in classes]
                if class_name_legacy not in allowed_names:
                    return "Bạn không có quyền xem lớp này", 403

        detailed_report = db.get_detailed_attendance(date_str, target_class)
        
        # Tìm tên lớp để hiển thị
        for cls in classes:
            if (class_id and cls[0] == class_id) or (class_name_legacy and cls[1] == class_name_legacy):
                current_class_name = f"[{cls[2]}] {cls[1]}" if cls[2] else cls[1]
                if not class_id: class_id = cls[0] # Cập nhật class_id để UI đồng bộ
                break
        
        # Thống kê nhanh cho lớp được chọn
        total = len(detailed_report)
        present = len([r for r in detailed_report if r['status'] != 'Vắng'])
        stats = {
            "total": total,
            "present": present,
            "absent": total - present
        }
    
    return render_template('reports.html', 
                           stats=stats, 
                           report=detailed_report, 
                           classes=classes,
                           selected_date=date_str,
                           selected_class_id=class_id,
                           current_class_name=current_class_name)

@attendance_bp.route('/reports/export')
@login_required
def export_excel():
    from flask import send_file
    import pandas as pd
    import io
    
    date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    class_id = request.args.get('class_id', type=int)
    class_name_legacy = request.args.get('class', None)
    
    target_class = class_id or class_name_legacy
    
    if not target_class:
        return "Vui lòng chọn lớp để xuất báo cáo", 400
        
    data = db.get_detailed_attendance(date_str, target_class)
    
    # Chuyển đổi dữ liệu sang DataFrame
    df = pd.DataFrame(data)
    
    # Việt hóa tiêu đề cột
    df = df.rename(columns={
        "id": "MSSV",
        "name": "Họ và Tên",
        "in_time": "Giờ vào",
        "out_time": "Giờ ra",
        "status": "Trạng thái"
    })
    
    # Bỏ cột ảnh khi xuất excel
    if 'image' in df.columns:
        df = df.drop(columns=['image'])
        
    # Tạo file Excel trong bộ nhớ
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Diem_Danh')
        
    output.seek(0)
    
    filename = f"DiemDanh_{target_class}_{date_str}.xlsx"
    return send_file(output, 
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True,
                     download_name=filename)

@attendance_bp.route('/video_feed')
def video_feed():
    def generate():
        while True:
            time.sleep(0.04) # 25 FPS
            img = None
            
            # TRUY XUẤT TỪ SHARED
            with shared.frame_lock:
                if shared.last_frame is not None:
                    img = shared.last_frame.copy()
            
            if img is not None:
                # LẤY KẾT QUẢ AI TỪ SHARED
                results = shared.last_results
                for res in results:
                    x1, y1, x2, y2 = res['box']
                    name = res['id']
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(img, name, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                # Màn hình chờ nếu camera chưa có data trong shared
                img = np.zeros((480, 640, 3), np.uint8)
                img[:] = (40, 40, 40)
                cv2.putText(img, "CONNECTING VIA SHARED MEMORY...", (100, 240), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            ret, buffer = cv2.imencode('.jpg', img)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@attendance_bp.route('/api/student/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    try:
        from app import ai_engine
        import os
        from config import Config
        
        # 1. Delete from DB
        db.delete_student(student_id)
        
        # 2. Delete embedding file
        emb_path = os.path.join(Config.EMBEDDINGS_DIR, f"{student_id}.npy")
        if os.path.exists(emb_path):
            os.remove(emb_path)
            
        # 3. Reload AI engine database
        ai_engine.load_database()
        
        return {"status": "success", "message": "Deleted successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@attendance_bp.route('/api/student/<student_id>', methods=['PUT'])
def update_student(student_id):
    from flask import request
    try:
        data = request.json
        name = data.get('name')
        dob = data.get('dob')
        student_class = data.get('student_class')
        
        db.update_student_info(student_id, name, dob, student_class)
        
        return {"status": "success", "message": "Updated successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@attendance_bp.route('/attendance/action', methods=['POST'])
def manual_action():
    from flask import request
    try:
        data = request.json
        student_id = data.get('id')
        action = data.get('action')
        
        # Lấy tên sinh viên từ DB
        name = db.get_student_name(student_id)
                
        db.update_status(student_id, name, action)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@attendance_bp.route('/images/<path:filename>')
@login_required
def serve_image(filename):
    from flask import send_from_directory
    from config import Config
    return send_from_directory(Config.LOG_IMAGES_DIR, filename)