import sqlite3
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Path configurations
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data/database/attendance.db")
FIREBASE_CRED_PATH = os.path.join(BASE_DIR, "data/firebase/firebase-credentials.json")

def sync_accounts():
    print("=== STARTING ACCOUNT SYNCHRONIZATION TO FIREBASE ===")
    
    # 1. Initialize Firebase
    if not os.path.exists(FIREBASE_CRED_PATH):
        print(f"Error: Firebase credentials not found at {FIREBASE_CRED_PATH}")
        return
        
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CRED_PATH)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        return
        
    db = firestore.client()
    
    # 2. Connect to local SQLite
    if not os.path.exists(DB_PATH):
        print(f"Error: SQLite database not found at {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 3. Sync Students
    print("\n--- Syncing Students ---")
    try:
        cursor.execute("SELECT id, name, dob, student_class FROM students")
        students = cursor.fetchall()
        
        batch = db.batch()
        count = 0
        for student in students:
            doc_ref = db.collection("students").document(student['id'])
            batch.set(doc_ref, {
                "id": student['id'],
                "name": student['name'],
                "dob": student['dob'], # acts as password
                "student_class": student['student_class'],
                "role": "student"
            })
            count += 1
            if count % 500 == 0:
                batch.commit()
                batch = db.batch()
        batch.commit()
        print(f"Successfully synchronized {count} student accounts to Firestore 'students' collection.")
    except Exception as e:
        print(f"Error syncing students: {e}")
        
    # 4. Sync Lecturers / Admins (Users table)
    print("\n--- Syncing Lecturers & Admins ---")
    try:
        cursor.execute("SELECT id, username, password, role, name FROM users")
        users = cursor.fetchall()
        
        batch = db.batch()
        count = 0
        for user in users:
            # For easy testing directly via Firestore, we add a plain 'password' field
            # admin and gv2026@gmail.com will use 'ngoc123' as password
            plain_password = "ngoc123"
            
            doc_ref = db.collection("users").document(user['username'])
            batch.set(doc_ref, {
                "id": user['id'],
                "username": user['username'],
                "password": plain_password, # Plain text password for direct Firestore login
                "password_hash": user['password'], # SQLite scrypt/pbkdf2 hash
                "role": user['role'],
                "name": user['name']
            })
            count += 1
        batch.commit()
        print(f"Successfully synchronized {count} user/lecturer accounts to Firestore 'users' collection.")
    except Exception as e:
        print(f"Error syncing users: {e}")
        
    conn.close()
    print("\n=== SYNCHRONIZATION COMPLETED ===")

if __name__ == "__main__":
    sync_accounts()
