import sqlite3
from datetime import datetime, timedelta
import os
import hashlib

# Import Mixins
from app.database.mixins.lecturer import LecturerDBMixin
from app.database.mixins.academic import AcademicDBMixin
from app.database.mixins.class_student import ClassStudentDBMixin
from app.database.mixins.schedule import ScheduleDBMixin
from app.database.mixins.attendance import AttendanceDBMixin

class AttendanceDB(
    LecturerDBMixin, 
    AcademicDBMixin, 
    ClassStudentDBMixin, 
    ScheduleDBMixin, 
    AttendanceDBMixin
):
    def __init__(self, db_path):
        """Khởi tạo đối tượng quản lý Database và thực hiện kiểm tra cấu trúc bảng."""
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        """Tạo kết nối đến SQLite, cấu hình Row factory và đăng ký các hàm hỗ trợ sắp xếp tiếng Việt."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        except:
            pass
        conn.row_factory = sqlite3.Row
        # Hàm lấy tên (chữ cuối cùng) để sắp xếp A-Z theo tên tiếng Việt
        def get_vietnamese_name(full_name):
            if not full_name: return ""
            parts = str(full_name).strip().split()
            return parts[-1] if parts else ""
        conn.create_function("GET_TEN", 1, get_vietnamese_name)
        return conn

    def _init_db(self):
        """Khởi tạo hệ thống bảng, thực hiện migration schema nếu có thay đổi và nạp cấu hình mặc định."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_conn() as conn:
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
            if 'is_active' not in columns:
                cursor.execute("ALTER TABLE students ADD COLUMN is_active INTEGER DEFAULT 1")

            # Bang classes
            cursor.execute('''CREATE TABLE IF NOT EXISTS classes 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, code TEXT, course_id INTEGER)''')
            
            cursor.execute("PRAGMA table_info(classes)")
            class_columns = [col[1] for col in cursor.fetchall()]
            if 'course_id' not in class_columns:
                cursor.execute("ALTER TABLE classes ADD COLUMN course_id INTEGER")
            if 'code' not in class_columns:
                cursor.execute("ALTER TABLE classes ADD COLUMN code TEXT")

            # Bang users
            cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, name TEXT, code TEXT, email TEXT)''')
            
            cursor.execute("PRAGMA table_info(users)")
            user_cols = [col[1] for col in cursor.fetchall()]
            if 'code' not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN code TEXT")
            if 'email' not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
            if 'must_change_password' not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0")

            # Bang password_resets (Ma OTP va token khoi phuc mat khau)
            cursor.execute('''CREATE TABLE IF NOT EXISTS password_resets 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, email TEXT, token TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP, used INTEGER DEFAULT 0)''')

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
                (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, code TEXT UNIQUE, 
                 credits INTEGER, lt_credits INTEGER, th_credits INTEGER, 
                 total_periods INTEGER, is_mandatory INTEGER DEFAULT 1, major_id INTEGER,
                 FOREIGN KEY(major_id) REFERENCES majors(id))''')

            cursor.execute("PRAGMA table_info(courses)")
            course_cols = [col[1] for col in cursor.fetchall()]
            course_updates = [
                ('code', 'TEXT'),
                ('credits', 'INTEGER'),
                ('lt_credits', 'INTEGER'),
                ('th_credits', 'INTEGER'),
                ('total_periods', 'INTEGER'),
                ('is_mandatory', 'INTEGER DEFAULT 1'),
                ('category', 'TEXT'),
                ('major_id', 'INTEGER')
            ]
            for col_name, col_type in course_updates:
                if col_name not in course_cols:
                    try:
                        cursor.execute(f"ALTER TABLE courses ADD COLUMN {col_name} {col_type}")
                    except: pass
            
            # Index for unique code
            try:
                cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_course_code ON courses(code)')
            except: pass

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
            if 'num_periods' not in sess_cols:
                cursor.execute("ALTER TABLE class_sessions ADD COLUMN num_periods INTEGER")

            # Bang holidays
            cursor.execute('''CREATE TABLE IF NOT EXISTS holidays 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, holiday_date TEXT UNIQUE)''')

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

            # Bang attendance_logs (Nhật ký điểm danh chi tiết)
            cursor.execute('''CREATE TABLE IF NOT EXISTS attendance_logs 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, name TEXT, 
                 date TEXT, time TEXT, status TEXT, image TEXT, room_id INTEGER, class_id INTEGER)''')

            # Bang leave_requests (Đơn xin nghỉ phép)
            cursor.execute('''CREATE TABLE IF NOT EXISTS leave_requests 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, class_id INTEGER, 
                 reason TEXT, date TEXT, status TEXT DEFAULT 'PENDING',
                 FOREIGN KEY(student_id) REFERENCES students(id),
                 FOREIGN KEY(class_id) REFERENCES classes(id))''')

            # Bang makeup_requests (Yêu cầu dạy bù)
            cursor.execute('''CREATE TABLE IF NOT EXISTS makeup_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER,
                    user_id INTEGER,
                    requested_date TEXT,
                    start_period_id INTEGER,
                    num_periods INTEGER,
                    room_id INTEGER,
                    reason TEXT,
                    status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    approved_by INTEGER,
                    FOREIGN KEY (class_id) REFERENCES classes (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (room_id) REFERENCES rooms (id)
                )''')

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
            
            # MIGRATION: Chuyển dữ liệu từ logs sang attendance_logs (Nếu bảng logs còn tồn tại)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='logs'")
            if cursor.fetchone():
                print(">>> Thực hiện Migration dữ liệu từ logs sang attendance_logs...")
                cursor.execute("""
                    INSERT INTO attendance_logs (student_id, name, date, time, status, image)
                    SELECT l.student_id, s.name, date(l.time), time(l.time), l.action, l.image_path 
                    FROM logs l
                    LEFT JOIN students s ON l.student_id = s.id
                """)
                cursor.execute("DROP TABLE logs")
                print(">>> Migration hoàn tất. Đã xóa bảng logs cũ.")
            
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
                
            # Pre-populate periods (Tiết 1-10)
            default_periods = [
                (1, 'Tiết 1', '07:30', '08:20'), (2, 'Tiết 2', '08:20', '09:10'),
                (3, 'Tiết 3', '09:20', '10:10'), (4, 'Tiết 4', '10:10', '11:00'),
                (5, 'Tiết 5', '13:30', '14:20'), (6, 'Tiết 6', '14:20', '15:10'),
                (7, 'Tiết 7', '15:20', '16:10'), (8, 'Tiết 8', '16:10', '17:00'),
                (9, 'Tiết 9', '18:20', '19:10'), (10, 'Tiết 10', '19:10', '20:00')
            ]
            for pid, pname, pstart, pend in default_periods:
                cursor.execute("INSERT OR IGNORE INTO periods (id, name, start_time, end_time) VALUES (?, ?, ?, ?)", (pid, pname, pstart, pend))

    def hash_password(self, password):
        from werkzeug.security import generate_password_hash
        return generate_password_hash(password)

    def verify_login(self, username, password, role):
        """Kiểm tra thông tin đăng nhập. Trả về thông tin User nếu khớp, ngược lại trả về None."""
        from werkzeug.security import check_password_hash
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, role, password, COALESCE(must_change_password, 0) 
                FROM users 
                WHERE (username = ? OR email = ? OR code = ?) AND role = ?
            """, (username, username, username, role))
            user = cursor.fetchone()
            if user:
                user_id, name, user_role, stored_pw, must_change = user
                
                # Check using Werkzeug check_password_hash
                if stored_pw.startswith('pbkdf2:') or stored_pw.startswith('scrypt:') or stored_pw.startswith('bcrypt:'):
                    if check_password_hash(stored_pw, password):
                        return (user_id, name, user_role, must_change)
                else:
                    # Fallback to legacy SHA-256 hash comparison
                    legacy_hash = hashlib.sha256(password.encode()).hexdigest()
                    if stored_pw == legacy_hash:
                        # Auto-upgrade the legacy SHA-256 hash to a secure hash!
                        new_hashed_pw = self.hash_password(password)
                        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_hashed_pw, user_id))
                        conn.commit()
                        return (user_id, name, user_role, must_change)
            return None


    # ---- SYSTEM SETTINGS ----
    def get_setting(self, key, default=None):
        """Lấy giá trị của một cấu hình cụ thể theo khóa (key)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def get_settings(self):
        """Lấy toàn bộ cấu hình hệ thống dưới dạng dictionary (key-value)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            return dict(cursor.fetchall())

    def update_setting(self, key, value):
        """Cập nhật hoặc thêm mới một giá trị cấu hình hệ thống."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE settings SET value = ? WHERE key = ?", (str(value), key))
            conn.commit()

