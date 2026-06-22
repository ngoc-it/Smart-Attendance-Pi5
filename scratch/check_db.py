import sqlite3
import os

db_path = "data/database/attendance.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", tables)
    for table in tables:
        print(f"\nSchema for {table[0]}:")
        cursor.execute(f"PRAGMA table_info({table[0]})")
        print(cursor.fetchall())
    conn.close()
