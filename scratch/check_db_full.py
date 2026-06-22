import sqlite3
import os

db_path = "data/database/attendance.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for table in tables:
    print(f"Table: {table[0]}")
    cursor.execute(f"PRAGMA table_info({table[0]})")
    for col in cursor.fetchall():
        print(f"  {col}")
conn.close()
