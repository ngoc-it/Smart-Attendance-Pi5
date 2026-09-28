import sqlite3
import os
from datetime import datetime
from app.core.firebase_sync import sync_student_account, delete_student_account

class ClassStudentDBMixin:
    # ---- CLASSES CRUD ----
    def get_all_classes(self, page=1, per_page=10):
        """Lấy danh sách toàn bộ các lớp học phần trong hệ thống (có phân trang) kèm giảng viên phân công."""
        offset = (page - 1) * per_page
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.id, c.name, c.code, c.course_id, crs.name as course_name,
                (SELECT COUNT(*) FROM class_students cs WHERE cs.class_id = c.id) as student_count,
                (SELECT GROUP_CONCAT(COALESCE(NULLIF(u.name, ''), u.username), ', ') FROM user_classes uc JOIN users u ON uc.user_id = u.id WHERE uc.class_id = c.id) as lecturer_name,
                (SELECT GROUP_CONCAT(uc.user_id, ',') FROM user_classes uc WHERE uc.class_id = c.id) as lecturer_id
                FROM classes c 
                LEFT JOIN courses crs ON c.course_id = crs.id
                ORDER BY c.name ASC 
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            return cursor.fetchall()

    def get_class_count(self):
        """Đếm tổng số lớp học phần hiện có."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM classes")
            return cursor.fetchone()[0]

    def create_class(self, name, code=None, course_id=None):
        """Tạo một lớp học phần mới và liên kết với mã học phần (nếu có)."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO classes (name, code, course_id) VALUES (?, ?, ?)", (name, code, course_id))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def update_class(self, class_id, name, code, course_id=None):
        """Cập nhật thông tin cơ bản của lớp học phần."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE classes SET name = ?, code = ?, course_id = ? WHERE id = ?", (name, code, course_id, class_id))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_class_by_id(self, class_id):
        """Lấy thông tin chi tiết của một lớp học phần theo ID."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
            return cursor.fetchone()

    def get_students_by_class_identifier(self, name, code=None):
        """Tìm kiếm danh sách sinh viên dựa trên tên lớp hoặc mã lớp (hỗ trợ migration)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # Tìm sinh viên khớp với Tên hoặc Mã lớp
            cursor.execute("SELECT id, name, dob, student_class FROM students WHERE student_class = ? OR (student_class = ? AND ? IS NOT NULL)", 
                           (name, code, code))
            return cursor.fetchall()

    def import_classes(self, classes_data):
        """Nhập dữ liệu các lớp học phần hàng loạt và tự động liên kết với mã học phần tương ứng."""
        count = 0
        with self._get_conn() as conn:
            cursor = conn.cursor()
            for c in classes_data:
                try:
                    course_id = None
                    if c.get('course_code'):
                        cursor.execute("SELECT id FROM courses WHERE code = ?", (c['course_code'],))
                        row = cursor.fetchone()
                        if row: course_id = row[0]
                    
                    # Check if class exists by code (if provided) or name
                    if c['code']:
                        cursor.execute("SELECT id FROM classes WHERE code = ?", (c['code'],))
                    else:
                        cursor.execute("SELECT id FROM classes WHERE name = ?", (c['name'],))
                    
                    existing = cursor.fetchone()
                    if existing:
                        cursor.execute("UPDATE classes SET name = ?, course_id = ? WHERE id = ?", 
                                       (c['name'], course_id, existing[0]))
                    else:
                        cursor.execute("INSERT INTO classes (name, code, course_id) VALUES (?, ?, ?)", 
                                       (c['name'], c['code'], course_id))
                    count += 1
                except Exception as e:
                    print(f"Error importing class {c['name']}: {e}")
            conn.commit()
        return count

    def delete_class(self, class_id):
        """Xóa hoàn toàn một lớp học phần và các dữ liệu liên quan (Lịch học, phân công giảng viên)."""
        if self.has_students(class_id):
            return False
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM classes WHERE id = ?", (class_id,))
            cursor.execute("DELETE FROM user_classes WHERE class_id = ?", (class_id,))
            cursor.execute("DELETE FROM schedules WHERE class_id = ?", (class_id,))
            conn.commit()
        return True

    def remove_all_students_from_class(self, class_id):
        """Xóa toàn bộ danh sách sinh viên khỏi một lớp học phần cụ thể."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM class_students WHERE class_id = ?", (class_id,))
            conn.commit()

    def remove_student_from_class(self, class_id, student_id):
        """Loại bỏ một sinh viên khỏi một lớp học phần cụ thể (không làm xóa sinh viên khỏi hệ thống)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM class_students WHERE class_id = ? AND student_id = ?", (class_id, student_id))
            conn.commit()

    def has_students(self, class_id):
        """Kiểm tra xem lớp học phần hiện tại có sinh viên nào đang theo học hay không."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM class_students WHERE class_id = ? LIMIT 1", (class_id,))
            return cursor.fetchone() is not None

    def get_student_name(self, student_id):
        """Lấy họ tên của sinh viên dựa trên mã số sinh viên."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM students WHERE id = ?", (student_id,))
            row = cursor.fetchone()
            return row[0] if row else "Unknown"

    def check_student_exists(self, student_id):
        """Kiểm tra xem mã số sinh viên đã tồn tại trong cơ sở dữ liệu hệ thống chưa."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM students WHERE id = ?", (student_id,))
            return cursor.fetchone() is not None

    def get_face_registration_status(self, student_ids):
        """Kiểm tra trạng thái đăng ký khuôn mặt của danh sách sinh viên (xem đã có file embedding chưa)."""
        from config import Config
        status = {}
        for s_id in student_ids:
            file_path = os.path.join(Config.EMBEDDINGS_DIR, f"{s_id}.npy")
            status[s_id] = os.path.exists(file_path)
        return status

    def enroll_student(self, student_id, name, dob, student_class, course_class_id=None):
        """Đăng ký thông tin sinh viên mới và tùy chọn liên kết vào một lớp học phần cụ thể."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # 1. Cap nhat thong tin sinh vien (lop sinh vien co dinh)
            cursor.execute("INSERT OR REPLACE INTO students (id, name, dob, student_class, status, last_seen) VALUES (?, ?, ?, ?, 'REGISTERED', ?)", 
                           (student_id, name, dob, student_class, now))
            
            # 2. Neu co lop hoc phan, lien ket vao class_students
            if course_class_id:
                cursor.execute("INSERT OR IGNORE INTO class_students (class_id, student_id) VALUES (?, ?)", 
                               (course_class_id, student_id))
            conn.commit()
        
        # 3. Đồng bộ lên Firebase Firestore
        sync_student_account(student_id, name, dob, student_class)


    def get_student_by_id(self, student_id):
        """Lấy toàn bộ thông tin chi tiết của một sinh viên dựa trên ID (MSSV)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
            return cursor.fetchone()

    def get_all_students(self, user_id=None, class_id=None, page=1, per_page=10, dept_prefix=None, search_query=None): 
        """Lấy danh sách sinh viên kèm trạng thái điểm danh thực tế theo Ca học đang diễn ra."""
        offset = (page - 1) * per_page
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 1. Tìm ca học đang diễn ra của lớp này
            s_start, s_end = "00:00:00", "23:59:59"
            if class_id:
                cursor.execute("""
                    SELECT start_time, end_time FROM class_sessions 
                    WHERE class_id = ? AND session_date = DATE('now', 'localtime') 
                    ORDER BY 
                        CASE 
                            WHEN time('now', 'localtime') BETWEEN start_time AND end_time THEN 0
                            WHEN time('now', 'localtime') BETWEEN time(start_time, '-30 minutes') AND start_time THEN 1
                            WHEN time('now', 'localtime') BETWEEN end_time AND time(end_time, '+30 minutes') THEN 2
                            ELSE 3 
                        END ASC,
                        ABS(strftime('%s', time('now', 'localtime')) - strftime('%s', start_time)) ASC
                    LIMIT 1
                """, (class_id,))
                session_now = cursor.fetchone()
                if session_now:
                    s_start, s_end = session_now[0], session_now[1]
                else:
                    # Nếu không có ca học, ta ép giờ về một khoảng không thể có log
                    s_start, s_end = "23:59:58", "23:59:59" 

            # 2. Truy vấn JOIN với attendance_logs
            if class_id:
                cursor.execute("""
                    SELECT s.id, s.name, s.dob, s.student_class, al.status, s.last_seen
                    FROM students s
                    JOIN class_students cs ON s.id = cs.student_id
                    LEFT JOIN attendance_logs al ON s.id = al.student_id 
                        AND al.class_id = ?
                        AND al.date = DATE('now', 'localtime')
                        AND al.time BETWEEN ? AND ?
                    WHERE cs.class_id = ?
                    ORDER BY s.id ASC
                    LIMIT ? OFFSET ?
                """, (class_id, s_start, s_end, class_id, per_page, offset))
            else:
                query = "SELECT * FROM students WHERE 1=1"
                params = []
                if dept_prefix:
                    query += " AND (student_class LIKE ?)"
                    params.append(f"{dept_prefix}%")
                if search_query:
                    query += " AND (id LIKE ? OR name LIKE ? OR student_class LIKE ?)"
                    params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
                query += " ORDER BY id ASC LIMIT ? OFFSET ?"
                params.extend([per_page, offset])
                cursor.execute(query, tuple(params))
                
            rows = cursor.fetchall()
            return [list(row) for row in rows]

    def get_all_students_legacy(self, user_id=None, class_id=None, page=1, per_page=10, dept_prefix=None, search_query=None): 
        offset = (page - 1) * per_page
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            if class_id:
                # Lay sinh vien cua mot lop hoc phan cu the
                cursor.execute("""
                    SELECT s.* FROM students s
                    JOIN class_students cs ON s.id = cs.student_id
                    WHERE cs.class_id = ?
                    ORDER BY GET_TEN(s.name) ASC, s.name ASC
                    LIMIT ? OFFSET ?
                """, (class_id, per_page, offset))
            elif user_id:
                # Lay tat ca sinh vien thuoc cac lop cua mot giang vien
                cursor.execute("""
                    SELECT DISTINCT s.* FROM students s
                    JOIN class_students cs ON s.id = cs.student_id
                    JOIN user_classes uc ON cs.class_id = uc.class_id
                    WHERE uc.user_id = ?
                    ORDER BY GET_TEN(s.name) ASC, s.name ASC
                    LIMIT ? OFFSET ?
                """, (user_id, per_page, offset))
            else:
                query = "SELECT * FROM students WHERE 1=1"
                params = []
                if dept_prefix:
                    query += " AND (student_class LIKE ?)"
                    params.append(f"{dept_prefix}%")
                if search_query:
                    query += " AND (id LIKE ? OR name LIKE ? OR student_class LIKE ?)"
                    params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
                query += " ORDER BY GET_TEN(name) ASC, name ASC LIMIT ? OFFSET ?"
                params.extend([per_page, offset])
                cursor.execute(query, tuple(params))
            return cursor.fetchall()

    def get_student_count(self, user_id=None, class_id=None, dept_prefix=None, search_query=None):
        """Đếm tổng số lượng sinh viên dựa trên các tiêu chí lọc (Giảng viên, Lớp hoặc toàn hệ thống)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            if class_id:
                cursor.execute("SELECT COUNT(*) FROM class_students WHERE class_id = ?", (class_id,))
            elif user_id:
                cursor.execute("""
                    SELECT COUNT(DISTINCT s.id) FROM students s
                    JOIN class_students cs ON s.id = cs.student_id
                    JOIN user_classes uc ON cs.class_id = uc.class_id
                    WHERE uc.user_id = ?
                """, (user_id,))
            else:
                query = "SELECT COUNT(*) FROM students WHERE 1=1"
                params = []
                if dept_prefix:
                    query += " AND (student_class LIKE ?)"
                    params.append(f"{dept_prefix}%")
                if search_query:
                    query += " AND (id LIKE ? OR name LIKE ? OR student_class LIKE ?)"
                    params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
                cursor.execute(query, tuple(params))
            return cursor.fetchone()[0]

    def delete_student(self, student_id):
        """Thực hiện xóa mềm (Soft Delete) sinh viên: Chuyển is_active = 0 và loại khỏi lớp học phần, GIỮ NGUYÊN lịch sử điểm danh."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE students SET is_active = 0 WHERE id = ?", (student_id,))
            cursor.execute("DELETE FROM class_students WHERE student_id = ?", (student_id,))
            conn.commit()
        # Đồng bộ cập nhật trạng thái INACTIVE lên Firebase Firestore
        sync_student_account(student_id, self.get_student_name(student_id), "", "", status="INACTIVE")

    def restore_student(self, student_id):
        """Kích hoạt lại tài khoản sinh viên đã bị xóa mềm (is_active = 1)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE students SET is_active = 1 WHERE id = ?", (student_id,))
            conn.commit()
        sync_student_account(student_id, self.get_student_name(student_id), "", "", status="ACTIVE")

    def update_student_info(self, student_id, name, dob, student_class):
        """Cập nhật thông tin định danh cơ bản của sinh viên."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE students 
                SET name = ?, dob = ?, student_class = ?
                WHERE id = ?
            """, (name, dob, student_class, student_id))
            conn.commit()
        # Đồng bộ cập nhật lên Firebase Firestore
        sync_student_account(student_id, name, dob, student_class)

