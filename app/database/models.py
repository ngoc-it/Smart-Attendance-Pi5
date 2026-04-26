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
        conn.row_factory = sqlite3.Row
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

            # Bang schedules (Thời khóa biểu gốc)
            cursor.execute('''CREATE TABLE IF NOT EXISTS schedules 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, class_id INTEGER, 
                 weekday INTEGER, start_time TEXT, end_time TEXT, room TEXT,
                 start_period_id INTEGER, num_periods INTEGER, room_id INTEGER,
                 FOREIGN KEY(class_id) REFERENCES classes(id))''')

            cursor.execute("PRAGMA table_info(schedules)")
            sched_cols = [col[1] for col in cursor.fetchall()]
            if 'start_period_id' not in sched_cols:
                cursor.execute("ALTER TABLE schedules ADD COLUMN start_period_id INTEGER")
            if 'num_periods' not in sched_cols:
                cursor.execute("ALTER TABLE schedules ADD COLUMN num_periods INTEGER")
            if 'room_id' not in sched_cols:
                cursor.execute("ALTER TABLE schedules ADD COLUMN room_id INTEGER")

            # Bang semesters (Học kỳ)
            cursor.execute('''CREATE TABLE IF NOT EXISTS semesters
                (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, start_date TEXT, end_date TEXT, is_current INTEGER DEFAULT 0)''')

            # Bang class_sessions (Từng buổi học cụ thể được sinh ra)
            cursor.execute('''CREATE TABLE IF NOT EXISTS class_sessions
                (id INTEGER PRIMARY KEY AUTOINCREMENT, class_id INTEGER, 
                 session_date TEXT, start_time TEXT, end_time TEXT, status TEXT DEFAULT 'SCHEDULED', room TEXT,
                 room_id INTEGER,
                 FOREIGN KEY(class_id) REFERENCES classes(id))''')

            cursor.execute("PRAGMA table_info(class_sessions)")
            sess_cols = [col[1] for col in cursor.fetchall()]
            if 'room_id' not in sess_cols:
                cursor.execute("ALTER TABLE class_sessions ADD COLUMN room_id INTEGER")

            # Bang rooms (Phòng học)
            cursor.execute('''CREATE TABLE IF NOT EXISTS rooms 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, capacity INTEGER, has_camera INTEGER DEFAULT 1)''')

            # Bang periods (Tiết học)
            cursor.execute('''CREATE TABLE IF NOT EXISTS periods 
                (id INTEGER PRIMARY KEY, name TEXT UNIQUE, start_time TEXT, end_time TEXT)''')
            
            # Bang device_payloads (Queue cho Edge Devices)
            cursor.execute('''CREATE TABLE IF NOT EXISTS device_payloads 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, class_id INTEGER, 
                 date TEXT, trigger_start TEXT, trigger_end TEXT, status TEXT DEFAULT 'PENDING')''')

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
                "camera_status": "online",
                "early_checkin_minutes": "15" # Default allow checkin 15 mins early
            }
            for k, v in default_settings.items():
                cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
                
            # Pre-populate periods (Tiết 1-12)
            default_periods = [
                (1, 'Tiết 1', '07:30', '08:20'), (2, 'Tiết 2', '08:20', '09:10'),
                (3, 'Tiết 3', '09:20', '10:10'), (4, 'Tiết 4', '10:10', '11:00'),
                (5, 'Tiết 5', '11:00', '11:50'), (6, 'Tiết 6', '13:00', '13:50'),
                (7, 'Tiết 7', '13:50', '14:40'), (8, 'Tiết 8', '14:50', '15:40'),
                (9, 'Tiết 9', '15:40', '16:30'), (10, 'Tiết 10', '16:30', '17:20'),
                (11, 'Tiết 11', '18:00', '18:50'), (12, 'Tiết 12', '18:50', '19:40')
            ]
            for pid, pname, pstart, pend in default_periods:
                cursor.execute("INSERT OR IGNORE INTO periods (id, name, start_time, end_time) VALUES (?, ?, ?, ?)", (pid, pname, pstart, pend))

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
            cursor.execute("""
                SELECT c.id, c.name, c.code, 
                (SELECT COUNT(*) FROM class_students cs WHERE cs.class_id = c.id) as student_count
                FROM classes c 
                ORDER BY c.name ASC 
                LIMIT ? OFFSET ?
            """, (per_page, offset))
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

    def get_class_by_id(self, class_id):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
            return cursor.fetchone()

    def get_students_by_class_identifier(self, name, code=None):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # Tìm sinh viên khớp với Tên hoặc Mã lớp
            cursor.execute("SELECT id, name, dob, student_class FROM students WHERE student_class = ? OR (student_class = ? AND ? IS NOT NULL)", 
                           (name, code, code))
            return cursor.fetchall()

    # ---- ACADEMIC CRUD (Departments, Majors, Courses) ----
    def get_all_departments(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM departments ORDER BY name")
            return cursor.fetchall()

    def get_all_majors(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.*, d.name as dept_name 
                FROM majors m 
                LEFT JOIN departments d ON m.department_id = d.id 
                ORDER BY m.name
            """)
            return cursor.fetchall()

    def get_all_courses(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.*, m.name as major_name 
                FROM courses c 
                LEFT JOIN majors m ON c.major_id = m.id 
                ORDER BY c.name
            """)
            return cursor.fetchall()
            
    def create_department(self, name):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO departments (name) VALUES (?)", (name,))
                conn.commit()
                return True
        except: return False

    def update_department(self, dept_id, name):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE departments SET name = ? WHERE id = ?", (name, dept_id))
                conn.commit()
                return True
        except: return False

    def delete_department(self, dept_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM departments WHERE id = ?", (dept_id,))
                conn.commit()
                return True
        except: return False

    def get_majors(self, department_id=None):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if department_id:
                cursor.execute("SELECT m.*, d.name as dept_name FROM majors m LEFT JOIN departments d ON m.department_id = d.id WHERE m.department_id = ?", (department_id,))
            else:
                cursor.execute("SELECT m.*, d.name as dept_name FROM majors m LEFT JOIN departments d ON m.department_id = d.id ORDER BY m.name")
            return cursor.fetchall()

    def create_major(self, name, department_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO majors (name, department_id) VALUES (?, ?)", (name, department_id))
                conn.commit()
                return True
        except: return False

    def update_major(self, major_id, name, department_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE majors SET name = ?, department_id = ? WHERE id = ?", (name, department_id, major_id))
                conn.commit()
                return True
        except: return False

    def delete_major(self, major_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM majors WHERE id = ?", (major_id,))
                conn.commit()
                return True
        except: return False

    def get_courses(self, major_id=None):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if major_id:
                cursor.execute("SELECT c.*, m.name as major_name FROM courses c LEFT JOIN majors m ON c.major_id = m.id WHERE c.major_id = ?", (major_id,))
            else:
                cursor.execute("SELECT c.*, m.name as major_name FROM courses c LEFT JOIN majors m ON c.major_id = m.id ORDER BY c.name")
            return cursor.fetchall()

    def create_course(self, name, major_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO courses (name, major_id) VALUES (?, ?)", (name, major_id))
                conn.commit()
                return True
        except: return False

    def update_course(self, course_id, name, major_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE courses SET name = ?, major_id = ? WHERE id = ?", (name, major_id, course_id))
                conn.commit()
                return True
        except: return False

    def delete_course(self, course_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
                conn.commit()
                return True
        except: return False

    def delete_semester(self, sem_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM semesters WHERE id = ? AND is_current = 0", (sem_id,))
                conn.commit()
                return cursor.rowcount > 0
        except: return False

    def delete_room(self, room_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
                conn.commit()
                return True
        except: return False

    def update_room(self, room_id, name, capacity, has_camera):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE rooms SET name = ?, capacity = ?, has_camera = ? WHERE id = ?", (name, capacity, has_camera, room_id))
                conn.commit()
                return True
        except: return False

    # ---- LECTURER SPECIFIC ----
    def get_user_schedule(self, user_id):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.class_id, s.weekday, 
                       p.start_time, p.end_time, 
                       r.name as room_name,
                       c.name as class_name, c.code as class_code,
                       s.num_periods, p.name as period_name
                FROM schedules s 
                JOIN user_classes uc ON s.class_id = uc.class_id
                JOIN classes c ON s.class_id = c.id
                LEFT JOIN periods p ON s.start_period_id = p.id
                LEFT JOIN rooms r ON s.room_id = r.id
                WHERE uc.user_id = ?
                ORDER BY s.weekday, p.start_time
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

    def get_student_by_id(self, student_id):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
            return cursor.fetchone()

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

    # --- TKB & SESSION MANAGEMENT ---
    
    def get_all_semesters(self):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM semesters ORDER BY start_date DESC")
            return cursor.fetchall()

    def get_current_semester(self):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM semesters WHERE is_current = 1 LIMIT 1")
            return cursor.fetchone()

    def create_semester(self, name, start_date, end_date, is_current=0):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if is_current == 1:
                cursor.execute("UPDATE semesters SET is_current = 0")
            cursor.execute("INSERT INTO semesters (name, start_date, end_date, is_current) VALUES (?, ?, ?, ?)",
                           (name, start_date, end_date, is_current))
            conn.commit()
            return cursor.lastrowid

    def set_current_semester(self, semester_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE semesters SET is_current = 0")
            cursor.execute("UPDATE semesters SET is_current = 1 WHERE id = ?", (semester_id,))
            conn.commit()

    def update_semester(self, sem_id, name, start_date, end_date):
        """Cập nhật thông tin học kỳ và đồng bộ lại toàn bộ buổi học"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE semesters 
                    SET name = ?, start_date = ?, end_date = ? 
                    WHERE id = ?
                """, (name, start_date, end_date, sem_id))
                conn.commit()
            
            # Sau khi đổi ngày, cần đồng bộ lại toàn bộ các lớp
            # Senior Logic: Quét toàn bộ các lớp đang có và sinh lại session
            self.regenerate_all_sessions()
            return True, "Cập nhật thành công và đã đồng bộ lại toàn bộ buổi học."
        except Exception as e:
            return False, str(e)

    def regenerate_all_sessions(self):
        """Xóa và sinh lại toàn bộ session cho tất cả các lớp dựa trên TKB hiện tại"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM classes")
            classes = cursor.fetchall()
            
        for (class_id,) in classes:
            self.generate_sessions_for_class(class_id)

    # ---- MASTER DATA (ROOMS & PERIODS) ----
    def get_all_rooms(self):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rooms ORDER BY name ASC")
            return cursor.fetchall()
            
    def create_room(self, name, capacity, has_camera=1):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO rooms (name, capacity, has_camera) VALUES (?, ?, ?)", (name, capacity, has_camera))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_all_periods(self):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM periods ORDER BY id ASC")
            return cursor.fetchall()

    def get_class_schedules(self, class_id):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, r.name as room_name, p.name as period_name, p.start_time, p.end_time
                FROM schedules s
                LEFT JOIN rooms r ON s.room_id = r.id
                LEFT JOIN periods p ON s.start_period_id = p.id
                WHERE s.class_id = ?
            """, (class_id,))
            return cursor.fetchall()

    def check_schedule_conflict(self, class_id, weekday, start_period_id, num_periods, room_id):
        """
        Zero Trust Check:
        1. Room conflict: Is the room already booked at this time?
        2. Lecturer conflict: Is the lecturer assigned to this class busy?
        """
        end_period_id = start_period_id + num_periods - 1
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 1. Check Room Conflict
            cursor.execute("""
                SELECT c.name, s.start_period_id, s.num_periods 
                FROM schedules s
                JOIN classes c ON s.class_id = c.id
                WHERE s.room_id = ? AND s.weekday = ? AND s.class_id != ?
            """, (room_id, weekday, class_id))
            room_schedules = cursor.fetchall()
            for cname, s_start, s_num in room_schedules:
                s_end = s_start + s_num - 1
                if not (end_period_id < s_start or start_period_id > s_end):
                    return False, f"Phòng này đã được xếp cho lớp {cname} vào tiết {s_start}-{s_end}."
                    
            # 2. Check Lecturer Conflict
            # Get lecturers of this class
            cursor.execute("SELECT user_id FROM user_classes WHERE class_id = ?", (class_id,))
            lecturers = [row[0] for row in cursor.fetchall()]
            
            for lec_id in lecturers:
                # Get all other classes of this lecturer
                cursor.execute("""
                    SELECT c.name, s.start_period_id, s.num_periods 
                    FROM schedules s
                    JOIN classes c ON s.class_id = c.id
                    JOIN user_classes uc ON c.id = uc.class_id
                    WHERE uc.user_id = ? AND s.weekday = ? AND s.class_id != ?
                """, (lec_id, weekday, class_id))
                lec_schedules = cursor.fetchall()
                for cname, s_start, s_num in lec_schedules:
                    s_end = s_start + s_num - 1
                    if not (end_period_id < s_start or start_period_id > s_end):
                        return False, f"Giảng viên bị trùng lịch với lớp {cname} vào tiết {s_start}-{s_end}."
            
            return True, "OK"

    def save_class_schedules(self, class_id, schedules_list):
        """
        schedules_list is a list of dicts: [{'weekday': 2, 'start_period_id': 1, 'num_periods': 3, 'room_id': 1}, ...]
        weekday: 2=Monday, 8=Sunday
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM schedules WHERE class_id = ?", (class_id,))
            for sch in schedules_list:
                cursor.execute("""
                    INSERT INTO schedules (class_id, weekday, start_period_id, num_periods, room_id) 
                    VALUES (?, ?, ?, ?, ?)
                """, (class_id, sch.get('weekday'), sch.get('start_period_id'), sch.get('num_periods'), sch.get('room_id')))
            conn.commit()
            
    def generate_sessions_for_class(self, class_id):
        """Sinh ra các buổi học thực tế dựa trên TKB và học kỳ hiện tại"""
        semester = self.get_current_semester()
        if not semester:
            return False, "Chưa thiết lập học kỳ hiện tại."
            
        start_date = datetime.strptime(semester['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(semester['end_date'], '%Y-%m-%d')
        
        schedules = self.get_class_schedules(class_id)
        if not schedules:
            return False, "Lớp chưa có thời khóa biểu gốc."
            
        # Lấy thông tin periods để tính giờ
        periods = {p['id']: p for p in self.get_all_periods()}
        early_checkin_minutes = int(self.get_setting("early_checkin_minutes", 15))
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Xóa các session tương lai (hoặc tất cả session SCHEDULED) của lớp này
            cursor.execute("DELETE FROM class_sessions WHERE class_id = ? AND status = 'SCHEDULED'", (class_id,))
            cursor.execute("DELETE FROM device_payloads WHERE class_id = ? AND status = 'PENDING'", (class_id,))
            
            from datetime import timedelta
            
            count = 0
            current_date = start_date
            while current_date <= end_date:
                # python weekday(): Monday is 0, Sunday is 6
                # CSDL weekday: 2=Monday, 8=Sunday
                current_weekday = current_date.weekday() + 2
                
                for sch in schedules:
                    if sch['weekday'] == current_weekday:
                        date_str = current_date.strftime('%Y-%m-%d')
                        start_p_id = sch['start_period_id']
                        num_p = sch['num_periods']
                        if not start_p_id or not num_p:
                            continue
                            
                        end_p_id = start_p_id + num_p - 1
                        
                        # Handle potential missing period mappings gracefully
                        try:
                            start_time = periods[start_p_id]['start_time']
                            end_time = periods[end_p_id]['end_time']
                        except KeyError:
                            start_time = "00:00"
                            end_time = "00:00"
                        
                        room_id = sch['room_id']
                        
                        cursor.execute("""
                            INSERT INTO class_sessions (class_id, session_date, start_time, end_time, room_id, status)
                            VALUES (?, ?, ?, ?, ?, 'SCHEDULED')
                        """, (class_id, date_str, start_time, end_time, room_id))
                        
                        # Generate payload for Edge Device
                        if start_time != "00:00":
                            start_dt = datetime.strptime(f"{date_str} {start_time}", '%Y-%m-%d %H:%M')
                            trigger_start = (start_dt - timedelta(minutes=early_checkin_minutes)).strftime('%H:%M')
                            trigger_end = end_time
                            cursor.execute("""
                                INSERT INTO device_payloads (room_id, class_id, date, trigger_start, trigger_end, status)
                                VALUES (?, ?, ?, ?, ?, 'PENDING')
                            """, (room_id, class_id, date_str, trigger_start, trigger_end))
                            
                        count += 1
                
                current_date += timedelta(days=1)
                
            conn.commit()
            return True, f"Đã sinh {count} buổi học và payload thiết bị."

    def get_class_sessions(self, class_id):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM class_sessions WHERE class_id = ? ORDER BY session_date ASC, start_time ASC", (class_id,))
            return cursor.fetchall()

    def update_session_status(self, session_id, status):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE class_sessions SET status = ? WHERE id = ?", (status, session_id))
            conn.commit()

    def get_active_session(self):
        """Kiosk gọi hàm này để tự động tìm lớp học hiện tại"""
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        
        # Lấy cấu hình check-in sớm / check-out muộn
        early_min = 15
        late_out_min = 30
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings WHERE key IN ('early_checkin_minutes', 'late_checkout_minutes')")
            rows = cursor.fetchall()
            for k, v in rows:
                if k == 'early_checkin_minutes':
                    try: early_min = int(v)
                    except: pass
                elif k == 'late_checkout_minutes':
                    try: late_out_min = int(v)
                    except: pass

            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cs.*, c.name as class_name 
                FROM class_sessions cs
                JOIN classes c ON cs.class_id = c.id
                WHERE cs.session_date = ? AND cs.status = 'SCHEDULED'
            """, (date_str,))
            sessions = cursor.fetchall()
            
            from datetime import timedelta
            for s in sessions:
                # Format: HH:MM
                start_t = datetime.strptime(f"{date_str} {s['start_time']}", '%Y-%m-%d %H:%M')
                end_t = datetime.strptime(f"{date_str} {s['end_time']}", '%Y-%m-%d %H:%M')
                
                checkin_start = start_t - timedelta(minutes=early_min)
                checkout_end = end_t + timedelta(minutes=late_out_min)
                
                if checkin_start <= now <= checkout_end:
                    return s
            return None