import sqlite3
from app.core.firebase_sync import sync_lecturer_account, delete_lecturer_account

class LecturerDBMixin:
    # ---- USERS CRUD ----
    def get_all_lecturers(self, page=1, per_page=10):
        """Lấy danh sách giảng viên có phân trang, sắp xếp theo tên tiếng Việt (A-Z)."""
        offset = (page - 1) * per_page
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, name, code FROM users WHERE role = 'lecturer' ORDER BY GET_TEN(name) ASC, name ASC LIMIT ? OFFSET ?", 
                           (per_page, offset))
            return cursor.fetchall()

    def get_lecturer_count(self):
        """Đếm tổng số lượng giảng viên trong hệ thống."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'lecturer'")
            return cursor.fetchone()[0]

    def create_lecturer(self, username, password, name, code=None):
        """Tạo mới một tài khoản giảng viên. Nếu mật khẩu rỗng sẽ dùng mật khẩu mặc định."""
        from config import Config
        must_change = 0
        default_pw = getattr(Config, 'DEFAULT_LECTURER_PASSWORD', '123456')
        if not password or not password.strip() or password == default_pw:
            password = default_pw
            must_change = 1
            
        hashed_pw = self.hash_password(password)
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password, role, name, code, must_change_password) VALUES (?, ?, 'lecturer', ?, ?, ?)", 
                               (username, hashed_pw, name, code, must_change))
                conn.commit()
            
            # Đồng bộ lên Firebase
            sync_lecturer_account(username, password, name, code)
            return True
        except sqlite3.IntegrityError:
            return False # Username da ton tai

    def delete_lecturer(self, user_id):
        """Xóa vĩnh viễn một giảng viên và các liên kết lớp học liên quan."""
        username = None
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE id = ? AND role = 'lecturer'", (user_id,))
            row = cursor.fetchone()
            if row:
                username = row[0]
            cursor.execute("DELETE FROM users WHERE id = ? AND role = 'lecturer'", (user_id,))
            cursor.execute("DELETE FROM user_classes WHERE user_id = ?", (user_id,))
            conn.commit()
        
        if username:
            delete_lecturer_account(username)

    def update_lecturer(self, user_id, username, name, code, password=None):
        """Cập nhật thông tin giảng viên. Nếu có mật khẩu mới, mật khẩu sẽ được mã hóa lại."""
        try:
            with self._get_conn() as conn:
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
            
            # Đồng bộ lên Firebase
            sync_lecturer_account(username, password, name, code)
            return True
        except sqlite3.IntegrityError:
            return False

    def change_user_password(self, user_id, old_password, new_password):
        """Cho phép người dùng (giảng viên) tự đổi mật khẩu cá nhân."""
        from werkzeug.security import check_password_hash
        import hashlib
        
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password, username, name, code FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return False, "Tài khoản không tồn tại!"
            
            stored_pw, username, name, code = row[0], row[1], row[2], row[3]
            
            # Kiểm tra mật khẩu cũ
            match = False
            if stored_pw and (stored_pw.startswith('pbkdf2:') or stored_pw.startswith('scrypt:') or stored_pw.startswith('bcrypt:')):
                match = check_password_hash(stored_pw, old_password)
            else:
                legacy_hash = hashlib.sha256(old_password.encode()).hexdigest()
                match = (stored_pw == legacy_hash or stored_pw == old_password)
            
            if not match:
                return False, "Mật khẩu hiện tại không chính xác!"
            
            # Mã hóa mật khẩu mới và lưu
            hashed_new = self.hash_password(new_password)
            cursor.execute("UPDATE users SET password = ?, must_change_password = 0 WHERE id = ?", (hashed_new, user_id))
            conn.commit()
            
            # Đồng bộ Firebase nếu có
            try:
                sync_lecturer_account(username, new_password, name, code, role='lecturer')
            except Exception as sync_err:
                print(f"Failed to sync updated lecturer password to Firebase: {sync_err}")
                
            return True, "Đổi mật khẩu thành công!"

    # ---- USER-CLASS ASSIGNMENT ----
    def get_user_classes(self, user_id):
        """Lấy danh sách các lớp học phần đã được phân công cho một giảng viên cụ thể."""
        with self._get_conn() as conn:
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
        """Gán quyền quản lý một lớp học phần cho giảng viên."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO user_classes (user_id, class_id) VALUES (?, ?)", (user_id, class_id))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def remove_class_from_user(self, user_id, class_id):
        """Hủy quyền quản lý một lớp học phần của giảng viên."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_classes WHERE user_id = ? AND class_id = ?", (user_id, class_id))
            conn.commit()

    def remove_all_lecturers_from_class(self, class_id):
        """Xóa tất cả phân công giảng viên của một lớp học phần."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_classes WHERE class_id = ?", (class_id,))
            conn.commit()

    def get_lecturer_classes_names(self, user_id):
        """Lấy danh sách tên và mã của tất cả các lớp mà giảng viên đang phụ trách."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.name, c.code
                FROM classes c
                JOIN user_classes uc ON c.id = uc.class_id
                WHERE uc.user_id = ?
            """, (user_id,))
            return [f"{row[1]} - {row[0]}" if row[1] else row[0] for row in cursor.fetchall()]

    def create_password_reset_token(self, identifier):
        """
        Tạo mã OTP 6 chữ số để lấy lại mật khẩu theo email hoặc username.
        Hạn dùng: 15 phút.
        """
        import random, datetime
        identifier = str(identifier).strip()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, name FROM users WHERE email = ? OR username = ? OR code = ? LIMIT 1", (identifier, identifier, identifier))
            row = cursor.fetchone()
            if not row:
                return False, "Tài khoản không tồn tại!", None, None, None
            
            user_id, username, email, name = row[0], row[1], row[2], row[3]
            target_email = email if email else identifier
            
            # Tạo OTP 6 chữ số
            otp_code = f"{random.randint(100000, 999999)}"
            expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("""
                INSERT INTO password_resets (user_id, email, token, expires_at, used)
                VALUES (?, ?, ?, ?, 0)
            """, (user_id, target_email, otp_code, expires_at))
            conn.commit()
            
            return True, "Thành công", otp_code, target_email, name

    def verify_otp_code(self, identifier, otp_code):
        """
        Bước 2: Xác thực mã OTP 6 số (chưa dùng và chưa hết hạn 15 phút).
        """
        import datetime
        identifier = str(identifier).strip()
        otp_code = str(otp_code).strip()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pr.id, pr.user_id, u.username, u.name
                FROM password_resets pr
                JOIN users u ON pr.user_id = u.id
                WHERE (pr.email = ? OR u.code = ?) AND pr.token = ? AND pr.used = 0 AND pr.expires_at >= ?
                ORDER BY pr.id DESC LIMIT 1
            """, (identifier, identifier, otp_code, now_str))
            row = cursor.fetchone()
            
            if not row:
                return False, "Mã OTP sai hoặc đã hết hạn!", None, None
                
            reset_id, user_id = row[0], row[1]
            return True, "Xác thực OTP thành công!", reset_id, user_id

    def reset_password_after_otp(self, reset_id, user_id, new_password):
        """
        Bước 3: Đặt mật khẩu mới sau khi đã xác thực OTP thành công.
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, name, code FROM users WHERE id = ?", (user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                return False, "Tài khoản không tồn tại!"
                
            username, name, code = user_row[0], user_row[1], user_row[2]
            
            hashed_new = self.hash_password(new_password)
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_new, user_id))
            cursor.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (reset_id,))
            conn.commit()
            
            try:
                sync_lecturer_account(username, new_password, name, code, role='lecturer')
            except Exception as sync_err:
                print(f"Failed to sync reset password to Firebase: {sync_err}")
                
            return True, "Đổi mật khẩu thành công!"

    def verify_and_reset_password(self, identifier, otp_code, new_password):
        """
        Xác thực mã OTP và cập nhật mật khẩu mới cho người dùng (Hỗ trợ tương thích ngược).
        """
        success, msg, reset_id, user_id = self.verify_otp_code(identifier, otp_code)
        if not success:
            return False, msg
        return self.reset_password_after_otp(reset_id, user_id, new_password)

