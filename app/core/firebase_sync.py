import os
import firebase_admin
from firebase_admin import firestore
from datetime import datetime
from config import Config

_db = None

def get_firestore_client():
    global _db
    if not getattr(Config, 'ENABLE_FIREBASE_SYNC', True):
        return None
        
    if _db is not None:
        return _db
    
    try:
        # Check if Firebase Admin is initialized
        if firebase_admin._apps:
            _db = firestore.client()
            return _db
    except Exception as e:
        print(f"Firebase Sync: Failed to get Firestore client: {e}")
    return None

def sync_attendance_log(student_id, name, date, time, status, image_name=None, room_id=None, class_id=None):
    """
    Syncs a student attendance log to Firestore 'attendance_logs' collection.
    """
    db = get_firestore_client()
    if db is None:
        return False
        
    try:
        doc_id = f"{student_id}_{date}_{time.replace(':', '-')}"
        doc_ref = db.collection("attendance_logs").document(doc_id)
        doc_ref.set({
            "student_id": student_id,
            "name": name,
            "date": date,
            "time": time,
            "timestamp": datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S"),
            "status": status,
            "image": image_name,
            "room_id": room_id,
            "class_id": class_id,
            "synced_at": firestore.SERVER_TIMESTAMP
        })
        print(f"Firebase Sync: Attendance log synced for {student_id}")
        return True
    except Exception as e:
        print(f"Firebase Sync: Error syncing attendance log: {e}")
        return False

def sync_leave_request(request_id, student_id, student_name, class_id, class_name, date, reason, status):
    """
    Syncs a student leave request to Firestore 'leave_requests' collection.
    """
    db = get_firestore_client()
    if db is None:
        return False
        
    try:
        doc_ref = db.collection("leave_requests").document(str(request_id))
        doc_ref.set({
            "id": request_id,
            "student_id": student_id,
            "student_name": student_name,
            "class_id": class_id,
            "class_name": class_name,
            "date": date,
            "reason": reason,
            "status": status,
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        print(f"Firebase Sync: Leave request {request_id} synced")
        return True
    except Exception as e:
        print(f"Firebase Sync: Error syncing leave request: {e}")
        return False

def sync_active_session(session_id, class_id, class_name, date, start_time, end_time, status, room):
    """
    Syncs a class session to Firestore 'class_sessions' collection.
    """
    db = get_firestore_client()
    if db is None:
        return False
        
    try:
        doc_ref = db.collection("class_sessions").document(str(session_id))
        doc_ref.set({
            "session_id": session_id,
            "class_id": class_id,
            "class_name": class_name,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "status": status,
            "room": room,
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        print(f"Firebase Sync: Class session {session_id} synced")
        return True
    except Exception as e:
        print(f"Firebase Sync: Error syncing class session: {e}")
        return False

def sync_student_account(student_id, name, dob, student_class, status="REGISTERED", password=None):
    """
    Syncs student account details to Firestore 'students' collection.
    """
    db = get_firestore_client()
    if db is None:
        return False
    try:
        doc_ref = db.collection("students").document(str(student_id))
        payload = {
            "id": student_id,
            "name": name,
            "dob": dob,
            "student_class": student_class,
            "status": status,
            "role": "student",
            "updated_at": firestore.SERVER_TIMESTAMP
        }
        if password:
            payload["password"] = password
        doc_ref.set(payload, merge=True)
        print(f"Firebase Sync: Student account {student_id} synced")
        return True
    except Exception as e:
        print(f"Firebase Sync: Error syncing student account {student_id}: {e}")
        return False

def delete_student_account(student_id):
    """
    Deletes student account details from Firestore 'students' collection.
    """
    db = get_firestore_client()
    if db is None:
        return False
    try:
        doc_ref = db.collection("students").document(str(student_id))
        doc_ref.delete()
        print(f"Firebase Sync: Student account {student_id} deleted")
        return True
    except Exception as e:
        print(f"Firebase Sync: Error deleting student account {student_id}: {e}")
        return False

def sync_lecturer_account(username, password, name, code, role="lecturer"):
    """
    Syncs lecturer or admin account details to Firestore 'users' collection.
    """
    db = get_firestore_client()
    if db is None:
        return False
    try:
        doc_ref = db.collection("users").document(str(username))
        data = {
            "username": username,
            "name": name,
            "code": code,
            "role": role,
            "updated_at": firestore.SERVER_TIMESTAMP
        }
        if password:
            data["password"] = password # For easy remote login matching
        doc_ref.set(data, merge=True)
        print(f"Firebase Sync: Lecturer account {username} synced")
        return True
    except Exception as e:
        print(f"Firebase Sync: Error syncing lecturer account {username}: {e}")
        return False

def delete_lecturer_account(username):
    """
    Deletes lecturer account details from Firestore 'users' collection.
    """
    db = get_firestore_client()
    if db is None:
        return False
    try:
        doc_ref = db.collection("users").document(str(username))
        doc_ref.delete()
        print(f"Firebase Sync: Lecturer account {username} deleted")
        return True
    except Exception as e:
        print(f"Firebase Sync: Error deleting lecturer account {username}: {e}")
        return False

def sync_all_schedules(db_path):
    """
    Syncs all regular schedules and rooms from SQLite to Firestore.
    """
    import sqlite3
    db = get_firestore_client()
    if db is None:
        return False
    try:
        schedules_data = []
        rooms_data = []
        
        with sqlite3.connect(db_path, timeout=30.0) as conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except:
                pass
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Sync schedules
            cursor.execute("""
                SELECT s.id, s.class_id, s.weekday, s.start_period_id, s.num_periods, s.room_id,
                       p.start_time, 
                       (SELECT end_time FROM periods WHERE id = s.start_period_id + s.num_periods - 1) as end_time,
                       r.name as room_name,
                       c.name as class_name, c.code as class_code,
                       p.name as period_name
                FROM schedules s
                JOIN classes c ON s.class_id = c.id
                LEFT JOIN periods p ON s.start_period_id = p.id
                LEFT JOIN rooms r ON s.room_id = r.id
            """)
            schedules = cursor.fetchall()
            for sch in schedules:
                # Get lecturer usernames assigned to this class
                cursor.execute("SELECT username FROM users u JOIN user_classes uc ON u.id = uc.user_id WHERE uc.class_id = ?", (sch['class_id'],))
                lecturers = [row[0] for row in cursor.fetchall()]
                
                # Get student IDs enrolled in this class
                cursor.execute("SELECT student_id FROM class_students WHERE class_id = ?", (sch['class_id'],))
                students = [row[0] for row in cursor.fetchall()]
                
                schedules_data.append({
                    "id": sch['id'],
                    "class_id": sch['class_id'],
                    "class_name": sch['class_name'],
                    "class_code": sch['class_code'],
                    "weekday": sch['weekday'],
                    "start_time": sch['start_time'],
                    "end_time": sch['end_time'],
                    "period_name": sch['period_name'],
                    "num_periods": sch['num_periods'],
                    "room_name": sch['room_name'],
                    "lecturers": lecturers,
                    "students": students
                })
            
            # Sync rooms
            cursor.execute("SELECT id, name FROM rooms")
            rooms = cursor.fetchall()
            for rm in rooms:
                rooms_data.append({
                    "id": rm['id'],
                    "name": rm['name']
                })

        # Perform network writes outside SQLite lock
        for sch in schedules_data:
            doc_id = f"sch_{sch['id']}"
            db.collection("schedules").document(doc_id).set({
                "id": sch['id'],
                "class_id": sch['class_id'],
                "class_name": sch['class_name'],
                "class_code": sch['class_code'],
                "weekday": sch['weekday'],
                "start_time": sch['start_time'],
                "end_time": sch['end_time'],
                "period_name": sch['period_name'],
                "num_periods": sch['num_periods'],
                "room_name": sch['room_name'],
                "lecturer_ids": sch['lecturers'],
                "student_ids": sch['students'],
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
        for rm in rooms_data:
            doc_id = f"room_{rm['id']}"
            db.collection("rooms").document(doc_id).set({
                "id": rm['id'],
                "name": rm['name']
            })

        print("Firebase Sync: Successfully synced all schedules and rooms.")
        return True
    except Exception as e:
        print(f"Firebase Sync: Error syncing schedules: {e}")
        return False

def run_bidirectional_sync(db_instance):
    """
    Run bidirectional synchronization:
    1. Pull leave requests from Firestore to SQLite
    2. Pull/Push makeup requests between Firestore and SQLite
    3. Push recent local attendance logs to Firestore
    4. Sync schedules
    """
    db_firestore = get_firestore_client()
    if db_firestore is None:
        return
        
    import sqlite3
    db_path = db_instance.db_path
    
    try:
        # --- 1. Pull Leave Requests (chỉ lấy thay đổi trong 3 ngày gần nhất để tiết kiệm băng thông và quota) ---
        from datetime import datetime, timedelta
        from google.cloud.firestore_v1.base_query import FieldFilter
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        try:
            leaves_ref = db_firestore.collection("leave_requests").where(filter=FieldFilter("updated_at", ">=", three_days_ago)).get()
        except Exception:
            # Fallback nếu trường updated_at chưa kịp cập nhật hoặc chưa được đánh chỉ mục
            leaves_ref = db_firestore.collection("leave_requests").get()

        with sqlite3.connect(db_path, timeout=30.0) as conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except:
                pass
            cursor = conn.cursor()
            for doc in leaves_ref:
                data = doc.to_dict()
                req_id = data.get("id") or doc.id
                student_id = data.get("student_id")
                class_id = data.get("class_id")
                date = data.get("date")
                reason = data.get("reason")
                status = data.get("status") or "PENDING"
                
                if not student_id or not class_id or not date:
                    continue

                if isinstance(req_id, int) or (isinstance(req_id, str) and req_id.isdigit()):
                    int_id = int(req_id)
                    cursor.execute("SELECT status FROM leave_requests WHERE id = ?", (int_id,))
                    row = cursor.fetchone()
                    if not row:
                        cursor.execute("""
                            INSERT INTO leave_requests (id, student_id, class_id, reason, date, status)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (int_id, student_id, class_id, reason, date, status))
                        print(f"Firebase Sync: Pulled new leave request {int_id} ({status})")
                    else:
                        if row[0] != status:
                            cursor.execute("UPDATE leave_requests SET status = ? WHERE id = ?", (status, int_id))
                            print(f"Firebase Sync: Updated leave request {int_id} status locally to {status}")
                else:
                    # Cloud Firestore string doc.id (e.g. 'abc123xyz')
                    cursor.execute("""
                        SELECT id, status FROM leave_requests 
                        WHERE student_id = ? AND class_id = ? AND date = ?
                    """, (student_id, class_id, date))
                    row = cursor.fetchone()
                    if not row:
                        cursor.execute("""
                            INSERT INTO leave_requests (student_id, class_id, reason, date, status)
                            VALUES (?, ?, ?, ?, ?)
                        """, (student_id, class_id, reason, date, status))
                        print(f"Firebase Sync: Pulled new cloud leave request for student {student_id} ({status})")
                    else:
                        int_id = row[0]
                        if row[1] != status:
                            cursor.execute("UPDATE leave_requests SET status = ? WHERE id = ?", (status, int_id))
                            print(f"Firebase Sync: Updated leave request {int_id} status locally to {status}")
                
                # If approved, update attendance status to ABSENT (Vắng có phép)
                if status == "APPROVED":
                    cursor.execute("""
                        INSERT OR REPLACE INTO attendance_logs (student_id, name, date, time, status, image)
                        SELECT ?, (SELECT name FROM students WHERE id = ?), ?, '00:00:00', 'ABSENT', 'leave_approved'
                        WHERE NOT EXISTS (
                            SELECT 1 FROM attendance_logs WHERE student_id = ? AND date = ? AND status = 'ABSENT'
                        )
                    """, (student_id, student_id, date, student_id, date))
            conn.commit()
            
        # --- 2. Pull/Push Makeup Requests ---
        try:
            makeups_ref = db_firestore.collection("makeup_requests").where(filter=FieldFilter("updated_at", ">=", three_days_ago)).get()
        except Exception:
            makeups_ref = db_firestore.collection("makeup_requests").get()

        local_makeups_to_push = []
        with sqlite3.connect(db_path, timeout=30.0) as conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except:
                pass
            cursor = conn.cursor()
            for doc in makeups_ref:
                data = doc.to_dict()
                m_id = data.get("id") or doc.id
                class_id = data.get("class_id")
                username = data.get("username")
                requested_date = data.get("requested_date")
                start_period_id = data.get("start_period_id")
                num_periods = data.get("num_periods")
                room_name = data.get("room_name")
                reason = data.get("reason")
                status = data.get("status") or "PENDING"
                
                # Resolve room_id
                cursor.execute("SELECT id FROM rooms WHERE name = ?", (room_name,))
                room_row = cursor.fetchone()
                room_id = room_row[0] if room_row else None
                
                # Resolve user_id
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                user_row = cursor.fetchone()
                user_id = user_row[0] if user_row else None
                
                cursor.execute("SELECT status FROM makeup_requests WHERE id = ?", (m_id,))
                row = cursor.fetchone()
                if not row:
                    # Insert new makeup request from Cloud
                    cursor.execute("""
                        INSERT INTO makeup_requests (id, class_id, user_id, requested_date, start_period_id, num_periods, room_id, reason, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (m_id, class_id, user_id, requested_date, start_period_id, num_periods, room_id, reason, status))
                    print(f"Firebase Sync: Pulled new makeup request {m_id} ({status})")
                else:
                    local_status = row[0]
                    if local_status != status:
                        # Update status locally
                        cursor.execute("UPDATE makeup_requests SET status = ? WHERE id = ?", (status, m_id))
                        print(f"Firebase Sync: Updated makeup request {m_id} status locally to {status}")
            
            # Fetch local makeup requests that aren't on Cloud yet
            cursor.execute("""
                SELECT m.id, m.class_id, u.username, m.requested_date, m.start_period_id, m.num_periods, r.name as room_name, m.reason, m.status
                FROM makeup_requests m
                LEFT JOIN users u ON m.user_id = u.id
                LEFT JOIN rooms r ON m.room_id = r.id
            """)
            local_makeups = cursor.fetchall()
            for lm in local_makeups:
                local_makeups_to_push.append({
                    "id": lm[0],
                    "class_id": lm[1],
                    "username": lm[2],
                    "requested_date": lm[3],
                    "start_period_id": lm[4],
                    "num_periods": lm[5],
                    "room_name": lm[6],
                    "reason": lm[7],
                    "status": lm[8]
                })
            conn.commit()

        # Perform network writes for makeup requests outside SQLite lock
        for lm in local_makeups_to_push:
            doc_id = str(lm["id"])
            db_firestore.collection("makeup_requests").document(doc_id).set({
                "id": lm["id"],
                "class_id": lm["class_id"],
                "username": lm["username"],
                "requested_date": lm["requested_date"],
                "start_period_id": lm["start_period_id"],
                "num_periods": lm["num_periods"],
                "room_name": lm["room_name"],
                "reason": lm["reason"],
                "status": lm["status"],
                "updated_at": firestore.SERVER_TIMESTAMP
            }, merge=True)

        # --- 3. Push Recent Attendance Logs ---
        attendance_logs_to_push = []
        with sqlite3.connect(db_path, timeout=30.0) as conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except:
                pass
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.student_id, a.name, a.date, a.time, a.status, a.image,
                       c.id as class_id, c.name as class_name
                FROM attendance_logs a
                LEFT JOIN students s ON a.student_id = s.id
                LEFT JOIN classes c ON s.student_class = c.name
                WHERE a.date >= date('now', '-7 days')
            """)
            logs = cursor.fetchall()
            for log in logs:
                attendance_logs_to_push.append({
                    "student_id": log[0],
                    "name": log[1],
                    "date": log[2],
                    "time": log[3],
                    "status": log[4],
                    "image": log[5],
                    "class_id": log[6],
                    "class_name": log[7]
                })

        # Perform network writes for attendance logs outside SQLite lock
        for log in attendance_logs_to_push:
            doc_id = f"{log['student_id']}_{log['date']}_{log['time'].replace(':', '-')}"
            db_firestore.collection("attendance_logs").document(doc_id).set({
                "student_id": log['student_id'],
                "name": log['name'],
                "date": log['date'],
                "time": log['time'],
                "status": log['status'],
                "image": log['image'],
                "class_id": log['class_id'],
                "class_name": log['class_name'],
                "synced_at": firestore.SERVER_TIMESTAMP
            }, merge=True)

        # --- 3b. Pull Recent Attendance Logs from Cloud Firestore to Local SQLite ---
        try:
            cloud_logs_ref = db_firestore.collection("attendance_logs").where(filter=FieldFilter("synced_at", ">=", three_days_ago)).get()
        except Exception:
            cloud_logs_ref = db_firestore.collection("attendance_logs").get()

        with sqlite3.connect(db_path, timeout=30.0) as conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except:
                pass
            cursor = conn.cursor()
            for doc in cloud_logs_ref:
                data = doc.to_dict()
                student_id = data.get("student_id")
                name = data.get("name")
                date = data.get("date")
                time_val = data.get("time")
                status = data.get("status")
                image = data.get("image")
                class_id = data.get("class_id")
                room_id = data.get("room_id")

                if student_id and date and time_val:
                    # Check if log already exists locally
                    cursor.execute("""
                        SELECT id, status FROM attendance_logs 
                        WHERE student_id = ? AND date = ? AND time = ?
                    """, (student_id, date, time_val))
                    existing = cursor.fetchone()
                    if not existing:
                        cursor.execute("""
                            INSERT INTO attendance_logs (student_id, name, date, time, status, image, room_id, class_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (student_id, name, date, time_val, status, image, room_id, class_id))
                        print(f"Firebase Sync: Pulled attendance log for student {student_id} ({date} {time_val})")
                    else:
                        if existing[1] != status:
                            cursor.execute("""
                                UPDATE attendance_logs SET status = ? WHERE id = ?
                            """, (status, existing[0]))
                            print(f"Firebase Sync: Updated attendance log status for student {student_id} to {status}")
            conn.commit()

        # --- 4. Sync Schedules ---
        sync_all_schedules(db_path)
        
    except Exception as e:
        print(f"Firebase Sync: Bidirectional sync failed: {e}")

def start_background_sync(db_instance):
    """
    Starts a background thread that periodically runs bidirectional sync.
    """
    if not getattr(Config, 'ENABLE_FIREBASE_SYNC', True):
        print("Firebase Sync: Background sync disabled (ENABLE_FIREBASE_SYNC = False).")
        return
        
    import threading
    import time
    
    def sync_loop():
        print("Firebase Sync: Background sync thread started.")
        while True:
            try:
                run_bidirectional_sync(db_instance)
            except Exception as e:
                print(f"Firebase Sync error in background loop: {e}")
            time.sleep(300) # Run every 300 seconds (5 minutes) to avoid locking SQLite
            
    t = threading.Thread(target=sync_loop, daemon=True)
    t.start()

