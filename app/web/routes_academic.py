from flask import Blueprint, render_template, request, jsonify
from app import db
from app.core.auth_utils import admin_required

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
    return render_template('admin_academic.html',
                           depts=depts, majors=majors, courses=courses,
                           semesters=semesters, classes=classes,
                           rooms=rooms, periods=periods)

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
    success = db.create_course(data['name'], data['major_id'])
    if success:
        return jsonify({"status": "success", "message": "Đã thêm Học phần"})
    return jsonify({"status": "error", "message": "Tên Học phần đã tồn tại"}), 400

@academic_bp.route('/course/<int:course_id>', methods=['PUT'])
@admin_required
def update_course(course_id):
    data = request.json
    success = db.update_course(course_id, data['name'], data['major_id'])
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

# ---- SCHEDULE ----
@academic_bp.route('/class/<int:class_id>/schedules', methods=['GET'])
@admin_required
def get_class_schedules(class_id):
    schedules = db.get_class_schedules(class_id)
    return jsonify([dict(s) for s in schedules])

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
        return jsonify({"status": "error", "message": f"Lưu TKB nhưng lỗi sinh buổi học: {msg}"}), 500

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
