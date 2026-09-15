from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app import db
from app.core.auth_utils import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_required
def dashboard():
    page_cls = request.args.get('page_cls', 1, type=int)
    per_page = 10
    
    classes = db.get_all_classes(page=page_cls, per_page=per_page)
    total_cls = db.get_class_count()
    
    # Lấy toàn bộ giảng viên phục vụ modal Phân công (không phân trang)
    all_lecturers = db.get_all_lecturers(page=1, per_page=1000)
    
    # Lấy dữ liệu danh mục cho Quản trị hệ thống
    depts = db.get_all_departments()
    majors = db.get_all_majors()
    courses = db.get_all_courses()
    
    pagination_cls = {
        "current": page_cls,
        "total_pages": (total_cls + per_page - 1) // per_page,
        "has_next": page_cls * per_page < total_cls,
        "has_prev": page_cls > 1
    }
    
    return render_template('admin_dashboard.html', 
                           classes=classes,
                           depts=depts,
                           majors=majors,
                           courses=courses,
                           all_lecturers=all_lecturers,
                           pag_cls=pagination_cls)


@admin_bp.route('/accounts', methods=['GET'])
@admin_required
def accounts_page():
    page_gv = request.args.get('page_gv', 1, type=int)
    page_std = request.args.get('page_std', 1, type=int)
    dept_std = request.args.get('dept_std', '')
    q_std = request.args.get('q_std', '')
    per_page = 10
    
    lecturers = db.get_all_lecturers(page=page_gv, per_page=per_page)
    total_gv = db.get_lecturer_count()
    
    students = db.get_all_students(
        page=page_std, 
        per_page=per_page, 
        dept_prefix=dept_std if dept_std else None, 
        search_query=q_std if q_std else None
    )
    total_std = db.get_student_count(
        dept_prefix=dept_std if dept_std else None, 
        search_query=q_std if q_std else None
    )
    
    pagination_gv = {
        "current": page_gv,
        "total_pages": (total_gv + per_page - 1) // per_page,
        "has_next": page_gv * per_page < total_gv,
        "has_prev": page_gv > 1
    }
    
    pagination_std = {
        "current": page_std,
        "total_pages": (total_std + per_page - 1) // per_page,
        "has_next": page_std * per_page < total_std,
        "has_prev": page_std > 1
    }
    
    return render_template('admin_accounts.html', 
                           lecturers=lecturers, 
                           students=students,
                           pag_gv=pagination_gv,
                           pag_std=pagination_std,
                           dept_std=dept_std,
                           q_std=q_std)


@admin_bp.route('/lecturer', methods=['POST'])
@admin_required
def add_lecturer():
    data = request.json
    password = data.get('password')
    if not password or not password.strip():
        password = getattr(Config, 'DEFAULT_LECTURER_PASSWORD', 'SmartAttendance@2026')
    success = db.create_lecturer(data['username'], password, data['name'], data.get('code'))
    if success:
        return jsonify({"status": "success", "message": "Thêm giảng viên thành công"})
    return jsonify({"status": "error", "message": "Tên đăng nhập đã tồn tại"}), 400

@admin_bp.route('/lecturer/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_lecturer(user_id):
    db.delete_lecturer(user_id)
    return jsonify({"status": "success"})

@admin_bp.route('/lecturer/<int:user_id>', methods=['PUT'])
@admin_required
def update_lecturer(user_id):
    data = request.json
    success = db.update_lecturer(user_id, data['username'], data['name'], data.get('code'), data.get('password'))
    if success:
        return jsonify({"status": "success", "message": "Cập nhật giảng viên thành công"})
    return jsonify({"status": "error", "message": "Tên đăng nhập đã tồn tại"}), 400

@admin_bp.route('/class', methods=['POST'])
@admin_required
def add_class():
    data = request.json
    success = db.create_class(data['name'], data.get('code'), data.get('course_id'))
    if success:
        return jsonify({"status": "success", "message": "Thêm lớp học thành công"})
    return jsonify({"status": "error", "message": "Lớp học đã tồn tại"}), 400

@admin_bp.route('/class/<int:class_id>', methods=['DELETE'])
@admin_required
def delete_class(class_id):
    success = db.delete_class(class_id)
    if success:
        return jsonify({"status": "success"})
    else:
        return jsonify({
            "status": "error", 
            "message": "Không thể xóa lớp đang có sinh viên. Vui lòng xóa hết sinh viên trong danh sách lớp trước."
        }), 400

@admin_bp.route('/class/<int:class_id>', methods=['PUT'])
@admin_required
def update_class(class_id):
    data = request.json
    success = db.update_class(class_id, data['name'], data.get('code'), data.get('course_id'))
    if success:
        return jsonify({"status": "success", "message": "Cập nhật lớp học thành công"})
    return jsonify({"status": "error", "message": "Lỗi cập nhật lớp học"}), 400

@admin_bp.route('/class/<int:class_id>/students', methods=['GET'])
@admin_required
def get_class_students(class_id):
    cls = db.get_class_by_id(class_id)
    if not cls:
        return jsonify({"status": "error", "message": "Lớp không tồn tại"}), 404
    # Sử dụng hàm chuẩn để lấy sinh viên theo class_id (đồng bộ với GV)
    students_raw = db.get_all_students(class_id=class_id, per_page=1000)
    students_list = []
    for s in students_raw:
        if isinstance(s, dict):
            students_list.append(s)
        elif isinstance(s, (list, tuple)):
            students_list.append({
                "id": s[0],
                "name": s[1] if len(s) > 1 else "",
                "dob": s[2] if len(s) > 2 else "",
                "student_class": s[3] if len(s) > 3 else ""
            })
    return jsonify({
        "status": "success",
        "class_id": class_id,
        "class_name": cls['name'],
        "students": students_list
    })

@admin_bp.route('/class/<int:class_id>/student/<string:student_id>', methods=['DELETE'])
@admin_required
def remove_student_from_class(class_id, student_id):
    db.remove_student_from_class(class_id, student_id)
    return jsonify({"status": "success", "message": "Đã loại sinh viên khỏi lớp học phần"})

@admin_bp.route('/student', methods=['POST'])
@admin_required
def add_student():
    data = request.json
    db.enroll_student(data['student_id'], data['name'], data['dob'], data['student_class'])
    return jsonify({"status": "success", "message": "Thêm sinh viên thành công"})

@admin_bp.route('/student/<string:student_id>', methods=['DELETE'])
@admin_required
def delete_student(student_id):
    db.delete_student(student_id)
    return jsonify({"status": "success"})

@admin_bp.route('/student/<string:student_id>', methods=['PUT'])
@admin_required
def update_student(student_id):
    data = request.json
    db.update_student_info(student_id, data['name'], data['dob'], data['student_class'])
    return jsonify({"status": "success", "message": "Cập nhật sinh viên thành công"})


# ---- ASSIGNMENT ROUTES ----
@admin_bp.route('/lecturer/<int:user_id>/classes', methods=['GET'])
@admin_required
def get_lecturer_classes(user_id):
    assigned = db.get_user_classes(user_id)
    return jsonify({"status": "success", "classes": assigned})

@admin_bp.route('/lecturer/assign', methods=['POST'])
@admin_required
def assign_class():
    data = request.json
    class_id = data.get('class_id')
    user_id = data.get('user_id')

    if not class_id:
        return jsonify({"status": "error", "message": "Thiếu mã lớp học!"}), 400

    # Xóa phân công cũ trước khi cập nhật phân công mới
    db.remove_all_lecturers_from_class(class_id)

    if user_id:
        success = db.assign_class_to_user(int(user_id), int(class_id))
        if success:
            return jsonify({"status": "success", "message": "Cập nhật phân công thành công!"})
        return jsonify({"status": "error", "message": "Lỗi gán giảng viên"}), 400
    else:
        return jsonify({"status": "success", "message": "Đã hủy phân công giảng viên!"})

@admin_bp.route('/lecturer/unassign', methods=['POST'])
@admin_required
def unassign_class():
    data = request.json
    db.remove_class_from_user(data['user_id'], data['class_id'])
    return jsonify({"status": "success"})

# ---- SETTINGS ROUTES ----
@admin_bp.route('/settings', methods=['GET'])
@admin_required
def settings_page():
    settings = db.get_settings()
    return render_template('admin_settings.html', settings=settings)

@admin_bp.route('/settings/update', methods=['POST'])
@admin_required
def update_settings():
    from app import ai_engine
    data = request.form
    for key, value in data.items():
        db.update_setting(key, value)
    ai_engine.refresh_settings()
    return jsonify({"status": "success", "message": "Cấu hình đã được cập nhật"})

@admin_bp.route('/export/students', methods=['GET'])
@admin_required
def export_students():
    import csv
    from io import StringIO
    from flask import make_response
    students = db.get_all_students(per_page=10000)
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['MSSV', 'Họ Tên', 'Ngày sinh', 'Lớp', 'Ngày đăng ký'])
    for s in students:
        cw.writerow([s[0], s[1], s[2], s[3], s[5]])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=students_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@admin_bp.route('/import/students', methods=['POST'])
@admin_required
def import_students():
    import csv
    import unicodedata
    from io import TextIOWrapper
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Không tìm thấy file"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "Chưa chọn file"}), 400
    try:
        csv_file = TextIOWrapper(file, encoding='utf-8')
        reader = csv.DictReader(csv_file)
        count = 0
        
        def clean_val(val):
            if val is None:
                return ""
            return unicodedata.normalize('NFC', str(val)).strip()

        for row in reader:
            normalized_row = {clean_val(k): clean_val(v) for k, v in row.items() if k is not None}
            
            s_id = normalized_row.get('MSSV') or normalized_row.get('Mã SV') or normalized_row.get('Mã số sinh viên')
            s_name = normalized_row.get('Họ Tên') or normalized_row.get('Họ và Tên') or normalized_row.get('Họ lót Tên')
            s_dob = normalized_row.get('Ngày sinh', '')
            s_class = normalized_row.get('Lớp', '') or normalized_row.get('Lớp SV')
            
            if s_id and s_name:
                # Skip header template rows
                if s_id.lower() in ['mssv', 'mã sv', 'ma sv', 'mã số sinh viên', 'ma so sinh vien']:
                    continue
                if s_name.lower() in ['họ tên', 'ho ten', 'họ và tên', 'ho va ten', 'họ lót tên', 'ho lot ten']:
                    continue
                    
                if not db.check_student_exists(s_id):
                    db.enroll_student(s_id, s_name, s_dob, s_class)
                    count += 1
        return jsonify({"status": "success", "message": f"Đã nhập thành công {count} sinh viên."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Lỗi: {str(e)}"}), 500

@admin_bp.route('/import/classes', methods=['POST'])
@admin_required
def import_classes():
    from app.utils.excel_parser import parse_classes_excel
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Không tìm thấy file"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "Chưa chọn file"}), 400
    
    # Save file temporarily
    upload_dir = 'data/uploads'
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)
    
    try:
        classes_data = parse_classes_excel(file_path)
        if not classes_data:
            return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu lớp học hợp lệ trong file"}), 400
        
        count = db.import_classes(classes_data)
        return jsonify({"status": "success", "message": f"Đã nhập/cập nhật {count} lớp học phần"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Lỗi xử lý: {str(e)}"}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
