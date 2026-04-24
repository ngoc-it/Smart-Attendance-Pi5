import sqlite3
import os

def batch_import(student_list):
    db_path = os.path.join("data", "database", "attendance.db")
    # Đảm bảo thư mục tồn tại
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for mssv, name in student_list:
        try:
            # Mặc định sinh viên mới là OUT
            cursor.execute("INSERT INTO students (id, name, status) VALUES (?, ?, 'OUT')", (mssv, name))
            print(f"Da them: {name} ({mssv})")
        except sqlite3.IntegrityError:
            print(f"Bo qua: {mssv} da ton tai trong he thong.")
    
    conn.commit()
    conn.close()
    print("Hoan tat nap danh sach sinh vien.")

if __name__ == "__main__":
    # Thay the danh sach duoi day bang 50 sinh vien lop Ly 1 cua ban
    physics_class_1 = [
        ("21000001", "Nguyen Van A"),
        ("21000002", "Tran Thi B"),
        # ... tiep tuc cho den du 50 nguoi
    ]
    batch_import(physics_class_1)