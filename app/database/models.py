import sqlite3
from datetime import datetime
import os
import hashlib

class AttendanceDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        # Hàm lấy tên (chữ cuối cùng) để sắp xếp A-Z theo tên tiếng Việt
        def get_vietnamese_name(full_name):
            if not full_name: return ""
            parts = str(full_name).strip().split()
            return parts[-1] if parts else ""
        conn.create_function("GET_TEN", 1, get_vietnamese_name)
        return conn

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS students 
                (id TEXT PRIMARY KEY, name TEXT, dob TEXT, student_class TEXT, status TEXT DEFAULT 'OUT', last_seen TEXT)''')
            
            # Kiểm tra và thêm cột nếu schema cũ chưa có
            cursor.execute("PRAGMA table_info(students)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'dob' not in columns:
                cursor.execute("ALTER TABLE students ADD COLUMN dob TEXT")
            if 'student_class' not in columns:
                cursor.execute("ALTER TABLE students ADD COLUMN student_class TEXT")

            cursor.execute('''CREATE TABLE IF NOT EXISTS logs 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, action TEXT, time TEXT, image_path TEXT)''')
                
            cursor.execute("PRAGMA table_info(logs)")
            log_columns = [col[1] for col in cursor.fetchall()]
            if 'image_path' not in log_columns:
                cursor.execute("ALTER TABLE logs ADD COLUMN image_path TEXT")

            # Bang classes
            cursor.execute('''CREATE TABLE IF NOT EXISTS classes 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, code TEXT, course_id INTEGER)''')
            
            cursor.execute("PRAGMA table_info(classes)")
            class_columns = [col[1] for col in cursor.fetchall()]
            if 'course_id' not in class_columns:
                cursor.execute("ALTER TABLE classes ADD COLUMN course_id INTEGER")
            if 'code' not in class_columns:
                cursor.execute("ALTER TABLE classes ADD COLUMN code TEXT")
            
            # Xóa UNIQUE constraint cũ trên cột name nếu có (SQLite không hỗ trợ DROP CONSTRAINT trực tiếp)
            # Tuy nhiên, trong CREATE TABLE ở trên ta đã bỏ UNIQUE rồi. 
            # Nếu bảng đã tồn tại với UNIQUE(name), ta có thể cần migration phức tạp hơn, 
            # nhưng ở đây ta chấp nhận để code làm nhiệm vụ phân biệt.

            # Bang users
            cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, name TEXT, code TEXT)''')
            
            cursor.execute("PRAGMA table_info(users)")
            user_cols = [col[1] for col in cursor.fetchall()]
            if 'code' not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN code TEXT")

            # Bang user_classes (Liên kết GV với lớp học)
            cursor.execute('''CREATE TABLE IF NOT EXISTS user_classes 
                (user_id INTEGER, class_id INTEGER, PRIMARY KEY (user_id, class_id))''')
                
            # Bang settings (Cau hinh he thong)
            cursor.execute('''CREATE TABLE IF NOT EXISTS settings 
                (key TEXT PRIMARY KEY, value TEXT)''')
                
            # Bang departments (Khoa)
            cursor.execute('''CREATE TABLE IF NOT EXISTS departments 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
                
            # Bang majors (Ngành)
            cursor.execute('''CREATE TABLE IF NOT EXISTS majors 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, department_id INTEGER,
                 FOREIGN KEY(department_id) REFERENCES departments(id))''')
                 
            # Bang courses (Học phần)
            cursor.execute('''CREATE TABLE IF NOT EXISTS courses 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, major_id INTEGER,
                 FOREIGN KEY(major_id) REFERENCES majors(id))''')

            # Bang schedules (Thời khóa biểu)
            cursor.execute('''CREATE TABLE IF NOT EXISTS schedules 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, class_id INTEGER, 
                 weekday INTEGER, start_time TEXT, end_time TEXT, room TEXT,
                 FOREIGN KEY(class_id) REFERENCES classes(id))''')

            # Bang leave_requests (Đơn xin nghỉ phép)
            cursor.execute('''CREATE TABLE IF NOT EXISTS leave_requests 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, class_id INTEGER, 
                 reason TEXT, date TEXT, status TEXT DEFAULT 'PENDING',
                 FOREIGN KEY(student_id) REFERENCES students(id),
                 FOREIGN KEY(class_id) REFERENCES classes(id))''')

            # Bang class_students (Liên kết sinh viên với lớp học phần)
            cursor.execute('''CREATE TABLE IF NOT EXISTS class_students 
                (class_id INTEGER, student_id TEXT, PRIMARY KEY (class_id, student_id),
                 FOREIGN KEY(class_id) REFERENCES classes(id),
                 FOREIGN KEY(student_id) REFERENCES students(id))''')

            # MIGRATION: Lien ket sinh vien cu vao lop hoc phan neu ten trung khop
            cursor.execute("""
                INSERT OR IGNORE INTO class_students (class_id, student_id)
                SELECT c.id, s.id FROM students s
                JOIN classes c ON s.student_class = c.name
            """)

            # Tu dong tao tai khoan admin neu chua co
            cursor.execute("SELECT * FROM users WHERE username = 'admin'")
            if not cursor.fetchone():
                hashed_pw = hashlib.sha256("ngoc123".encode()).hexdigest()
                cursor.execute("INSERT INTO users (username, password, role, name) VALUES (?, ?, 'admin', 'Super Admin')", ('admin', hashed_pw))
            
            # Nap cau hinh mac dinh
            default_settings = {
                "match_threshold": "0.65",
                "late_limit_minutes": "15",
                "absent_limit_minutes": "30",
                "school_name": "Smart Attendance System",
                "camera_status": "online"
            }
            for k, v in default_settings.items():
                cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
                
            conn.commit()

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_login(self, username, password, role):
        hashed_pw = self.hash_password(password)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, role FROM users WHERE username = ? AND password = ? AND role = ?", 
                           (username, hashed_pw, role))
            return cursor.fetchone()

    # ---- USERS CRUD ----
    def get_all_lecturers(self, page=1, per_page=10):
        offset = (page - 1) * per_page
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, name, code FROM users WHERE role = 'lecturer' ORDER BY GET_TEN(name) ASC, name ASC LIMIT ? OFFSET ?", 
                           (per_page, offset))
            return cursor.fetchall()

    def get_lecturer_count(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'lecturer'")
            return cursor.fetchone()[0]

    def create_lecturer(self, username, password, name, code=None):
        hashed_pw = self.hash_password(password)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password, role, name, code) VALUES (?, ?, 'lecturer', ?, ?)", 
                               (username, hashed_pw, name, code))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False # Username da ton tai

    def delete_lecturer(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ? AND role = 'lecturer'", (user_id,))
            cursor.execute("DELETE FROM user_classes WHERE user_id = ?", (user_id,))
            conn.commit()

    def update_lecturer(self, user_id, username, name, code, password=None):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if password:
                    hashed_pw = self.hash_password(password)
                    cursor.execute("""
                        UPDATE users SET username = ?, name = ?, code = ?, password = ?
                        WHERE id = ? AND role = 'lecturer'
                    """, (username, name, code, hashed_pw, user_id))
                else:
                    cursor.execute("""
                        UPDATE users SET username = ?, name = ?, code = ?
                        WHERE id = ? AND role = 'lecturer'
                    """, (username, name, code, user_id))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    # ---- USER-CLASS ASSIGNMENT ----
    def get_user_classes(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.id, c.name, c.code
                FROM classes c
                JOIN user_classes uc ON c.id = uc.class_id
                WHERE uc.user_id = ?
            """, (user_id,))
            return cursor.fetchall()

    def assign_class_to_user(self, user_id, class_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO user_classes (user_id, class_id) VALUES (?, ?)", (user_id, class_id))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def remove_class_from_user(self, user_id, class_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_classes WHERE user_id = ? AND class_id = ?", (user_id, class_id))
            conn.commit()

    # ---- SYSTEM SETTINGS ----
    def get_settings(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            return dict(cursor.fetchall())

    def update_setting(self, key, value):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE settings SET value = ? WHERE key = ?", (str(value), key))
            conn.commit()
            
    def get_setting(self, key, default=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    # ---- CLASSES CRUD ----
    def get_all_classes(self, page=1, per_page=10):
        offset = (page - 1) * per_page
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, code FROM classes ORDER BY name ASC LIMIT ? OFFSET ?", 
                           (per_page, offset))
            return cursor.fetchall()

    def get_class_count(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM classes")
            return cursor.fetchone()[0]

    def create_class(self, name, code=None, course_id=None):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO classes (name, code, course_id) VALUES (?, ?, ?)", (name, code, course_id))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def update_class(self, class_id, name, code):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE classes SET name = ?, code = ? WHERE id = ?", (name, code, class_id))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    # ---- ACADEMIC CRUD (Departments, Majors, Courses) ----
    def get_all_departments(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM departments")
            return cursor.fetchall()
            
    def create_department(self, name):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO departments (name) VALUES (?)", (name,))
                conn.commit()
                return True
        except: return False

    def get_majors(self, department_id=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if department_id:
                cursor.execute("SELECT * FROM majors WHERE department_id = ?", (department_id,))
            else:
                cursor.execute("SELECT * FROM majors")
            return cursor.fetchall()

    def create_major(self, name, department_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO majors (name, department_id) VALUES (?, ?)", (name, department_id))
                conn.commit()
                return True
        except: return False

    def get_courses(self, major_id=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if major_id:
                cursor.execute("SELECT * FROM courses WHERE major_id = ?", (major_id,))
            else:
                cursor.execute("SELECT * FROM courses")
            return cursor.fetchall()

    def create_course(self, name, major_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO courses (name, major_id) VALUES (?, ?)", (name, major_id))
                conn.commit()
                return True
        except: return False

    # ---- LECTURER SPECIFIC ----
    def get_user_schedule(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, c.name as class_name, c.code as class_code
                FROM schedules s 
                JOIN user_classes uc ON s.class_id = uc.class_id
                JOIN classes c ON s.class_id = c.id
                WHERE uc.user_id = ?
                ORDER BY s.weekday, s.start_time
            """, (user_id,))
            return cursor.fetchall()

    def get_leave_requests(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT lr.*, s.name as student_name, c.name as class_name
                FROM leave_requests lr
                JOIN students s ON lr.student_id = s.id
                JOIN classes c ON lr.class_id = c.id
                JOIN user_classes uc ON c.id = uc.class_id
                WHERE uc.user_id = ?
                ORDER BY lr.date DESC
            """, (user_id,))
            return cursor.fetchall()

    def update_leave_status(self, request_id, status):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE leave_requests SET status = ? WHERE id = ?", (status, request_id))
            conn.commit()

    # ---- SCHEDULE CRUD ----
    def get_schedules(self, class_id=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if class_id:
                cursor.execute("SELECT * FROM schedules WHERE class_id = ?", (class_id,))
            else:
                cursor.execute("""
                    SELECT s.*, c.name as class_name 
                    FROM schedules s JOIN classes c ON s.class_id = c.id
                """)
            return cursor.fetchall()

    def create_schedule(self, class_id, weekday, start_time, end_time, room):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedules (class_id, weekday, start_time, end_time, room)
                VALUES (?, ?, ?, ?, ?)
            """, (class_id, weekday, start_time, end_time, room))
            conn.commit()

    def delete_class(self, class_id):
        if self.has_students(class_id):
            return False
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM classes WHERE id = ?", (class_id,))
            cursor.execute("DELETE FROM user_classes WHERE class_id = ?", (class_id,))
            cursor.execute("DELETE FROM schedules WHERE class_id = ?", (class_id,))
            conn.commit()
        return True

    def remove_all_students_from_class(self, class_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM class_students WHERE class_id = ?", (class_id,))
            conn.commit()

    def has_students(self, class_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM class_students WHERE class_id = ? LIMIT 1", (class_id,))
            return cursor.fetchone() is not None

    def get_student_name(self, student_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM students WHERE id = ?", (student_id,))
            row = cursor.fetchone()
            return row[0] if row else "Unknown"

    def check_student_exists(self, student_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM students WHERE id = ?", (student_id,))
            return cursor.fetchone() is not None

    def get_lecturer_classes_names(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.name, c.code
                FROM classes c
                JOIN user_classes uc ON c.id = uc.class_id
                WHERE uc.user_id = ?
            """, (user_id,))
            return [f"{row[1]} - {row[0]}" if row[1] else row[0] for row in cursor.fetchall()]

    def get_face_registration_status(self, student_ids):
        """Kiểm tra xem sinh viên đã đăng ký khuôn mặt (có file embedding) chưa"""
        from config import Config
        status = {}
        for s_id in student_ids:
            file_path = os.path.join(Config.EMBEDDINGS_DIR, f"{s_id}.npy")
            status[s_id] = os.path.exists(file_path)
        return status

    def enroll_student(self, student_id, name, dob, student_class, course_class_id=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 1. Cap nhat thong tin sinh vien (lop sinh vien co dinh)
            cursor.execute("INSERT OR REPLACE INTO students (id, name, dob, student_class, status, last_seen) VALUES (?, ?, ?, ?, 'REGISTERED', ?)", 
                           (student_id, name, dob, student_class, now))
            
            # 2. Neu co lop hoc phan, lien ket vao class_students
            if course_class_id:
                cursor.execute("INSERT OR IGNORE INTO class_students (class_id, student_id) VALUES (?, ?)", 
                               (course_class_id, student_id))
            conn.commit()

    def get_all_students(self, user_id=None, class_id=None, page=1, per_page=10): 
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
                cursor.execute("SELECT * FROM students ORDER BY GET_TEN(name) ASC, name ASC LIMIT ? OFFSET ?", (per_page, offset))
            return cursor.fetchall()

    def get_student_count(self, user_id=None, class_id=None):
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
                cursor.execute("SELECT COUNT(*) FROM students")
            return cursor.fetchone()[0]

    def delete_student(self, student_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
            cursor.execute("DELETE FROM logs WHERE student_id = ?", (student_id,))
            conn.commit()

    def update_student_info(self, student_id, name, dob, student_class):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE students 
                SET name = ?, dob = ?, student_class = ?
                WHERE id = ?
            """, (name, dob, student_class, student_id))
            conn.commit()

    def update_status(self, student_id, name, action, image_path=None): # Thụt lề 4 space
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Lấy thông tin hiện tại
            cursor.execute("SELECT dob, student_class FROM students WHERE id = ?", (student_id,))
            row = cursor.fetchone()
            dob, student_class = row if row else ("", "")
            
            cursor.execute("INSERT OR REPLACE INTO students (id, name, dob, student_class, status, last_seen) VALUES (?, ?, ?, ?, ?, ?)", 
                           (student_id, name, dob, student_class, action, now))
            cursor.execute("INSERT INTO logs (student_id, action, time, image_path) VALUES (?, ?, ?, ?)", 
                           (student_id, action, now, image_path))
            conn.commit()

    def get_daily_attendance(self, date_str=None, user_id=None):
        """Lấy danh sách log điểm danh trong ngày"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        params = [date_str]
        filter_clause = ""
        if user_id:
            filter_clause = "AND s.student_class IN (SELECT c.name FROM classes c JOIN user_classes uc ON c.id = uc.class_id WHERE uc.user_id = ?)"
            params.append(user_id)

        query = f"""
            SELECT l.time, s.name, s.id, l.action, l.image_path, s.student_class
            FROM logs l
            JOIN students s ON l.student_id = s.id
            WHERE date(l.time) = date(?) {filter_clause}
            ORDER BY l.time DESC
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
            
    def get_attendance_stats(self, date_str=None, user_id=None):
        """Thống kê số lượng sinh viên đi học/vắng mặt"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if user_id:
                # Tổng số sinh viên thuộc các lớp của GV
                cursor.execute("""
                    SELECT COUNT(id) FROM students 
                    WHERE student_class IN (SELECT c.name FROM classes c JOIN user_classes uc ON c.id = uc.class_id WHERE uc.user_id = ?)
                """, (user_id,))
                total = cursor.fetchone()[0]
                
                # Số sinh viên đã điểm danh IN trong ngày (thuộc lớp của GV)
                cursor.execute("""
                    SELECT COUNT(DISTINCT l.student_id) FROM logs l
                    JOIN students s ON l.student_id = s.id
                    WHERE l.action = 'IN' AND date(l.time) = date(?)
                    AND s.student_class IN (SELECT c.name FROM classes c JOIN user_classes uc ON c.id = uc.class_id WHERE uc.user_id = ?)
                """, (date_str, user_id))
                present = cursor.fetchone()[0]
            else:
                # Tổng số sinh viên
                cursor.execute("SELECT COUNT(id) FROM students")
                total = cursor.fetchone()[0]
                
                # Số sinh viên đã điểm danh IN trong ngày (distinct)
                cursor.execute("""
                    SELECT COUNT(DISTINCT student_id) FROM logs 
                    WHERE action = 'IN' AND date(time) = date(?)
                """, (date_str,))
                present = cursor.fetchone()[0]
            
            return {
                "total": total,
                "present": present,
                "absent": total - present
            }

    def get_detailed_attendance(self, date_str, class_name):
        """Lấy ma trận điểm danh chi tiết của tất cả sinh viên trong lớp"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 1. Lấy tất cả sinh viên trong lớp này
            # Kiểm tra xem class_name là ID hay Tên
            if str(class_name).isdigit():
                cursor.execute("""
                    SELECT s.id, s.name FROM students s
                    JOIN class_students cs ON s.id = cs.student_id
                    WHERE cs.class_id = ?
                    ORDER BY GET_TEN(s.name) ASC, s.name ASC
                """, (class_name,))
            else:
                cursor.execute("""
                    SELECT s.id, s.name FROM students s
                    JOIN class_students cs ON s.id = cs.student_id
                    JOIN classes c ON cs.class_id = c.id
                    WHERE c.name = ?
                    ORDER BY GET_TEN(s.name) ASC, s.name ASC
                """, (class_name,))
            students = cursor.fetchall()
            
            # 2. Lấy tất cả log trong ngày đó cho lớp này
            if str(class_name).isdigit():
                query = """
                    SELECT l.student_id, l.action, l.time, l.image_path
                    FROM logs l
                    JOIN class_students cs ON l.student_id = cs.student_id
                    WHERE date(l.time) = date(?) AND cs.class_id = ?
                    ORDER BY l.time ASC
                """
            else:
                query = """
                    SELECT l.student_id, l.action, l.time, l.image_path
                    FROM logs l
                    JOIN students s ON l.student_id = s.id
                    WHERE date(l.time) = date(?) AND s.student_class = ?
                    ORDER BY l.time ASC
                """
            cursor.execute(query, (date_str, class_name))
            logs = cursor.fetchall()
            
            # Gom nhóm log theo sinh viên
            student_logs = {}
            for log in logs:
                s_id = log['student_id']
                if s_id not in student_logs:
                    student_logs[s_id] = []
                student_logs[s_id].append(log)
            
            # 3. Xây dựng ma trận kết quả
            report = []
            for s in students:
                s_id = s['id']
                s_name = s['name']
                
                logs_of_student = student_logs.get(s_id, [])
                
                in_time = "-"
                out_time = "-"
                in_image = None
                out_image = None
                status = "Vắng" # Mặc định
                
                if logs_of_student:
                    # Tìm check-in đầu tiên và check-out cuối cùng trong ngày
                    ins = [l for l in logs_of_student if l['action'] == 'IN']
                    outs = [l for l in logs_of_student if l['action'] == 'OUT']
                    
                    if ins:
                        in_time = ins[0]['time'].split(" ")[1] # Giờ của lần vào đầu tiên
                        # Tìm ảnh đầu tiên có dữ liệu trong danh sách các lần vào
                        in_imgs = [l['image_path'] for l in ins if l['image_path']]
                        in_image = in_imgs[0] if in_imgs else None
                        status = "Có mặt"
                        
                        if outs:
                            out_time = outs[-1]['time'].split(" ")[1] # Giờ của lần ra cuối cùng
                            # Tìm ảnh cuối cùng có dữ liệu trong danh sách các lần ra
                            out_imgs = [l['image_path'] for l in outs if l['image_path']]
                            out_image = out_imgs[-1] if out_imgs else None
                            status = "Hoàn thành"
                        else:
                            status = "Chưa Checkout"
                    elif outs:
                        # Trường hợp hi hữu: chỉ có log OUT
                        out_time = outs[-1]['time'].split(" ")[1]
                        out_imgs = [l['image_path'] for l in outs if l['image_path']]
                        out_image = out_imgs[-1] if out_imgs else None
                        status = "Chỉ Checkout"

                report.append({
                    "id": s_id,
                    "name": s_name,
                    "in_time": in_time,
                    "out_time": out_time,
                    "status": status,
                    "in_image": in_image,
                    "out_image": out_image
                })
                
            return report