import sqlite3
from datetime import datetime, timedelta

class ScheduleDBMixin:
    # ---- LECTURER SPECIFIC SCHEDULE ----
    def get_user_schedule(self, user_id):
        """Lấy thời khóa biểu chi tiết của một giảng viên trong học kỳ hiện tại."""
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

    # ---- SCHEDULE CRUD ----
    def get_schedules(self, class_id=None):
        """Lấy thông tin thời khóa biểu gốc của một lớp hoặc toàn bộ hệ thống."""
        with self._get_conn() as conn:
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
        """Tạo mới một bản ghi thời khóa biểu gốc cho lớp học phần."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedules (class_id, weekday, start_time, end_time, room)
                VALUES (?, ?, ?, ?, ?)
            """, (class_id, weekday, start_time, end_time, room))
            conn.commit()

    def get_class_schedules(self, class_id):
        """Lấy thông tin thời khóa biểu hàng tuần (thời gian, thứ, phòng) của một lớp cụ thể."""
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
        """Kiểm tra xung đột lịch học: Đảm bảo phòng học và giảng viên không bị trùng lịch tại thời điểm đăng ký."""
        end_period_id = start_period_id + num_periods - 1
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 0. Check Max Period Limit
            cursor.execute("SELECT MAX(id) FROM periods")
            max_p = cursor.fetchone()[0] or 10
            if end_period_id > max_p:
                return False, f"Số tiết vượt quá giới hạn ca học (Tối đa tiết {max_p})."
                
            # 0.1 Academic Block Validation (Senior Engineer Logic)
            # Sáng: 1-4, Chiều: 5-8, Tối: 9-12
            def get_block(p_id):
                if 1 <= p_id <= 4: return "Sáng"
                if 5 <= p_id <= 8: return "Chiều"
                if 9 <= p_id <= 12: return "Tối"
                return "Khác"
                
            start_block = get_block(start_period_id)
            end_block = get_block(end_period_id)
            if start_block != end_block:
                return False, f"Lịch học không được vượt quá ranh giới buổi (Tiết {start_period_id} là buổi {start_block}, Tiết {end_period_id} là buổi {end_block})."
                
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
        """Lưu (ghi đè) danh sách thời khóa biểu hàng tuần cho một lớp học phần."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM schedules WHERE class_id = ?", (class_id,))
            for sch in schedules_list:
                cursor.execute("""
                    INSERT INTO schedules (class_id, weekday, start_period_id, num_periods, room_id) 
                    VALUES (?, ?, ?, ?, ?)
                """, (class_id, sch.get('weekday'), sch.get('start_period_id'), sch.get('num_periods'), sch.get('room_id')))
            conn.commit()
            
    def generate_sessions_for_class(self, class_id):
        """Thuật toán thông minh sinh lịch trình buổi học: Tính toán số tiết còn lại, bỏ qua ngày lễ và sinh buổi học cho đến khi đủ định mức học phần."""
        try:
            with self._get_conn() as conn:
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
                    SELECT s.id, s.class_id, s.weekday, s.room_id, s.num_periods, s.start_period_id,
                           p.start_time, 
                           (SELECT end_time FROM periods WHERE id = s.start_period_id + s.num_periods - 1) as end_time
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
                        session_id = cursor.lastrowid
                        
                        # Sync to Firestore
                        try:
                            # Use secondary cursor or query to fetch names
                            cursor.execute("SELECT name FROM classes WHERE id = ?", (class_id,))
                            class_name = cursor.fetchone()[0]
                            cursor.execute("SELECT name FROM rooms WHERE id = ?", (room_id,))
                            room_name = cursor.fetchone()[0]
                            from app.core.firebase_sync import sync_active_session
                            sync_active_session(session_id, class_id, class_name, date_str, start_time, end_time, 'SCHEDULED', room_name)
                        except Exception as sync_err:
                            print(f"Failed to sync scheduled session to Firebase: {sync_err}")
                        
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
        """Mô phỏng việc sinh lịch học để hiển thị bản xem trước cho người dùng trước khi lưu chính thức."""
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
                        SELECT s.weekday, s.num_periods, s.start_period_id,
                               p.start_time,
                               (SELECT end_time FROM periods WHERE id = s.start_period_id + s.num_periods - 1) as end_time
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

    def regenerate_all_sessions(self):
        """Xóa toàn bộ các buổi học chưa diễn ra và sinh lại lịch trình mới cho tất cả các lớp dựa trên TKB gốc."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM classes")
            classes = cursor.fetchall()
            
        for (class_id,) in classes:
            self.generate_sessions_for_class(class_id)

    def get_class_sessions(self, class_id):
        """Lấy danh sách tất cả các buổi học cụ thể (Sessions) đã được sinh ra của một lớp kèm tên phòng."""
        today = datetime.now().strftime('%Y-%m-%d')
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Auto update past scheduled sessions to COMPLETED
            cursor.execute("""
                UPDATE class_sessions 
                SET status = 'COMPLETED' 
                WHERE class_id = ? AND status = 'SCHEDULED' AND session_date < ?
            """, (class_id, today))
            conn.commit()

            cursor.execute("""
                SELECT cs.*, r.name as room_name 
                FROM class_sessions cs 
                LEFT JOIN rooms r ON cs.room_id = r.id
                WHERE cs.class_id = ? 
                ORDER BY session_date ASC, start_time ASC
            """, (class_id,))
            return cursor.fetchall()

    def get_editable_sessions(self, class_id, days_limit=7):
        """Lấy danh sách các buổi học trong quá khứ (mặc định 7 ngày) để hỗ trợ giảng viên điểm danh bù."""
        limit_date = (datetime.now() - timedelta(days=days_limit)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')
        
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Auto update past scheduled sessions to COMPLETED
            cursor.execute("""
                UPDATE class_sessions 
                SET status = 'COMPLETED' 
                WHERE class_id = ? AND status = 'SCHEDULED' AND session_date < ?
            """, (class_id, today))
            conn.commit()

            # Lấy các buổi đã qua (từ 7 ngày trước đến hôm nay)
            cursor.execute("""
                SELECT id, session_date, start_time, end_time, status, num_periods
                FROM class_sessions 
                WHERE class_id = ? AND session_date >= ? AND session_date <= ?
                ORDER BY session_date DESC, start_time DESC
            """, (class_id, limit_date, today))
            return [dict(row) for row in cursor.fetchall()]

    def update_session_status(self, session_id, status):
        """Cập nhật trạng thái của một buổi học (SCHEDULED, COMPLETED, CANCELLED)."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("UPDATE class_sessions SET status = ? WHERE id = ?", (status, session_id))
            conn.commit()
            
            # Sync to Firestore
            try:
                cursor.execute("""
                    SELECT cs.*, c.name as class_name, r.name as room_name 
                    FROM class_sessions cs 
                    JOIN classes c ON cs.class_id = c.id
                    LEFT JOIN rooms r ON cs.room_id = r.id
                    WHERE cs.id = ?
                """, (session_id,))
                sess = cursor.fetchone()
                if sess:
                    from app.core.firebase_sync import sync_active_session
                    sync_active_session(
                        sess['id'], 
                        sess['class_id'], 
                        sess['class_name'], 
                        sess['session_date'], 
                        sess['start_time'], 
                        sess['end_time'], 
                        status, 
                        sess['room_name']
                    )
            except Exception as sync_err:
                print(f"Failed to sync session status update to Firebase: {sync_err}")

    def get_active_session(self):
        """Tìm kiếm ca học đang diễn ra tại thời điểm hiện tại (dùng cho thiết bị Kiosk tự động nhận diện lớp)."""
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
                WHERE cs.session_date >= ? AND cs.status = 'SCHEDULED'
                ORDER BY cs.session_date ASC, cs.start_time ASC
            """, (date_str,))
            sessions = cursor.fetchall()
            
            for s in sessions:
                s_date = s['session_date']
                start_t = datetime.strptime(f"{s_date} {s['start_time']}", '%Y-%m-%d %H:%M')
                end_t = datetime.strptime(f"{s_date} {s['end_time']}", '%Y-%m-%d %H:%M')
                
                checkin_start = start_t - timedelta(minutes=early_min)
                checkout_end = end_t + timedelta(minutes=late_out_min)
                
                if checkin_start <= now <= checkout_end:
                    return dict(s)
            return None

    def get_upcoming_session(self):
        """Tìm kiếm ca học sắp diễn ra tiếp theo trong ngày hoặc ngày tới để hiển thị thông báo chờ."""
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cs.*, c.name as class_name 
                FROM class_sessions cs
                JOIN classes c ON cs.class_id = c.id
                WHERE cs.session_date >= ? AND cs.status = 'SCHEDULED'
                ORDER BY cs.session_date ASC, cs.start_time ASC
            """, (date_str,))
            sessions = cursor.fetchall()
            for s in sessions:
                s_date = s['session_date']
                start_t = datetime.strptime(f"{s_date} {s['start_time']}", '%Y-%m-%d %H:%M')
                if start_t > now:
                    return dict(s)
        return None

    # --- MAKE-UP CLASS MANAGEMENT ---
    def create_makeup_request(self, class_id, user_id, date_str, start_period, num_periods, room_id, reason):
        """Giảng viên gửi yêu cầu dạy bù mới."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO makeup_requests (class_id, user_id, requested_date, start_period_id, num_periods, room_id, reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (class_id, user_id, date_str, start_period, num_periods, room_id, reason))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error create_makeup_request: {e}")
            return False

    def get_user_makeup_requests(self, user_id):
        """Giảng viên lấy danh sách các yêu cầu dạy bù do mình gửi."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.*, c.name as class_name, c.code as class_code, r.name as room_name, p.name as period_name, p.start_time, p.end_time
                FROM makeup_requests m
                JOIN classes c ON m.class_id = c.id
                JOIN rooms r ON m.room_id = r.id
                JOIN periods p ON m.start_period_id = p.id
                WHERE m.user_id = ?
                ORDER BY m.created_at DESC
            """, (user_id,))
            return cursor.fetchall()

    def get_pending_makeup_requests(self):
        """Admin lấy danh sách các yêu cầu dạy bù đang chờ duyệt."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.*, c.name as class_name, u.name as lecturer_name, r.name as room_name, p.name as period_name
                FROM makeup_requests m
                JOIN classes c ON m.class_id = c.id
                JOIN users u ON m.user_id = u.id
                JOIN rooms r ON m.room_id = r.id
                JOIN periods p ON m.start_period_id = p.id
                WHERE m.status = 'PENDING'
                ORDER BY m.created_at DESC
            """)
            return cursor.fetchall()

    def get_processed_makeup_requests(self):
        """Admin lấy danh sách các yêu cầu dạy bù đã xử lý (APPROVED hoặc REJECTED)."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.*, c.name as class_name, u.name as lecturer_name, r.name as room_name, p.name as period_name,
                       admin.name as approver_name
                FROM makeup_requests m
                JOIN classes c ON m.class_id = c.id
                JOIN users u ON m.user_id = u.id
                JOIN rooms r ON m.room_id = r.id
                JOIN periods p ON m.start_period_id = p.id
                LEFT JOIN users admin ON m.approved_by = admin.id
                WHERE m.status IN ('APPROVED', 'REJECTED')
                ORDER BY m.approved_at DESC, m.created_at DESC
            """)
            return cursor.fetchall()

    def update_makeup_request_status(self, request_id, status, admin_id):
        """Cập nhật trạng thái yêu cầu dạy bù. Nếu Duyệt (APPROVED), tự động chèn vào lịch học chính thức."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # 1. Cập nhật trạng thái yêu cầu
                cursor.execute("""
                    UPDATE makeup_requests 
                    SET status = ?, approved_at = CURRENT_TIMESTAMP, approved_by = ? 
                    WHERE id = ?
                """, (status, admin_id, request_id))
                
                # 2. Nếu Duyệt, chèn vào bảng class_sessions
                if status == 'APPROVED':
                    cursor.execute("SELECT * FROM makeup_requests WHERE id = ?", (request_id,))
                    row = cursor.fetchone()
                    if row:
                        class_id, user_id, date_str, start_p_id, num_p, r_id = row[1], row[2], row[3], row[4], row[5], row[6]
                        
                        # Lấy giờ từ bảng periods với null check
                        cursor.execute("SELECT start_time FROM periods WHERE id = ?", (start_p_id,))
                        start_row = cursor.fetchone()
                        start_time = start_row[0] if start_row else "07:00"

                        cursor.execute("SELECT end_time FROM periods WHERE id = ?", (start_p_id + num_p - 1,))
                        end_row = cursor.fetchone()
                        if not end_row:
                            cursor.execute("SELECT end_time FROM periods WHERE id = ?", (start_p_id,))
                            end_row = cursor.fetchone()
                        end_time = end_row[0] if end_row else "11:30"
                        
                        cursor.execute("""
                            INSERT INTO class_sessions (class_id, session_date, start_time, end_time, room_id, status, num_periods)
                            VALUES (?, ?, ?, ?, ?, 'SCHEDULED', ?)
                        """, (class_id, date_str, start_time, end_time, r_id, num_p))
                        session_id = cursor.lastrowid
                        
                        # Sync to Firestore
                        try:
                            cursor.execute("SELECT name FROM classes WHERE id = ?", (class_id,))
                            class_name = cursor.fetchone()[0]
                            cursor.execute("SELECT name FROM rooms WHERE id = ?", (r_id,))
                            room_name = cursor.fetchone()[0]
                            from app.core.firebase_sync import sync_active_session
                            sync_active_session(session_id, class_id, class_name, date_str, start_time, end_time, 'SCHEDULED', room_name)
                        except Exception as sync_err:
                            print(f"Failed to sync approved makeup session to Firebase: {sync_err}")
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error update_makeup_request_status: {e}")
            return False

    def find_available_slots(self, date_str, num_periods):
        """Tìm các phòng học và khung giờ còn trống trong một ngày cụ thể."""
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        weekday = dt.weekday() + 2 # SQLite weekday: 2=Mon
        
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Lấy tất cả phòng
            rooms = self.get_all_rooms()
            # Lấy tất cả tiết học
            periods = self.get_all_periods()
            max_period = len(periods)
            
            available = []
            for r in rooms:
                for p in periods:
                    start_p = p['id']
                    if start_p + num_periods - 1 > max_period: continue
                    
                    # Kiểm tra lịch cố định (schedules)
                    cursor.execute("""
                        SELECT 1 FROM schedules 
                        WHERE room_id = ? AND weekday = ? 
                        AND NOT (start_period_id + num_periods - 1 < ? OR start_period_id > ?)
                    """, (r['id'], weekday, start_p, start_p + num_periods - 1))
                    
                    if cursor.fetchone(): continue
                    
                    # Kiểm tra buổi học thực tế (class_sessions) bao gồm dạy bù đã duyệt
                    # Lấy giờ của slot đang kiểm tra
                    cursor.execute("SELECT start_time FROM periods WHERE id = ?", (start_p,))
                    s_t = cursor.fetchone()[0]
                    cursor.execute("SELECT end_time FROM periods WHERE id = ?", (start_p + num_periods - 1,))
                    e_t = cursor.fetchone()[0]
                    
                    cursor.execute("""
                        SELECT 1 FROM class_sessions 
                        WHERE room_id = ? AND session_date = ? AND status != 'CANCELLED'
                        AND NOT (end_time <= ? OR start_time >= ?)
                    """, (r['id'], date_str, s_t, e_t))
                    
                    if cursor.fetchone(): continue
                    
                    # Nếu vượt qua tất cả, đây là slot trống
                    available.append({
                        'room_id': r['id'],
                        'room_name': r['name'],
                        'start_period_id': start_p,
                        'period_name': p['name'],
                        'start_time': s_t,
                        'end_time': e_t
                    })
            return available
