from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app import db
from app.core.auth_utils import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_required
def dashboard():
    page_gv = request.args.get('page_gv', 1, type=int)
    page_cls = request.args.get('page_cls', 1, type=int)
    per_page = 10
    
    lecturers = db.get_all_lecturers(page=page_gv, per_page=per_page)
    total_gv = db.get_lecturer_count()
    
    classes = db.get_all_classes(page=page_cls, per_page=per_page)
    total_cls = db.get_class_count()
    
    # Lấy dữ liệu danh mục cho Quản trị hệ thống
    depts = db.get_all_departments()
    majors = db.get_all_majors()
    courses = db.get_all_courses()
    
    pagination_gv = {
        "current": page_gv,
        "total_pages": (total_gv + per_page - 1) // per_page,
        "has_next": page_gv * per_page < total_gv,
        "has_prev": page_gv > 1
    }
    
    pagination_cls = {
        "current": page_cls,
        "total_pages": (total_cls + per_page - 1) // per_page,
        "has_next": page_cls * per_page < total_cls,
        "has_prev": page_cls > 1
    }
    
    return render_template('admin_dashboard.html', 
                           lecturers=lecturers, 
                           classes=classes,
                           depts=depts,
                           majors=majors,
                           courses=courses,
                           pag_gv=pagination_gv,
                           pag_cls=pagination_cls)

@admin_bp.route('/lecturer', methods=['POST'])
@admin_required
def add_lecturer():
    data = request.json
    success = db.create_lecturer(data['username'], data['password'], data['name'], data.get('code'))
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
    success = db.create_class(data['name'], data.get('code'))
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
    success = db.update_class(class_id, data['name'], data.get('code'))
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
    students = db.get_all_students(class_id=class_id, per_page=1000)
    return jsonify({
        "status": "success",
        "class_name": cls['name'],
        "students": [dict(s) for s in students]
    })

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
    success = db.assign_class_to_user(data['user_id'], data['class_id'])
    if success:
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Lớp học đã được gán cho GV này"}), 400

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
        for row in reader:
            s_id = row.get('MSSV')
            s_name = row.get('Họ Tên')
            s_dob = row.get('Ngày sinh', '')
            s_class = row.get('Lớp', '')
            if s_id and s_name:
                if not db.check_student_exists(s_id):
                    db.enroll_student(s_id, s_name, s_dob, s_class)
                    count += 1
        return jsonify({"status": "success", "message": f"Đã nhập thành công {count} sinh viên."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Lỗi: {str(e)}"}), 500
