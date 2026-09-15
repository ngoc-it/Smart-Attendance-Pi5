from flask import Blueprint, request, jsonify
from app import db, ai_engine
from app.api.utils import mobile_jwt_required
import sqlite3
import base64
import numpy as np
import cv2
import os
from config import Config

mobile_student_bp = Blueprint('mobile_student', __name__)

def get_db_connection():
    conn = sqlite3.connect(db.db_path, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except:
        pass
    conn.row_factory = sqlite3.Row
    return conn

@mobile_student_bp.route('/schedule', methods=['GET'])
@mobile_jwt_required(role='student')
def get_schedule():
    """Get schedule of classes for the authenticated student."""
    student_id = request.current_user['user_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Query schedules for classes this student belongs to
        cursor.execute("""
            SELECT c.id as class_id, c.name as class_name, c.code as class_code,
                   co.name as course_name, co.code as course_code,
                   s.weekday, s.start_time, s.end_time, s.room
            FROM class_students cs
            JOIN classes c ON cs.class_id = c.id
            JOIN courses co ON c.course_id = co.id
            LEFT JOIN schedules s ON c.id = s.class_id
            WHERE cs.student_id = ?
            ORDER BY s.weekday, s.start_time
        """, (student_id,))
        
        rows = cursor.fetchall()
        schedule_list = [dict(row) for row in rows]
        
        return jsonify({
            "status": "success",
            "schedule": schedule_list
        })


@mobile_student_bp.route('/attendance', methods=['GET'])
@mobile_jwt_required(role='student')
def get_attendance():
    """Get attendance logs and summaries for the authenticated student."""
    student_id = request.current_user['user_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Get detailed attendance logs
        cursor.execute("""
            SELECT al.id, al.date, al.time, al.status, al.image, 
                   c.name as class_name, c.code as class_code, r.name as room_name
            FROM attendance_logs al
            LEFT JOIN classes c ON al.class_id = c.id
            LEFT JOIN rooms r ON al.room_id = r.id
            WHERE al.student_id = ?
            ORDER BY al.date DESC, al.time DESC
        """, (student_id,))
        logs = [dict(row) for row in cursor.fetchall()]
        
        # 2. Get summaries per class
        cursor.execute("""
            SELECT c.id as class_id, c.name as class_name, c.code as class_code,
                   COUNT(CASE WHEN al.status = 'IN' THEN 1 END) as presence_count,
                   COUNT(CASE WHEN al.status = 'LATE' THEN 1 END) as late_count,
                   COUNT(CASE WHEN al.status = 'ABSENT' THEN 1 END) as absence_count
            FROM class_students cs
            JOIN classes c ON cs.class_id = c.id
            LEFT JOIN attendance_logs al ON c.id = al.class_id AND al.student_id = cs.student_id
            WHERE cs.student_id = ?
            GROUP BY c.id
        """, (student_id,))
        summaries = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            "status": "success",
            "logs": logs,
            "summaries": summaries
        })


@mobile_student_bp.route('/leave_request', methods=['POST'])
@mobile_jwt_required(role='student')
def submit_leave_request():
    """Submit a leave request for a specific class on a specific date."""
    student_id = request.current_user['user_id']
    data = request.get_json()
    
    if not data:
        return jsonify({"status": "error", "message": "Missing JSON body"}), 400
        
    class_id = data.get('class_id')
    date = data.get('date') # YYYY-MM-DD
    reason = data.get('reason', '').strip()
    
    if not class_id or not date or not reason:
        return jsonify({"status": "error", "message": "class_id, date, and reason are required"}), 400
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Verify student is in this class
        cursor.execute("SELECT 1 FROM class_students WHERE class_id = ? AND student_id = ?", (class_id, student_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "You are not enrolled in this class"}), 403
            
        # Check if already exists
        cursor.execute("SELECT id FROM leave_requests WHERE student_id = ? AND class_id = ? AND date = ?", 
                       (student_id, class_id, date))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Đơn xin nghỉ cho ngày này đã được gửi trước đó!"}), 400
            
        cursor.execute("""
            INSERT INTO leave_requests (student_id, class_id, reason, date, status)
            VALUES (?, ?, ?, ?, 'PENDING')
        """, (student_id, class_id, reason, date))
        request_id = cursor.lastrowid
        conn.commit()
        
        # Sync to Firestore
        try:
            cursor.execute("SELECT name FROM students WHERE id = ?", (student_id,))
            student_name = cursor.fetchone()[0]
            cursor.execute("SELECT name FROM classes WHERE id = ?", (class_id,))
            class_name = cursor.fetchone()[0]
            
            from app.core.firebase_sync import sync_leave_request
            sync_leave_request(request_id, student_id, student_name, class_id, class_name, date, reason, 'PENDING')
        except Exception as sync_err:
            print(f"Failed to sync leave request to Firebase: {sync_err}")
        
        return jsonify({
            "status": "success",
            "message": "Gửi đơn xin nghỉ thành công. Vui lòng chờ Giảng viên phê duyệt."
        })


@mobile_student_bp.route('/change_password', methods=['POST'])
@mobile_jwt_required(role='student')
def change_password():
    """
    Change Student Password Endpoint.
    Accepts: JSON with { "old_password": "...", "new_password": "..." }
    """
    student_id = request.current_user['user_id']
    data = request.get_json()
    
    if not data or 'old_password' not in data or 'new_password' not in data:
        return jsonify({"status": "error", "message": "Vui lòng nhập mật khẩu cũ và mật khẩu mới!"}), 400
        
    old_pw = str(data['old_password']).strip()
    new_pw = str(data['new_password']).strip()
    
    if len(new_pw) < 6:
        return jsonify({"status": "error", "message": "Mật khẩu mới phải có ít nhất 6 ký tự!"}), 400
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, dob, student_class, password FROM students WHERE id = ?", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            return jsonify({"status": "error", "message": "Sinh viên không tồn tại!"}), 404
            
        custom_pw = (student['password'] or '').strip()
        match = False
        
        if custom_pw:
            from werkzeug.security import check_password_hash
            if custom_pw.startswith('pbkdf2:') or custom_pw.startswith('scrypt:') or custom_pw.startswith('bcrypt:'):
                match = check_password_hash(custom_pw, old_pw)
            else:
                match = (custom_pw == old_pw)
        else:
            student_dob = str(student['dob'] or '').strip()
            stored_digits = ''.join(c for c in student_dob if c.isdigit())
            if len(stored_digits) == 8:
                if student_dob.startswith('20') or student_dob.startswith('19'):
                    year_s, month_s, day_s = stored_digits[:4], stored_digits[4:6], stored_digits[6:]
                    expected_dob = f"{day_s}{month_s}{year_s}"
                else:
                    expected_dob = stored_digits
            else:
                expected_dob = student_dob
            match = (old_pw == expected_dob)
            
        if not match:
            return jsonify({"status": "error", "message": "Mật khẩu cũ không chính xác!"}), 400
            
        from werkzeug.security import generate_password_hash
        hashed_new_pw = generate_password_hash(new_pw)
        
        cursor.execute("UPDATE students SET password = ? WHERE id = ?", (hashed_new_pw, student_id))
        conn.commit()
        
        # Sync to Firestore
        try:
            from app.core.firebase_sync import sync_student_account
            sync_student_account(student_id, student['name'], student['dob'], student['student_class'], password=hashed_new_pw)
        except Exception as sync_err:
            print(f"Failed to sync updated student password to Firebase: {sync_err}")
            
        return jsonify({
            "status": "success",
            "message": "Đổi mật khẩu thành công!"
        })

