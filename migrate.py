#!/usr/bin/env python3
"""
DB Migration Script - Run once to apply new schema
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data/database/attendance.db')
print(f"Migrating: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# New tables
c.execute('''CREATE TABLE IF NOT EXISTS rooms 
    (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, capacity INTEGER, has_camera INTEGER DEFAULT 1)''')
print("✓ rooms table")

c.execute('''CREATE TABLE IF NOT EXISTS periods 
    (id INTEGER PRIMARY KEY, name TEXT UNIQUE, start_time TEXT, end_time TEXT)''')
print("✓ periods table")

c.execute('''CREATE TABLE IF NOT EXISTS device_payloads 
    (id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, class_id INTEGER, 
     date TEXT, trigger_start TEXT, trigger_end TEXT, status TEXT DEFAULT 'PENDING')''')
print("✓ device_payloads table")

# Alter courses
cursor = c.execute("PRAGMA table_info(courses)")
course_cols = [col[1] for col in cursor.fetchall()]
for col, ctype in [('code','TEXT'),('credits','INTEGER'),('lt_credits','INTEGER'),
                   ('th_credits','INTEGER'),('total_periods','INTEGER'),('is_mandatory','INTEGER DEFAULT 1')]:
    if col not in course_cols:
        try:
            c.execute(f'ALTER TABLE courses ADD COLUMN {col} {ctype}')
            print(f"✓ courses.{col}")
        except Exception as e:
            print(f"  courses.{col}: {e}")

# Add unique index for code
try:
    c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_course_code ON courses(code)')
    print("✓ idx_course_code")
except Exception as e:
    print(f"  idx_course_code: {e}")

# Alter schedules
for col, ctype in [('start_period_id','INTEGER'),('num_periods','INTEGER'),('room_id','INTEGER')]:
    try:
        c.execute(f'ALTER TABLE schedules ADD COLUMN {col} {ctype}')
        print(f"✓ schedules.{col}")
    except Exception as e:
        print(f"  schedules.{col}: {e}")

# Alter class_sessions
try:
    c.execute('ALTER TABLE class_sessions ADD COLUMN room_id INTEGER')
    print("✓ class_sessions.room_id")
except Exception as e:
    print(f"  class_sessions.room_id: {e}")

# Seed periods
periods = [
    (1, 'Tiết 1', '07:30', '08:20'), (2, 'Tiết 2', '08:20', '09:10'),
    (3, 'Tiết 3', '09:20', '10:10'), (4, 'Tiết 4', '10:10', '11:00'),
    (5, 'Tiết 5', '13:30', '14:20'), (6, 'Tiết 6', '14:20', '15:10'),
    (7, 'Tiết 7', '15:20', '16:10'), (8, 'Tiết 8', '16:10', '17:00'),
    (9, 'Tiết 9', '18:20', '19:10'), (10, 'Tiết 10', '19:10', '20:00')
]
for p in periods:
    c.execute('INSERT OR REPLACE INTO periods (id,name,start_time,end_time) VALUES (?,?,?,?)', p)
c.execute('DELETE FROM periods WHERE id > 10')
count = c.execute('SELECT count(*) FROM periods').fetchone()[0]
print(f"✓ periods seeded: {count} records")

# Add new setting
c.execute("INSERT OR IGNORE INTO settings (key,value) VALUES ('early_checkin_minutes','15')")
print("✓ early_checkin_minutes setting")

conn.commit()

# Final check
tables = sorted([t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])
print(f"\nAll tables: {tables}")
print("\nMigration DONE ✓")
conn.close()
