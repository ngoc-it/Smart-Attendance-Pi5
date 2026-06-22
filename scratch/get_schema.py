import sqlite3
import os

db_path = 'data/database/attendance.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("DATABASE SCHEMA:\n")
for table in tables:
    table_name = table[0]
    print(f"Table: {table_name}")
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Get foreign keys
    cursor.execute(f"PRAGMA foreign_key_list({table_name});")
    fks = cursor.fetchall()
    for fk in fks:
        print(f"  FK: {fk[3]} -> {fk[2]}({fk[4]})")
    print("-" * 30)

conn.close()
