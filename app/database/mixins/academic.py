import sqlite3
from datetime import datetime, timedelta

class AcademicDBMixin:
    # ---- ACADEMIC CRUD (Departments, Majors, Courses) ----
    def get_all_departments(self):
        """Lấy danh sách tất cả các Khoa/Phòng ban trong trường."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM departments ORDER BY name")
            return cursor.fetchall()

    def get_all_majors(self):
        """Lấy danh sách tất cả các ngành học hiện có kèm theo thông tin khoa quản lý."""
        with self._get_conn() as conn:
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
        """Lấy danh sách tất cả học phần trong hệ thống, hỗ trợ lọc theo ngành và danh mục."""
        with self._get_conn() as conn:
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
        """Tạo mới một Khoa/Phòng ban đào tạo."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO departments (name) VALUES (?)", (name,))
                conn.commit()
                return True
        except: return False

    def update_department(self, dept_id, name):
        """Cập nhật tên của một Khoa hiện có."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE departments SET name = ? WHERE id = ?", (name, dept_id))
                conn.commit()
                return True
        except: return False

    def delete_department(self, dept_id):
        """Xóa một Khoa khỏi hệ thống (Lưu ý: Chỉ xóa được nếu không có ràng buộc dữ liệu)."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM departments WHERE id = ?", (dept_id,))
                conn.commit()
                return True
        except: return False

    def get_majors(self, department_id=None):
        """Lấy danh sách các ngành học thuộc về một Khoa cụ thể."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if department_id:
                cursor.execute("SELECT m.*, d.name as dept_name FROM majors m LEFT JOIN departments d ON m.department_id = d.id WHERE m.department_id = ?", (department_id,))
            else:
                cursor.execute("SELECT m.*, d.name as dept_name FROM majors m LEFT JOIN departments d ON m.department_id = d.id ORDER BY m.name")
            return cursor.fetchall()

    def create_major(self, name, department_id):
        """Tạo mới một ngành học và gắn nó vào một Khoa quản lý."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO majors (name, department_id) VALUES (?, ?)", (name, department_id))
                conn.commit()
                return True
        except: return False

    def update_major(self, major_id, name, department_id):
        """Cập nhật thông tin ngành học (Tên hoặc Khoa chủ quản)."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE majors SET name = ?, department_id = ? WHERE id = ?", (name, department_id, major_id))
                conn.commit()
                return True
        except: return False

    def delete_major(self, major_id):
        """Xóa một ngành học khỏi hệ thống."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM majors WHERE id = ?", (major_id,))
                conn.commit()
                return True
        except: return False

    def get_courses(self, major_id=None):
        """Lấy danh sách các học phần (Course) thuộc một ngành học cụ thể."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if major_id:
                cursor.execute("SELECT c.*, m.name as major_name FROM courses c LEFT JOIN majors m ON c.major_id = m.id WHERE c.major_id = ?", (major_id,))
            else:
                cursor.execute("SELECT c.*, m.name as major_name FROM courses c LEFT JOIN majors m ON c.major_id = m.id ORDER BY c.name")
            return cursor.fetchall()

    def create_course(self, name, major_id, code=None, category=None, credits=0, lt_credits=0, th_credits=0, total_periods=0):
        """Tạo mới một học phần với đầy đủ thông tin về số tín chỉ và số tiết học."""
        try:
            with self._get_conn() as conn:
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
        """Nhập dữ liệu học phần hàng loạt từ danh sách (thường dùng cho chức năng nhập từ Excel)."""
        count = 0
        with self._get_conn() as conn:
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
        """Cập nhật thông tin chi tiết của một học phần hiện có."""
        try:
            with self._get_conn() as conn:
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
        """Xóa một học phần khỏi hệ thống."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
                conn.commit()
                return True
        except: return False

    # --- SEMESTER CRUD ---
    def get_all_semesters(self):
        """Lấy danh sách toàn bộ các học kỳ đã khai báo trong hệ thống."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM semesters ORDER BY start_date DESC")
            return cursor.fetchall()

    def get_current_semester(self):
        """Lấy thông tin học kỳ đang được đánh dấu là học kỳ hiện tại."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM semesters WHERE is_current = 1 LIMIT 1")
            return cursor.fetchone()

    def create_semester(self, name, start_date, end_date, is_current=0):
        """Tạo mới một học kỳ và tùy chọn đặt làm học kỳ hiện tại (tự động bỏ chọn các học kỳ khác)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            if is_current == 1:
                cursor.execute("UPDATE semesters SET is_current = 0")
            cursor.execute("INSERT INTO semesters (name, start_date, end_date, is_current) VALUES (?, ?, ?, ?)",
                           (name, start_date, end_date, is_current))
            conn.commit()
            return cursor.lastrowid

    def set_current_semester(self, semester_id):
        """Thay đổi học kỳ hiện hành của hệ thống theo ID."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE semesters SET is_current = 0")
            cursor.execute("UPDATE semesters SET is_current = 1 WHERE id = ?", (semester_id,))
            conn.commit()

    def update_semester(self, sem_id, name, start_date, end_date):
        """Cập nhật thông tin học kỳ và tự động tính toán lại toàn bộ các buổi học dựa trên ngày bắt đầu/kết thúc mới."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE semesters 
                    SET name = ?, start_date = ?, end_date = ? 
                    WHERE id = ?
                """, (name, start_date, end_date, sem_id))
                conn.commit()
            
            # Sau khi đổi ngày, cần đồng bộ lại toàn bộ các lớp
            self.regenerate_all_sessions()
            return True, "Cập nhật thành công và đã đồng bộ lại toàn bộ buổi học."
        except Exception as e:
            return False, str(e)

    def delete_semester(self, sem_id):
        """Xóa một học kỳ (Chỉ cho phép xóa nếu không phải học kỳ hiện tại)."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM semesters WHERE id = ? AND is_current = 0", (sem_id,))
                conn.commit()
                return cursor.rowcount > 0
        except: return False

    # ---- MASTER DATA (ROOMS & PERIODS) ----
    def get_all_rooms(self):
        """Lấy danh sách tất cả các phòng học trong hệ thống."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rooms ORDER BY name ASC")
            return cursor.fetchall()
            
    def create_room(self, name, capacity, has_camera=1):
        """Tạo mới một phòng học kèm cấu hình sức chứa và camera."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO rooms (name, capacity, has_camera) VALUES (?, ?, ?)", (name, capacity, has_camera))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def update_room(self, room_id, name, capacity, has_camera):
        """Cập nhật thông tin tên phòng, sức chứa và trạng thái camera của phòng học."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE rooms SET name = ?, capacity = ?, has_camera = ? WHERE id = ?", (name, capacity, has_camera, room_id))
                conn.commit()
                return True
        except: return False

    def delete_room(self, room_id):
        """Xóa một phòng học khỏi hệ thống quản lý."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
                conn.commit()
                return True
        except: return False

    def get_all_periods(self):
        """Lấy danh sách khung giờ tiết học (Tiết 1 - Tiết 12) của nhà trường."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM periods ORDER BY id ASC")
            return cursor.fetchall()

    def get_holidays(self):
        """Lấy danh sách tất cả các ngày nghỉ lễ đã được khai báo."""
        try:
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM holidays ORDER BY holiday_date ASC")
                return [dict(row) for row in cursor.fetchall()]
        except: return []

    def create_holiday(self, name, start_date, end_date=None):
        """Tạo ngày nghỉ lễ (hỗ trợ một dải ngày) và tự động tính bù nếu rơi vào Chủ nhật (Senior logic)."""
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
            
            with self._get_conn() as conn:
                cursor = conn.cursor()
                for d in dates_to_add:
                    d_str = d.strftime('%Y-%m-%d')
                    cursor.execute("INSERT OR IGNORE INTO holidays (name, holiday_date) VALUES (?, ?)", (name, d_str))
                    
                    # Cập nhật các buổi học hiện có sang trạng thái HOLIDAY
                    cursor.execute("UPDATE class_sessions SET status = 'HOLIDAY' WHERE session_date = ? AND status = 'SCHEDULED'", (d_str,))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error create_holiday: {e}")
            return False

    def delete_holiday(self, holiday_id):
        """Xóa một bản ghi ngày nghỉ lễ và khôi phục các buổi học bị ảnh hưởng."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # Lấy ngày nghỉ trước khi xóa để khôi phục lịch
                cursor.execute("SELECT holiday_date FROM holidays WHERE id = ?", (holiday_id,))
                row = cursor.fetchone()
                if row:
                    h_date = row[0]
                    cursor.execute("DELETE FROM holidays WHERE id = ?", (holiday_id,))
                    # Khôi phục trạng thái cho các buổi học
                    cursor.execute("UPDATE class_sessions SET status = 'SCHEDULED' WHERE session_date = ? AND status = 'HOLIDAY'", (h_date,))
                
                conn.commit()
                return True
        except: return False
