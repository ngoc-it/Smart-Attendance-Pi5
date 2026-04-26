import sqlite3

def get_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table_name, sql in tables:
        print(f"Table: {table_name}")
        print(sql)
        print("-" * 40)
    conn.close()

if __name__ == "__main__":
    get_schema("data/database/attendance.db")
