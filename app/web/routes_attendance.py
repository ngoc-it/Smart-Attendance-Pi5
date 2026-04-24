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
    per_page = 100
    user_id = session.get('user_id')
    
    # Dữ liệu chính
    students = db.get_all_students(user_id=user_id, page=page, per_page=per_page)
    total_students = db.get_student_count(user_id=user_id)
    
    # Thời khóa biểu & Nghỉ phép
    schedule = db.get_user_schedule(user_id)
    leave_requests = db.get_leave_requests(user_id)
    
    # Kiểm tra trạng thái khuôn mặt
    student_ids = [s[0] for s in students]
    face_status = db.get_face_registration_status(student_ids)
    
    pagination = {
        "current": page,
        "total_pages": (total_students + per_page - 1) // per_page,
        "has_next": page * per_page < total_students,
        "has_prev": page > 1
    }
    
    return render_template('index.html', 
                           students=students, 
                           pagination=pagination,
                           schedule=schedule,
                           leave_requests=leave_requests,
                           face_status=face_status)

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
    class_name = request.args.get('class', None)
    
    # Lọc danh sách lớp dựa trên GV
    user_role = session.get('role')
    user_id = session.get('user_id')
    
    if user_role == 'admin':
        classes = db.get_all_classes()
    else:
        # Giảng viên chỉ thấy lớp mình được gán
        classes = db.get_user_classes(user_id)
    
    detailed_report = []
    stats = None
    
    if class_name:
        # Kiểm tra quyền truy cập lớp này nếu là GV
        if user_role == 'lecturer':
            allowed_classes = [c[1] for c in classes]
            if class_name not in allowed_classes:
                return "Bạn không có quyền xem lớp này", 403

        detailed_report = db.get_detailed_attendance(date_str, class_name)
        
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
                           selected_class=class_name)

@attendance_bp.route('/reports/export')
@login_required
def export_excel():
    from flask import send_file
    import pandas as pd
    import io
    
    date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    class_name = request.args.get('class', None)
    
    if not class_name:
        return "Vui lòng chọn lớp để xuất báo cáo", 400
        
    data = db.get_detailed_attendance(date_str, class_name)
    
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
    
    filename = f"DiemDanh_{class_name}_{date_str}.xlsx"
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
        
        # Here we just fetch the name to log, though ideally we should fetch from DB
        students = db.get_all_students()
        name = "Unknown"
        for s in students:
            if s[0] == student_id:
                name = s[1]
                break
                
        db.update_status(student_id, name, action)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500