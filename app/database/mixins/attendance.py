import sqlite3
from datetime import datetime

class AttendanceDBMixin:
    # ---- LEAVE REQUESTS ----
    def get_leave_requests(self, user_id):
        """Lấy danh sách các đơn xin nghỉ phép của sinh viên gửi tới các lớp do giảng viên quản lý."""
        with self._get_conn() as conn:
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
        """Duyệt hoặc từ chối đơn xin nghỉ phép của sinh viên."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("UPDATE leave_requests SET status = ? WHERE id = ?", (status, request_id))
            conn.commit()
            
            # Sync to Firestore
            try:
                cursor.execute("""
                    SELECT lr.*, s.name as student_name, c.name as class_name
                    FROM leave_requests lr
                    JOIN students s ON lr.student_id = s.id
                    JOIN classes c ON lr.class_id = c.id
                    WHERE lr.id = ?
                """, (request_id,))
                req = cursor.fetchone()
                if req:
                    from app.core.firebase_sync import sync_leave_request
                    sync_leave_request(
                        req['id'], 
                        req['student_id'], 
                        req['student_name'], 
                        req['class_id'], 
                        req['class_name'], 
                        req['date'], 
                        req['reason'], 
                        status
                    )
            except Exception as sync_err:
                print(f"Failed to sync leave request status update to Firebase: {sync_err}")

    # ---- ATTENDANCE LOGGING & STATUS UPDATE ----
    def update_status(self, student_id, name, action, image_path=None):
        """Ghi nhận sự kiện điểm danh tự động và cập nhật trạng thái hiện tại của sinh viên theo Ca học."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 1. Tìm ca học đang diễn ra của sinh viên này
            # Ưu tiên các lớp mà sinh viên này có tham gia (class_students)
            cursor.execute("""
                SELECT cs.class_id, cs.room_id
                FROM class_sessions cs
                JOIN class_students cstd ON cs.class_id = cstd.class_id
                WHERE cstd.student_id = ? 
                AND cs.session_date = ?
                AND cs.status = 'SCHEDULED'
                AND ? BETWEEN time(cs.start_time, '-15 minutes') AND cs.end_time
                LIMIT 1
            """, (student_id, date_str, time_str))
            session_now = cursor.fetchone()
            
            class_id = session_now[0] if session_now else None
            room_id = session_now[1] if session_now else None

            # 2. Ghi vào bảng attendance_logs mới
            cursor.execute("""
                INSERT INTO attendance_logs (student_id, name, date, time, status, image, room_id, class_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (student_id, name, date_str, time_str, action, image_path, room_id, class_id))
            
            # 3. Cập nhật status nhanh trong bảng students (để hiện thị ở các danh sách tổng quát)
            cursor.execute("UPDATE students SET status = ?, last_seen = ? WHERE id = ?", (action, f"{date_str} {time_str}", student_id))
            conn.commit()

            # Sync to Firestore
            try:
                from app.core.firebase_sync import sync_attendance_log
                sync_attendance_log(student_id, name, date_str, time_str, action, image_path, room_id, class_id)
            except Exception as sync_err:
                print(f"Failed to sync attendance to Firebase: {sync_err}")

    def update_attendance_manual(self, student_id, action, date_str, reason=None):
        """Ghi nhận trạng thái điểm danh thủ công, tự động tìm lớp học phù hợp trong ngày."""
        time_str = "00:00:01" 
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # Tìm class_id đầu tiên của sinh viên này trong ngày đó (nếu có)
            cursor.execute("""
                SELECT cs.class_id, cs.room_id FROM class_sessions cs
                JOIN class_students cstd ON cs.class_id = cstd.class_id
                WHERE cstd.student_id = ? AND cs.session_date = ?
                LIMIT 1
            """, (student_id, date_str))
            session_ref = cursor.fetchone()
            class_id = session_ref[0] if session_ref else None
            room_id = session_ref[1] if session_ref else None

            reason_payload = f"SPECIAL:{reason}" if reason else None
            
            cursor.execute("""
                INSERT INTO attendance_logs (student_id, name, date, time, status, image, room_id, class_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (student_id, self.get_student_name(student_id), date_str, time_str, action, reason_payload, room_id, class_id))
            
            if date_str == datetime.now().strftime("%Y-%m-%d"):
                cursor.execute("UPDATE students SET status = ?, last_seen = ? WHERE id = ?", (action, f"{date_str} {time_str}", student_id))
            conn.commit()
            
            # Sync to Firestore
            try:
                from app.core.firebase_sync import sync_attendance_log
                sync_attendance_log(
                    student_id, 
                    self.get_student_name(student_id), 
                    date_str, 
                    time_str, 
                    action, 
                    reason_payload, 
                    room_id, 
                    class_id
                )
            except Exception as sync_err:
                print(f"Failed to sync manual attendance to Firebase: {sync_err}")
                
            return True

    def get_daily_attendance(self, date_str=None, user_id=None):
        """Lấy danh sách chi tiết các lượt điểm danh trong một ngày cụ thể (Dùng cho Admin System Log)."""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        params = [date_str]
        filter_clause = ""
        if user_id:
            filter_clause = "AND s.id IN (SELECT student_id FROM class_students cs JOIN user_classes uc ON cs.class_id = uc.class_id WHERE uc.user_id = ?)"
            params.append(user_id)

        query = f"""
            SELECT l.date || ' ' || l.time as time, l.name, l.student_id as id, l.status as action, l.image as image_path
            FROM attendance_logs l
            JOIN students s ON l.student_id = s.id
            WHERE l.date = ? {filter_clause}
            ORDER BY l.time DESC
        """
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
            
    def get_attendance_stats(self, date_str=None, user_id=None):
        """Tính toán thống kê nhanh số lượng Có mặt/Vắng mặt trong ngày."""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        with self._get_conn() as conn:
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

    def get_detailed_attendance(self, date_str, class_id):
        """Xây dựng báo cáo điểm danh chi tiết phân tách theo từng Ca học (Session) trong ngày."""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 1. Tìm tất cả các buổi học (sessions) của lớp trong ngày này
            cursor.execute("""
                SELECT id, start_time, end_time, room, room_id 
                FROM class_sessions 
                WHERE class_id = ? AND session_date = ?
                ORDER BY start_time ASC
            """, (class_id, date_str))
            sessions = cursor.fetchall()
            
            # 2. Lấy danh sách sinh viên của lớp
            cursor.execute("""
                SELECT s.id, s.name FROM students s
                JOIN class_students cs ON s.id = cs.student_id
                WHERE cs.class_id = ?
                ORDER BY s.id ASC
            """, (class_id,))
            students = cursor.fetchall()
            
            final_report = []
            
            # 3. Với mỗi ca học, xây dựng bảng điểm danh riêng
            for sess in sessions:
                sess_id = sess['id']
                s_start = sess['start_time']
                s_end = sess['end_time']
                
                sess_report = {
                    "session_id": sess_id,
                    "info": f"{s_start} - {s_end} ({sess['room'] or 'N/A'})",
                    "students": []
                }
                
                for s in students:
                    s_id = s['id']
                    # Tìm log điểm danh trong khung giờ của ca này
                    cursor.execute("""
                        SELECT status, time, image FROM attendance_logs
                        WHERE student_id = ? AND class_id = ? AND date = ?
                        AND time BETWEEN ? AND ?
                        ORDER BY time ASC
                    """, (s_id, class_id, date_str, s_start, s_end))
                    logs = cursor.fetchall()
                    
                    status = "Vắng"
                    in_time = "-"
                    out_time = "-"
                    in_image = None
                    out_image = None
                    
                    if logs:
                        in_log = logs[0]
                        out_log = logs[-1] if len(logs) > 1 else None
                        
                        in_time = in_log['time']
                        in_image = in_log['image']
                        status = in_log['status'] # Có mặt, Muộn, vv.
                        
                        if out_log:
                            out_time = out_log['time']
                            out_image = out_log['image']
                            if status == "Có mặt": status = "Hoàn thành"

                    sess_report["students"].append({
                        "id": s_id,
                        "name": s['name'],
                        "in_time": in_time,
                        "out_time": out_time,
                        "in_image": in_image,
                        "out_image": out_image,
                        "status": status
                    })
                
                final_report.append(sess_report)
            
            return final_report

    def get_detailed_attendance_legacy(self, date_str, class_name):
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
        """Tạo ma trận điểm danh tổng hợp bám sát Lịch dạy (Session-based) cho báo cáo Excel."""
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
                ORDER BY s.id ASC
            """, (class_id,))
            students = cursor.fetchall()

            # 3. Lấy tất cả các CA HỌC (Sessions) trong khoảng thời gian (Thay vì chỉ lấy ngày có log)
            query = """
                SELECT id, session_date, start_time, end_time, room 
                FROM class_sessions 
                WHERE class_id = ?
            """
            params = [class_id]
            if start_date:
                query += " AND session_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND session_date <= ?"
                params.append(end_date)
            query += " ORDER BY session_date ASC, start_time ASC"
            
            cursor.execute(query, params)
            sessions = cursor.fetchall()

            # 4. Lấy TOÀN BỘ attendance_logs của lớp này trong khoảng thời gian
            query_logs = """
                SELECT student_id, status, date, time
                FROM attendance_logs
                WHERE class_id = ?
            """
            params_logs = [class_id]
            if start_date:
                query_logs += " AND date >= ?"
                params_logs.append(start_date)
            if end_date:
                query_logs += " AND date <= ?"
                params_logs.append(end_date)
            
            cursor.execute(query_logs, params_logs)
            all_logs = cursor.fetchall()
            
            # Chuyển logs thành dictionary để tra cứu nhanh: {(student_id, date): [logs]}
            log_lookup = {}
            for log in all_logs:
                key = (log['student_id'], log['date'])
                if key not in log_lookup:
                    log_lookup[key] = []
                log_lookup[key].append(log)

            today = datetime.now().strftime("%Y-%m-%d")
            matrix = {} 
            for sess in sessions:
                s_date = sess['session_date']
                s_start = sess['start_time']
                s_end = sess['end_time']
                label = f"{s_date}\n({s_start}-{s_end})"
                
                matrix[label] = {}
                
                # Trạng thái mặc định: "K" nếu đã/đang dạy, "-" nếu chưa dạy (tương lai)
                default_status = "K" if s_date <= today else "-"
                
                for s in students:
                    s_id = s['id']
                    logs_for_day = log_lookup.get((s_id, s_date), [])
                    
                    status = default_status
                    for l in logs_for_day:
                        l_time = l['time']
                        if s_start <= l_time <= s_end:
                            status = l['status']
                            break 
                    
                    matrix[label][s_id] = status

            return class_info, students, matrix

    def get_attendance_summary_matrix_legacy(self, class_id, start_date=None, end_date=None):
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
