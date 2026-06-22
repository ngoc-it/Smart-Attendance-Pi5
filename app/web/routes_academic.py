from flask import Blueprint, render_template, request, jsonify
from app import db
from app.core.auth_utils import admin_required
from app.utils.excel_parser import parse_curriculum_excel
import os

academic_bp = Blueprint('academic', __name__, url_prefix='/admin/academic')

@academic_bp.route('/', methods=['GET'])
@admin_required
def academic_page():
    depts = db.get_all_departments()
    majors = db.get_majors()
    courses = db.get_courses()
    semesters = db.get_all_semesters()
    classes = db.get_all_classes(per_page=1000)
    rooms = db.get_all_rooms()
    periods = db.get_all_periods()
    holidays = db.get_holidays()
    return render_template('admin_academic.html',
                           depts=depts, majors=majors, courses=courses,
                           semesters=semesters, classes=classes,
                           rooms=rooms, periods=periods, holidays=holidays)

# ---- DEPARTMENTS ----
@academic_bp.route('/department', methods=['POST'])
@admin_required
def create_department():
    data = request.json
    success = db.create_department(data['name'])
    if success:
        return jsonify({"status": "success", "message": "Đã thêm Khoa"})
    return jsonify({"status": "error", "message": "Tên Khoa đã tồn tại"}), 400

@academic_bp.route('/department/<int:dept_id>', methods=['PUT'])
@admin_required
def update_department(dept_id):
    data = request.json
    success = db.update_department(dept_id, data['name'])
    if success:
        return jsonify({"status": "success", "message": "Đã cập nhật Khoa"})
    return jsonify({"status": "error", "message": "Lỗi cập nhật"}), 400

@academic_bp.route('/department/<int:dept_id>', methods=['DELETE'])
@admin_required
def delete_department(dept_id):
    success = db.delete_department(dept_id)
    if success:
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Không thể xóa (có Ngành liên kết)"}), 400

# ---- MAJORS ----
@academic_bp.route('/major', methods=['POST'])
@admin_required
def create_major():
    data = request.json
    success = db.create_major(data['name'], data['department_id'])
    if success:
        return jsonify({"status": "success", "message": "Đã thêm Ngành"})
    return jsonify({"status": "error", "message": "Tên Ngành đã tồn tại"}), 400

@academic_bp.route('/major/<int:major_id>', methods=['PUT'])
@admin_required
def update_major(major_id):
    data = request.json
    success = db.update_major(major_id, data['name'], data['department_id'])
    if success:
        return jsonify({"status": "success", "message": "Đã cập nhật Ngành"})
    return jsonify({"status": "error", "message": "Lỗi cập nhật"}), 400

@academic_bp.route('/major/<int:major_id>', methods=['DELETE'])
@admin_required
def delete_major(major_id):
    success = db.delete_major(major_id)
    if success:
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Không thể xóa (có Học phần liên kết)"}), 400

# ---- COURSES ----
@academic_bp.route('/course', methods=['POST'])
@admin_required
def create_course():
    data = request.json
    success = db.create_course(
        name=data['name'], 
        major_id=data.get('major_id'),
        code=data.get('code'),
        category=data.get('category'),
        credits=data.get('credits', 0),
        lt_credits=data.get('lt_credits', 0),
        th_credits=data.get('th_credits', 0),
        total_periods=data.get('total_periods', 0)
    )
    if success:
        return jsonify({"status": "success", "message": "Đã thêm Học phần"})
    return jsonify({"status": "error", "message": "Lỗi thêm học phần"}), 400

@academic_bp.route('/course/<int:course_id>', methods=['PUT'])
@admin_required
def update_course(course_id):
    data = request.json
    success = db.update_course(
        course_id=course_id,
        name=data['name'],
        major_id=data.get('major_id'),
        code=data.get('code'),
        category=data.get('category'),
        credits=data.get('credits', 0),
        lt_credits=data.get('lt_credits', 0),
        th_credits=data.get('th_credits', 0),
        total_periods=data.get('total_periods', 0)
    )
    if success:
        return jsonify({"status": "success", "message": "Đã cập nhật Học phần"})
    return jsonify({"status": "error", "message": "Lỗi cập nhật"}), 400

@academic_bp.route('/course/<int:course_id>', methods=['DELETE'])
@admin_required
def delete_course(course_id):
    success = db.delete_course(course_id)
    if success:
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Không thể xóa (có Lớp học phần liên kết)"}), 400

# ---- SEMESTERS ----
@academic_bp.route('/semester', methods=['POST'])
@admin_required
def create_semester():
    data = request.json
    db.create_semester(data['name'], data['start_date'], data['end_date'], data.get('is_current', 0))
    return jsonify({"status": "success", "message": "Đã tạo học kỳ mới"})

@academic_bp.route('/semester/<int:sem_id>/set_current', methods=['POST'])
@admin_required
def set_current_semester(sem_id):
    db.set_current_semester(sem_id)
    return jsonify({"status": "success", "message": "Đã đặt làm học kỳ hiện tại"})

@academic_bp.route('/semester/<int:sem_id>', methods=['PUT'])
@admin_required
def update_semester(sem_id):
    data = request.json
    success, msg = db.update_semester(sem_id, data['name'], data['start_date'], data['end_date'])
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"status": "error", "message": msg}), 400

@academic_bp.route('/semester/<int:sem_id>', methods=['DELETE'])
@admin_required
def delete_semester(sem_id):
    success = db.delete_semester(sem_id)
    if success:
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Không thể xóa học kỳ đang diễn ra"}), 400

# ---- ROOMS ----
@academic_bp.route('/room', methods=['POST'])
@admin_required
def create_room():
    data = request.json
    success = db.create_room(data['name'], data.get('capacity', 50), data.get('has_camera', 1))
    if success:
        return jsonify({"status": "success", "message": "Đã thêm phòng học"})
    return jsonify({"status": "error", "message": "Tên phòng đã tồn tại"}), 400

@academic_bp.route('/room/<int:room_id>', methods=['PUT'])
@admin_required
def update_room(room_id):
    data = request.json
    success = db.update_room(room_id, data['name'], data.get('capacity', 50), data.get('has_camera', 1))
    if success:
        return jsonify({"status": "success", "message": "Đã cập nhật phòng học"})
    return jsonify({"status": "error", "message": "Lỗi cập nhật"}), 400

@academic_bp.route('/room/<int:room_id>', methods=['DELETE'])
@admin_required
def delete_room(room_id):
    success = db.delete_room(room_id)
    if success:
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Lỗi xóa phòng học"}), 400

# ---- HOLIDAYS ----
@academic_bp.route('/holiday', methods=['POST'])
@admin_required
def create_holiday():
    data = request.json
    success = db.create_holiday(data['name'], data['date'], data.get('end_date'))
    if success: return jsonify({"status": "success", "message": "Đã thêm ngày nghỉ"})
    return jsonify({"status": "error", "message": "Lỗi thêm ngày nghỉ"}), 400

@academic_bp.route('/holiday/<int:h_id>', methods=['DELETE'])
@admin_required
def delete_holiday(h_id):
    db.delete_holiday(h_id)
    return jsonify({"status": "success", "message": "Đã xóa ngày nghỉ"})

# ---- SCHEDULE ----
@academic_bp.route('/class/<int:class_id>/schedules', methods=['GET'])
@admin_required
def get_class_schedules(class_id):
    schedules = db.get_class_schedules(class_id)
    return jsonify([dict(s) for s in schedules])

@academic_bp.route('/class/<int:class_id>/sessions', methods=['GET'])
@admin_required
def get_class_sessions(class_id):
    sessions = db.get_class_sessions(class_id)
    return jsonify([dict(s) for s in sessions])

@academic_bp.route('/class/<int:class_id>/schedules', methods=['POST'])
@admin_required
def save_class_schedules(class_id):
    data = request.json
    schedules = data.get('schedules', [])

    # Zero Trust Validation
    for sch in schedules:
        valid, msg = db.check_schedule_conflict(
            class_id=class_id,
            weekday=sch.get('weekday'),
            start_period_id=sch.get('start_period_id'),
            num_periods=sch.get('num_periods'),
            room_id=sch.get('room_id')
        )
        if not valid:
            return jsonify({"status": "error", "message": f"Xung đột lịch: {msg}"}), 400

    db.save_class_schedules(class_id, schedules)
    success, msg = db.generate_sessions_for_class(class_id)
    if success:
        return jsonify({"status": "success", "message": f"Lưu TKB thành công. {msg}"})
    else:
        return jsonify({"status": "error", "message": f"Lỗi sinh buổi học: {msg}"}), 500

@academic_bp.route('/class/<int:class_id>/sessions/preview', methods=['GET', 'POST'])
@admin_required
def preview_sessions(class_id):
    schedules_list = None
    if request.method == 'POST':
        data = request.json
        schedules_list = data.get('schedules', [])
    
    preview = db.preview_sessions_for_class(class_id, schedules_list)
    return jsonify(preview)

# ---- MAKEUP REQUESTS ----
@academic_bp.route('/makeup/pending', methods=['GET'])
@admin_required
def get_pending_makeups():
    requests = db.get_pending_makeup_requests()
    return jsonify([dict(r) for r in requests])

@academic_bp.route('/makeup/approve', methods=['POST'])
@admin_required
def approve_makeup():
    data = request.json
    req_id = data.get('request_id')
    status = data.get('status') # APPROVED or REJECTED
    admin_id = session.get('user_id')
    
    success = db.update_makeup_request_status(req_id, status, admin_id)
    if success:
        return jsonify({"status": "success", "message": f"Đã { 'duyệt' if status == 'APPROVED' else 'từ chối' } yêu cầu dạy bù."})
    return jsonify({"status": "error", "message": "Lỗi cập nhật yêu cầu"}), 500


# ---- EXCEL IMPORT for Academic Data ----
@academic_bp.route('/import/departments', methods=['POST'])
@admin_required
def import_departments():
    return _import_excel_generic(request, 'department', ['Tên Khoa'], lambda row: db.create_department(row['Tên Khoa']))

@academic_bp.route('/import/majors', methods=['POST'])
@admin_required
def import_majors():
    def process(row):
        dept_name = row.get('Tên Khoa', '')
        # Find or create dept
        depts = {d['name']: d['id'] for d in db.get_all_departments()}
        dept_id = depts.get(dept_name)
        if not dept_id:
            return False
        return db.create_major(row['Tên Ngành'], dept_id)
    return _import_excel_generic(request, 'major', ['Tên Ngành', 'Tên Khoa'], process)

@academic_bp.route('/import/courses', methods=['POST'])
@admin_required
def import_courses():
    def process(row):
        major_name = row.get('Tên Ngành', '')
        majors = {m['name']: m['id'] for m in db.get_majors()}
        major_id = majors.get(major_name)
        if not major_id:
            return False
        return db.create_course(row['Tên Học phần'], major_id)
    return _import_excel_generic(request, 'course', ['Tên Học phần', 'Tên Ngành'], process)

@academic_bp.route('/import/curriculum', methods=['POST'])
@admin_required
def import_curriculum():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Không tìm thấy file"}), 400
    file = request.files['file']
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({"status": "error", "message": "Chỉ chấp nhận file Excel (.xlsx)"}), 400
    
    # Save file temporarily
    upload_dir = 'data/uploads'
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)
    
    try:
        courses_data = parse_curriculum_excel(file_path)
        if not courses_data:
            return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu học phần hợp lệ trong file"}), 400
        
        count = db.import_curriculum_courses(courses_data)
        return jsonify({"status": "success", "message": f"Đã nhập/cập nhật {count} học phần từ chương trình đào tạo"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Lỗi xử lý: {str(e)}"}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def _import_excel_generic(req, entity_name, required_cols, process_fn):
    try:
        import openpyxl
    except ImportError:
        return jsonify({"status": "error", "message": "Thiếu thư viện openpyxl. Chạy: pip install openpyxl"}), 500
    
    if 'file' not in req.files:
        return jsonify({"status": "error", "message": "Không tìm thấy file"}), 400
    file = req.files['file']
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({"status": "error", "message": "Chỉ chấp nhận file Excel (.xlsx)"}), 400
    
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file)
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        
        for col in required_cols:
            if col not in headers:
                return jsonify({"status": "error", "message": f"File thiếu cột: '{col}'"}), 400
        
        count = 0
        for row_data in ws.iter_rows(min_row=2, values_only=True):
            row = dict(zip(headers, row_data))
            if any(v for v in row.values() if v):
                if process_fn(row):
                    count += 1
        
        return jsonify({"status": "success", "message": f"Đã nhập {count} {entity_name}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Lỗi xử lý file: {str(e)}"}), 500
