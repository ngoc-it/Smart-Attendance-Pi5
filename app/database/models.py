import sqlite3
from datetime import datetime, timedelta
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
                (5, 'Tiết 5', '13:30', '14:20'), (6, 'Tiết 6', '14:20', '15:10'),
                (7, 'Tiết 7', '15:20', '16:10'), (8, 'Tiết 8', '16:10', '17:00'),
                (9, 'Tiết 9', '18:20', '19:10'), (10, 'Tiết 10', '19:10', '20:00')
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
                SELECT c.id, c.name, c.code, c.course_id, crs.name as course_name,
                (SELECT COUNT(*) FROM class_students cs WHERE cs.class_id = c.id) as student_count
                FROM classes c
                JOIN user_classes uc ON c.id = uc.class_id
                LEFT JOIN courses crs ON c.course_id = crs.id
                WHERE uc.user_id = ?
                ORDER BY c.name ASC
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
                SELECT c.id, c.name, c.code, c.course_id, crs.name as course_name,
                (SELECT COUNT(*) FROM class_students cs WHERE cs.class_id = c.id) as student_count
                FROM classes c 
                LEFT JOIN courses crs ON c.course_id = crs.id
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

    def update_class(self, class_id, name, code, course_id=None):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE classes SET name = ?, code = ?, course_id = ? WHERE id = ?", (name, code, course_id, class_id))
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

    def get_all_courses(self, major_id=None, category=None):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = """
                SELECT c.*, m.name as major_name 
                FROM courses c 
                LEFT JOIN majors m ON c.major_id = m.id
                WHERE 1=1
            """
            params = []
            if major_id:
                query += " AND c.major_id = ?"
                params.append(major_id)
            if category:
                query += " AND c.category = ?"
                params.append(category)
                
            query += " ORDER BY c.category ASC, c.name ASC"
            cursor.execute(query, params)
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

    def create_course(self, name, major_id, code=None, category=None, credits=0, lt_credits=0, th_credits=0, total_periods=0):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO courses (name, code, credits, lt_credits, th_credits, total_periods, category, major_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, code, credits, lt_credits, th_credits, total_periods, category, major_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error create_course: {e}")
            return False

    def import_curriculum_courses(self, courses_data):
        count = 0
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for c in courses_data:
                try:
                    # Tìm hoặc tạo Ngành (Major) nếu có major_name
                    major_id = None
                    if c.get('major_name'):
                        cursor.execute("SELECT id FROM majors WHERE name = ?", (c['major_name'],))
                        m_row = cursor.fetchone()
                        if m_row:
                            major_id = m_row[0]
                        else:
                            cursor.execute("INSERT INTO majors (name) VALUES (?)", (c['major_name'],))
                            major_id = cursor.lastrowid

                    cursor.execute("""
                        INSERT INTO courses (name, code, credits, lt_credits, th_credits, total_periods, is_mandatory, category, major_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(code) DO UPDATE SET
                            name = excluded.name,
                            credits = excluded.credits,
                            lt_credits = excluded.lt_credits,
                            th_credits = excluded.th_credits,
                            total_periods = excluded.total_periods,
                            is_mandatory = excluded.is_mandatory,
                            category = excluded.category,
                            major_id = excluded.major_id
                    """, (c['name'], c['code'], c['credits'], c['lt_credits'], c['th_credits'], c['total_periods'], c['is_mandatory'], c.get('category'), major_id))
                    count += 1
                except Exception as e:
                    print(f"Error importing course {c['code']}: {e}")
            conn.commit()
        return count

    def update_course(self, course_id, name, major_id, code=None, category=None, credits=0, lt_credits=0, th_credits=0, total_periods=0):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE courses 
                    SET name = ?, code = ?, category = ?, major_id = ?, 
                        credits = ?, lt_credits = ?, th_credits = ?, total_periods = ?
                    WHERE id = ?
                """, (name, code, category, major_id, credits, lt_credits, th_credits, total_periods, course_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error update_course: {e}")
            return False

    def delete_course(self, course_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
                conn.commit()
                return True
        except: return False

    def import_classes(self, classes_data):
        count = 0
        with sqlite3.connect(self.db_path) as conn:
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
                       p.start_time, 
                       (SELECT end_time FROM periods WHERE id = s.start_period_id + s.num_periods - 1) as end_time,
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

    def update_status(self, student_id, name, action, image_path=None):
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

    def update_attendance_manual(self, student_id, action, date_str, reason=None):
        """Ghi nhận trạng thái điểm danh thủ công (Vắng có phép/không phép) cho ngày cụ thể"""
        log_time = f"{date_str} 00:00:01" # 1 giây đầu ngày để phân biệt với log tự động
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Lưu lý do vào cột image_path với tiền tố SPECIAL:
            reason_payload = f"SPECIAL:{reason}" if reason else None
            cursor.execute("INSERT INTO logs (student_id, action, time, image_path) VALUES (?, ?, ?, ?)", 
                           (student_id, action, log_time, reason_payload))
            
            # Cập nhật status hiện tại nếu là hôm nay
            if date_str == datetime.now().strftime("%Y-%m-%d"):
                cursor.execute("UPDATE students SET status = ?, last_seen = ? WHERE id = ?", (action, log_time, student_id))
            conn.commit()
            return True

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
                
                # 1. Kiểm tra trạng thái vắng có phép/không phép trước (do GV đánh dấu)
                excused = [l for l in logs_of_student if l['action'] == 'EXCUSED']
                unexcused = [l for l in logs_of_student if l['action'] == 'UNEXCUSED']
                
                if excused:
                    reason = ""
                    if excused[0]['image_path'] and str(excused[0]['image_path']).startswith("SPECIAL:"):
                        reason = f" ({excused[0]['image_path'].split(':', 1)[1]})"
                    status = f"Vắng (Có phép){reason}"
                elif unexcused:
                    reason = ""
                    if unexcused[0]['image_path'] and str(unexcused[0]['image_path']).startswith("SPECIAL:"):
                        reason = f" ({unexcused[0]['image_path'].split(':', 1)[1]})"
                    status = f"Vắng (Không phép){reason}"
                elif logs_of_student:
                    # 2. Xử lý logic vào/ra tự động
                    ins = [l for l in logs_of_student if l['action'] == 'IN']
                    outs = [l for l in logs_of_student if l['action'] == 'OUT']
                    
                    if ins:
                        full_in_time = ins[0]['time']
                        in_time = full_in_time.split(" ")[1] 
                        in_imgs = [l['image_path'] for l in ins if l['image_path']]
                        in_image = in_imgs[0] if in_imgs else None
                        
                        # Kiểm tra đi trễ (So với giờ bắt đầu ca học)
                        # Lấy session của lớp trong ngày này
                        cursor.execute("SELECT start_time FROM class_sessions WHERE class_id = ? AND session_date = ?", (class_name if str(class_name).isdigit() else 0, date_str))
                        sess = cursor.fetchone()
                        
                        is_late = False
                        if sess:
                            try:
                                sess_start = datetime.strptime(f"{date_str} {sess['start_time']}", "%Y-%m-%d %H:%M")
                                actual_in = datetime.strptime(full_in_time, "%Y-%m-%d %H:%M:%S")
                                # Lấy ngưỡng đi trễ từ settings (mặc định 15p)
                                late_limit = int(self.get_setting("late_limit_minutes", "15"))
                                if (actual_in - sess_start).total_seconds() > late_limit * 60:
                                    is_late = True
                            except: pass

                        if outs:
                            out_time = outs[-1]['time'].split(" ")[1]
                            out_imgs = [l['image_path'] for l in outs if l['image_path']]
                            out_image = out_imgs[-1] if out_imgs else None
                            status = "Đi trễ" if is_late else "Hoàn thành"
                        else:
                            status = "Đi trễ" if is_late else "Chưa Checkout"
                    elif outs:
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

    def get_attendance_summary_matrix(self, class_id, start_date=None, end_date=None):
        """Lấy dữ liệu ma trận điểm danh tổng hợp của lớp học trong khoảng thời gian"""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 1. Lấy thông tin lớp và học phần
            cursor.execute("""
                SELECT c.name as class_name, c.code as class_code, crs.name as course_name 
                FROM classes c
                LEFT JOIN courses crs ON c.course_id = crs.id
                WHERE c.id = ?
            """, (class_id,))
            class_info = cursor.fetchone()
            if not class_info: return None, None, None

            # 2. Lấy danh sách tất cả sinh viên trong lớp
            cursor.execute("""
                SELECT s.id, s.name 
                FROM students s
                JOIN class_students cs ON s.id = cs.student_id
                WHERE cs.class_id = ?
                ORDER BY GET_TEN(s.name) ASC, s.name ASC
            """, (class_id,))
            students = cursor.fetchall()

            # 3. Lấy tất cả các ngày đã có điểm danh trong khoảng thời gian
            query = """
                SELECT DISTINCT date(l.time) as session_date 
                FROM logs l
                JOIN class_students cs ON l.student_id = cs.student_id
                WHERE cs.class_id = ?
            """
            params = [class_id]
            if start_date:
                query += " AND date(l.time) >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date(l.time) <= ?"
                params.append(end_date)
            query += " ORDER BY session_date ASC"
            
            cursor.execute(query, params)
            dates = [row['session_date'] for row in cursor.fetchall()]

            # 4. Lấy toàn bộ logs tương ứng
            query = """
                SELECT l.student_id, l.action, l.time 
                FROM logs l
                JOIN class_students cs ON l.student_id = cs.student_id
                WHERE cs.class_id = ?
            """
            params = [class_id]
            if start_date:
                query += " AND date(l.time) >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date(l.time) <= ?"
                params.append(end_date)
            query += " ORDER BY l.time ASC"
            
            cursor.execute(query, params)
            all_logs = cursor.fetchall()

            # Tổ chức lại log: {date: {student_id: status}}
            matrix = {d: {} for d in dates}
            
            # Tạm thời gom nhóm log theo ngày và sinh viên
            grouped_logs = {} # (date, student_id) -> [actions]
            for log in all_logs:
                d = log['time'].split(' ')[0]
                s_id = log['student_id']
                if (d, s_id) not in grouped_logs:
                    grouped_logs[(d, s_id)] = []
                grouped_logs[(d, s_id)].append(log)

            # Xác định trạng thái cho từng ô trong ma trận
            # Lấy giờ bắt đầu của các session để tính đi trễ
            cursor.execute("SELECT session_date, start_time FROM class_sessions WHERE class_id = ?", (class_id,))
            session_starts = {row['session_date']: row['start_time'] for row in cursor.fetchall()}
            late_limit = int(self.get_setting("late_limit_minutes", "15"))

            for d in dates:
                for s in students:
                    s_id = s['id']
                    logs = grouped_logs.get((d, s_id), [])
                    
                    status = "" # Trống nếu không có log
                    if logs:
                        # Kiểm tra manual status trước
                        if any(l['action'] == 'EXCUSED' for l in logs):
                            status = "P" # Vắng có phép
                        elif any(l['action'] == 'UNEXCUSED' for l in logs):
                            status = "K" # Vắng không phép
                        else:
                            ins = [l for l in logs if l['action'] == 'IN']
                            if ins:
                                status = "x" # Mặc định là có mặt
                                # Kiểm tra đi trễ
                                start_time_str = session_starts.get(d)
                                if start_time_str:
                                    try:
                                        sess_start = datetime.strptime(f"{d} {start_time_str}", "%Y-%m-%d %H:%M")
                                        actual_in = datetime.strptime(ins[0]['time'], "%Y-%m-%d %H:%M:%S")
                                        if (actual_in - sess_start).total_seconds() > late_limit * 60:
                                            status = "T" # Đi trễ
                                    except: pass
                            elif any(l['action'] == 'OUT' for l in logs):
                                status = "x" # Chỉ có OUT vẫn tính là có mặt (hoặc T tùy logic)

                    matrix[d][s_id] = status

            return class_info, students, matrix

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
        """
        Smart Recalculation Logic:
        - Subtract periods already taught (COMPLETED status).
        - Delete all SCHEDULED sessions.
        - Skip holidays found in 'holidays' table.
        - Generate from today (or semester start) until Total Periods reached.
        - Clip last session duration if it exceeds remaining periods.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 1. Get Course Info & Total Needed
                cursor.execute("""
                    SELECT c.total_periods 
                    FROM courses c 
                    JOIN classes cl ON cl.course_id = c.id 
                    WHERE cl.id = ?
                """, (class_id,))
                course_row = cursor.fetchone()
                if not course_row or not course_row['total_periods']:
                    return False, "Học phần chưa có tổng số tiết định mức."
                
                total_needed = course_row['total_periods']

                # 2. Get Already Taught Periods (COMPLETED sessions)
                cursor.execute("SELECT SUM(num_periods) as taught FROM class_sessions WHERE class_id = ? AND status = 'COMPLETED'", (class_id,))
                taught_row = cursor.fetchone()
                taught_periods = taught_row['taught'] or 0
                
                remaining_periods = total_needed - taught_periods
                if remaining_periods <= 0:
                    cursor.execute("DELETE FROM class_sessions WHERE class_id = ? AND status = 'SCHEDULED'", (class_id,))
                    conn.commit()
                    return True, "Học phần đã hoàn thành đủ số tiết."

                # 3. Clear existing SCHEDULED sessions (Recalculate)
                cursor.execute("DELETE FROM class_sessions WHERE class_id = ? AND status = 'SCHEDULED'", (class_id,))
                cursor.execute("DELETE FROM device_payloads WHERE class_id = ? AND status = 'PENDING'", (class_id,))
                
                # 4. Get Semester Dates & Holidays
                cursor.execute("SELECT start_date, end_date FROM semesters WHERE is_current = 1")
                sem = cursor.fetchone()
                if not sem: return False, "Chưa thiết lập học kỳ hiện tại."
                
                cursor.execute("SELECT holiday_date FROM holidays")
                holidays = [h['holiday_date'] for h in cursor.fetchall()]
                
                # 5. Get Weekly Schedules (Explicitly pick times from periods)
                cursor.execute("""
                    SELECT s.id, s.class_id, s.weekday, s.room_id, s.num_periods,
                           p.start_time, p.end_time 
                    FROM schedules s 
                    JOIN periods p ON s.start_period_id = p.id 
                    WHERE s.class_id = ?
                """, (class_id,))
                schedules = [dict(row) for row in cursor.fetchall()]
                if not schedules: return False, "Lớp chưa có thời khóa biểu."

                early_checkin_minutes = int(self.get_setting("early_checkin_minutes", 15))
                
                # 6. Generate starting from max(today, sem_start)
                today = datetime.now().date()
                sem_start = datetime.strptime(sem['start_date'], '%Y-%m-%d').date()
                sem_end = datetime.strptime(sem['end_date'], '%Y-%m-%d').date()
                
                current_date = max(today, sem_start)
                count = 0
                
                while current_date <= sem_end and remaining_periods > 0:
                    date_str = current_date.strftime('%Y-%m-%d')
                    if date_str in holidays:
                        current_date += timedelta(days=1)
                        continue
                    
                    current_weekday = current_date.weekday() + 2
                    day_schedules = [s for s in schedules if s['weekday'] == current_weekday]
                    day_schedules.sort(key=lambda x: x['start_time'])
                    
                    for sch in day_schedules:
                        if remaining_periods <= 0: break
                        
                        num_p = min(remaining_periods, sch['num_periods'])
                        start_time = sch['start_time']
                        end_time = sch['end_time']
                        room_id = sch['room_id']
                        
                        cursor.execute("""
                            INSERT INTO class_sessions (class_id, session_date, start_time, end_time, room_id, status, num_periods)
                            VALUES (?, ?, ?, ?, ?, 'SCHEDULED', ?)
                        """, (class_id, date_str, start_time, end_time, room_id, num_p))
                        
                        # Edge payload
                        if start_time != "00:00":
                            start_dt = datetime.strptime(f"{date_str} {start_time}", '%Y-%m-%d %H:%M')
                            trigger_start = (start_dt - timedelta(minutes=early_checkin_minutes)).strftime('%H:%M')
                            cursor.execute("""
                                INSERT INTO device_payloads (room_id, class_id, date, trigger_start, trigger_end, status)
                                VALUES (?, ?, ?, ?, ?, 'PENDING')
                            """, (room_id, class_id, date_str, trigger_start, end_time))
                        
                        remaining_periods -= num_p
                        count += 1
                    
                    current_date += timedelta(days=1)
                    
                conn.commit()
                return True, f"Đã sinh/tính toán lại {count} buổi học. Tiết còn lại chưa xếp: {remaining_periods}"
        except Exception as e:
            return False, str(e)

    def preview_sessions_for_class(self, class_id, schedules_list=None):
        """Simulate session generation and return list of dates for UI preview"""
        from datetime import datetime, timedelta
        try:
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT c.total_periods, cl.name FROM courses c JOIN classes cl ON cl.course_id = c.id WHERE cl.id = ?", (class_id,))
                course_row = cursor.fetchone()
                if not course_row: return []
                
                total_needed = course_row['total_periods']
                cursor.execute("SELECT SUM(num_periods) as taught FROM class_sessions WHERE class_id = ? AND status = 'COMPLETED'", (class_id,))
                taught_periods = cursor.fetchone()['taught'] or 0
                remaining_periods = total_needed - taught_periods
                
                cursor.execute("SELECT start_date, end_date FROM semesters WHERE is_current = 1")
                sem = cursor.fetchone()
                if not sem: return []
                
                cursor.execute("SELECT holiday_date FROM holidays")
                holidays = [h['holiday_date'] for h in cursor.fetchall()]
                
                if schedules_list is None:
                    cursor.execute("""
                        SELECT s.weekday, s.num_periods, p.start_time, p.end_time 
                        FROM schedules s JOIN periods p ON s.start_period_id = p.id WHERE s.class_id = ?
                    """, (class_id,))
                    schedules = [dict(row) for row in cursor.fetchall()]
                else:
                    # Enrich schedules_list with times from periods table
                    schedules = []
                    for sch in schedules_list:
                        cursor.execute("SELECT start_time FROM periods WHERE id = ?", (sch['start_period_id'],))
                        p_start = cursor.fetchone()
                        cursor.execute("SELECT end_time FROM periods WHERE id = ?", (sch['start_period_id'] + sch['num_periods'] - 1,))
                        p_end = cursor.fetchone()
                        
                        s_enriched = sch.copy()
                        s_enriched['start_time'] = p_start['start_time'] if p_start else '--:--'
                        s_enriched['end_time'] = p_end['end_time'] if p_end else '--:--'
                        schedules.append(s_enriched)
                
                current_date = max(datetime.now().date(), datetime.strptime(sem['start_date'], '%Y-%m-%d').date())
                sem_end = datetime.strptime(sem['end_date'], '%Y-%m-%d').date()
                
                preview_list = []
                while current_date <= sem_end and remaining_periods > 0:
                    date_str = current_date.strftime('%Y-%m-%d')
                    if date_str not in holidays:
                        current_weekday = current_date.weekday() + 2
                        day_schedules = [s for s in schedules if s['weekday'] == current_weekday]
                        day_schedules.sort(key=lambda x: x['start_time'])
                        
                        for sch in day_schedules:
                            if remaining_periods <= 0: break
                            num_p = min(remaining_periods, sch['num_periods'])
                            preview_list.append({
                                'date': date_str,
                                'time': f"{sch['start_time']} - {sch['end_time']}",
                                'weekday': ['','','Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7','Chủ nhật'][current_weekday],
                                'periods': num_p
                            })
                            remaining_periods -= num_p
                    current_date += timedelta(days=1)
                return preview_list
        except: return []

    def get_class_sessions(self, class_id):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM class_sessions WHERE class_id = ? ORDER BY session_date ASC, start_time ASC", (class_id,))
            return cursor.fetchall()

    def get_editable_sessions(self, class_id, days_limit=7):
        """Lấy danh sách các buổi học trong vòng 7 ngày qua để giảng viên điểm danh bù"""
        from datetime import datetime, timedelta
        limit_date = (datetime.now() - timedelta(days=days_limit)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')
        
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Lấy các buổi đã qua (từ 7 ngày trước đến hôm nay)
            cursor.execute("""
                SELECT id, session_date, start_time, end_time, status, num_periods
                FROM class_sessions 
                WHERE class_id = ? AND session_date >= ? AND session_date <= ?
                ORDER BY session_date DESC, start_time DESC
            """, (class_id, limit_date, today))
            return [dict(row) for row in cursor.fetchall()]

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
                    return dict(s)
            return None

    def get_upcoming_session(self):
        """Tìm ca học tiếp theo trong ngày chưa đến giờ điểm danh"""
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cs.*, c.name as class_name 
                FROM class_sessions cs
                JOIN classes c ON cs.class_id = c.id
                WHERE cs.session_date = ? AND cs.status = 'SCHEDULED'
                ORDER BY cs.start_time ASC
            """, (date_str,))
            sessions = cursor.fetchall()
            for s in sessions:
                start_t = datetime.strptime(f"{date_str} {s['start_time']}", '%Y-%m-%d %H:%M')
                if start_t > now:
                    return dict(s)
        return None
    def get_holidays(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM holidays ORDER BY holiday_date ASC")
                return [dict(row) for row in cursor.fetchall()]
        except: return []

    def create_holiday(self, name, start_date, end_date=None):
        try:
            from datetime import datetime, timedelta
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = start
            if end_date:
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            dates_to_add = []
            curr = start
            while curr <= end:
                dates_to_add.append(curr)
                # Compensation logic: If Sunday, add next Monday
                if curr.weekday() == 6: # Sunday
                    dates_to_add.append(curr + timedelta(days=1))
                curr += timedelta(days=1)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for d in dates_to_add:
                    d_str = d.strftime('%Y-%m-%d')
                    cursor.execute("INSERT OR IGNORE INTO holidays (name, holiday_date) VALUES (?, ?)", (name, d_str))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error create_holiday: {e}")
            return False

    def delete_holiday(self, holiday_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM holidays WHERE id = ?", (holiday_id,))
                conn.commit()
                return True
        except: return False
