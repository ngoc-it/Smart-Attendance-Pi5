from flask import Blueprint, request, jsonify
from app import db
from app.api.utils import encode_token
import sqlite3

mobile_auth_bp = Blueprint('mobile_auth', __name__)

def get_db_connection():
    conn = sqlite3.connect(db.db_path, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except:
        pass
    conn.row_factory = sqlite3.Row
    return conn

@mobile_auth_bp.route('/login', methods=['POST'])
def login():
    """
    Mobile Login Endpoint.
    Accepts: JSON with { "username": "...", "password": "...", "role": "lecturer|student" }
    Returns: JSON with JWT Token and User Information.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Missing JSON request body"}), 400
        
    username = data.get('username')
    password = data.get('password')
    role = data.get('role') # 'lecturer' or 'student'
    
    if not username or not password or not role:
        return jsonify({"status": "error", "message": "Username, password, and role are required"}), 400

    if role == 'lecturer':
        # Authenticate lecturer/admin using db.verify_login
        user = db.verify_login(username, password, role)
        if user:
            # user is a tuple from cursor.fetchone(): (id, name, role)
            user_id = str(user[0])
            name = user[1]
            token = encode_token(user_id, role, name)
            return jsonify({
                "status": "success",
                "message": "Login successful",
                "token": token,
                "user": {
                    "id": user_id,
                    "name": name,
                    "role": role,
                    "username": username
                }
            })
        else:
            return jsonify({"status": "error", "message": "Sai tài khoản, mật khẩu hoặc vai trò giảng viên!"}), 401
            
    elif role == 'student':
        # Authenticate student: check if student exists where id = username and dob = password
        # Allow normalized DOB (replace dashes or slashes)
        normalized_password = password.replace('-', '/').strip()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Try direct match
            cursor.execute("SELECT id, name, dob, student_class, password FROM students WHERE id = ?", (username,))
            student = cursor.fetchone()
            
            if student:
                custom_pw = (student['password'] or '').strip()
                match = False
                
                if custom_pw:
                    # Custom student password set
                    from werkzeug.security import check_password_hash
                    if custom_pw.startswith('pbkdf2:') or custom_pw.startswith('scrypt:') or custom_pw.startswith('bcrypt:'):
                        match = check_password_hash(custom_pw, password.strip())
                    else:
                        match = (custom_pw == password.strip())
                else:
                    # Default initial password: 8-digit DOB (DDMMYYYY)
                    student_dob = str(student['dob'] or '').strip()
                    stored_digits = ''.join(c for c in student_dob if c.isdigit())
                    
                    # Convert stored DOB to strict 8-digit DDMMYYYY format (e.g. 23072007)
                    if len(stored_digits) == 8:
                        if student_dob.startswith('20') or student_dob.startswith('19'): # YYYY-MM-DD
                            year_s, month_s, day_s = stored_digits[:4], stored_digits[4:6], stored_digits[6:]
                            expected_dob = f"{day_s}{month_s}{year_s}"
                        else: # DDMMYYYY or DD/MM/YYYY
                            expected_dob = stored_digits
                    else:
                        expected_dob = student_dob
                    match = (password.strip() == expected_dob)
                
                if match:
                    user_id = student['id']
                    name = student['name']
                    token = encode_token(user_id, 'student', name)
                    return jsonify({
                        "status": "success",
                        "message": "Login successful",
                        "token": token,
                        "user": {
                            "id": user_id,
                            "name": name,
                            "role": "student",
                            "class": student['student_class']
                        }
                    })
            
            return jsonify({"status": "error", "message": "MSSV hoặc ngày sinh (DD/MM/YYYY) không chính xác!"}), 401
            
    else:
        return jsonify({"status": "error", "message": "Invalid role. Must be 'lecturer' or 'student'"}), 400
