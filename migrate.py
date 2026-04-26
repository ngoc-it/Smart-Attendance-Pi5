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
    (1,'Tiết 1','07:30','08:20'),(2,'Tiết 2','08:20','09:10'),
    (3,'Tiết 3','09:20','10:10'),(4,'Tiết 4','10:10','11:00'),
    (5,'Tiết 5','11:00','11:50'),(6,'Tiết 6','13:00','13:50'),
    (7,'Tiết 7','13:50','14:40'),(8,'Tiết 8','14:50','15:40'),
    (9,'Tiết 9','15:40','16:30'),(10,'Tiết 10','16:30','17:20'),
    (11,'Tiết 11','18:00','18:50'),(12,'Tiết 12','18:50','19:40')
]
for p in periods:
    c.execute('INSERT OR IGNORE INTO periods (id,name,start_time,end_time) VALUES (?,?,?,?)', p)
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
